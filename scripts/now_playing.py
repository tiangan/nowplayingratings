#!/usr/bin/env python3
"""List movies now playing in theaters with their IMDb ratings.

Sources (both permit this kind of personal use, unlike scraping imdb.com):
  - TMDB API /movie/now_playing  -> which films are in theaters (needs a free key)
  - IMDb's official datasets     -> title.ratings.tsv.gz (averageRating, numVotes)

Standard library only. Usage:
  export TMDB_TOKEN=...   # TMDB "API Read Access Token" (or TMDB_API_KEY=...)
  python3 now_playing.py [--region US] [--sort rating|votes|popularity|title]
                         [--min-votes 0] [--limit 0] [--max-age-days 45] [--json]
"""
import argparse, csv, datetime, gzip, io, json, os, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

TMDB = "https://api.themoviedb.org/3"
RATINGS_URL = "https://datasets.imdbws.com/title.ratings.tsv.gz"
CACHE_DIR = os.path.expanduser(os.environ.get("NOW_PLAYING_CACHE", "~/.cache/now-playing"))
RATINGS_MAX_AGE = 20 * 3600  # IMDb refreshes the dataset daily
# TMDB's own /movie/now_playing window is looser than "in theaters today": it
# can include films that have already left theaters or that release later
# this week. We tighten it to films released in the last N days and not yet
# in the future, which matches what a theater actually has on screen today.
DEFAULT_MAX_AGE_DAYS = 45


def tmdb_get(path, **params):
    token, key = os.environ.get("TMDB_TOKEN"), os.environ.get("TMDB_API_KEY")
    if not (token or key):
        sys.exit("Set TMDB_TOKEN (read access token) or TMDB_API_KEY. Free at themoviedb.org/settings/api")
    if key and not token:
        params["api_key"] = key
    url = f"{TMDB}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise


def now_playing(region):
    movies, page, pages = [], 1, 1
    while page <= pages and page <= 10:
        data = tmdb_get("/movie/now_playing", region=region, language="en-US", page=page)
        pages = data.get("total_pages", 1)
        movies.extend(data.get("results", []))
        page += 1
    seen, unique = set(), []
    for m in movies:
        if m["id"] not in seen:
            seen.add(m["id"])
            unique.append(m)
    return unique


def is_actually_in_theaters(movie, max_age_days):
    """Keep only films that have actually released and haven't aged out of theaters.

    TMDB's now_playing endpoint pads its window with films that release later
    this week and films that released weeks ago, so we re-filter by release_date.
    """
    release_date = movie.get("release_date")
    if not release_date:
        return False
    try:
        released = datetime.date.fromisoformat(release_date)
    except ValueError:
        return False
    today = datetime.date.today()
    if released > today:
        return False
    if max_age_days and (today - released).days > max_age_days:
        return False
    return True


def imdb_id(tmdb_id):
    try:
        return tmdb_get(f"/movie/{tmdb_id}/external_ids").get("imdb_id")
    except Exception:
        return None


def load_ratings(wanted):
    """Return {tconst: (rating, votes)} for the IDs we need, using a daily cache."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, "title.ratings.tsv.gz")
    if not os.path.exists(path) or time.time() - os.path.getmtime(path) > RATINGS_MAX_AGE:
        tmp = path + ".part"
        urllib.request.urlretrieve(RATINGS_URL, tmp)
        os.replace(tmp, path)
    out = {}
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for row in csv.reader(f, delimiter="\t"):
            if row[0] in wanted:
                out[row[0]] = (float(row[1]), int(row[2]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="US", help="ISO country code for theater listings")
    ap.add_argument("--sort", default="rating", choices=["rating", "votes", "popularity", "title"])
    ap.add_argument("--min-votes", type=int, default=0, help="hide films with fewer IMDb votes")
    ap.add_argument("--limit", type=int, default=0, help="show only the first N rows")
    ap.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS,
                     help="hide films released more than N days ago (0 disables this filter)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a table")
    a = ap.parse_args()

    movies = now_playing(a.region)
    movies = [m for m in movies if is_actually_in_theaters(m, a.max_age_days)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(imdb_id, [m["id"] for m in movies]))
    ratings = load_ratings({i for i in ids if i})

    rows = []
    for m, iid in zip(movies, ids):
        rating, votes = ratings.get(iid, (None, 0))
        if votes < a.min_votes:
            continue
        rows.append({
            "title": m.get("title"),
            "release_date": m.get("release_date"),
            "imdb_rating": rating,
            "imdb_votes": votes,
            "imdb_url": f"https://www.imdb.com/title/{iid}/" if iid else None,
            "popularity": m.get("popularity", 0),
        })

    keys = {
        "rating": lambda r: (r["imdb_rating"] is None, -(r["imdb_rating"] or 0), -r["imdb_votes"]),
        "votes": lambda r: -r["imdb_votes"],
        "popularity": lambda r: -r["popularity"],
        "title": lambda r: (r["title"] or "").lower(),
    }
    rows.sort(key=keys[a.sort])
    if a.limit:
        rows = rows[: a.limit]

    if a.json:
        print(json.dumps(rows, indent=2))
        return
    print(f"| # | Movie | Released | IMDb | Votes |\n|---|---|---|---|---|")
    for n, r in enumerate(rows, 1):
        rating = f"{r['imdb_rating']:.1f}" if r["imdb_rating"] is not None else "n/a"
        title = f"[{r['title']}]({r['imdb_url']})" if r["imdb_url"] else r["title"]
        print(f"| {n} | {title} | {r['release_date'] or ''} | {rating} | {r['imdb_votes']:,} |")
    print(f"\n{len(rows)} films in theaters ({a.region}). Ratings: IMDb datasets; listings: TMDB.")


if __name__ == "__main__":
    main()
