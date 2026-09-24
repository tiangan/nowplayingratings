#!/usr/bin/env python3
"""List movies currently in theaters with their IMDb ratings.

Sources (both permit this kind of personal use, unlike scraping imdb.com):
  - TMDB API /discover/movie -> films with a theatrical release in your region
    within the last N weeks, using that region's own release dates
  - IMDb's official datasets  -> title.ratings.tsv.gz (averageRating, numVotes)

Standard library only. Usage:
  export TMDB_TOKEN=...   # TMDB "API Read Access Token" (or TMDB_API_KEY=...)
  python3 now_playing.py [--region US] [--weeks 10] [--wide-only] [--no-digital]
                         [--sort rating|votes|popularity|title]
                         [--min-votes 2000] [--limit 0] [--json]
"""
import argparse, csv, gzip, json, os, sys, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

TMDB = "https://api.themoviedb.org/3"
RATINGS_URL = "https://datasets.imdbws.com/title.ratings.tsv.gz"
CACHE_DIR = os.path.expanduser(os.environ.get("NOW_PLAYING_CACHE", "~/.cache/now-playing"))
RATINGS_MAX_AGE = 20 * 3600  # IMDb refreshes the dataset daily
THEATRICAL_LIMITED, THEATRICAL, DIGITAL = 2, 3, 4  # TMDB release types


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


def in_theaters(region, weeks, wide_only):
    """Films whose theatrical release in `region` falls in the last `weeks` weeks."""
    today = date.today()
    params = {
        "region": region,
        "language": "en-US",
        "sort_by": "popularity.desc",
        "include_adult": "false",
        "include_video": "false",
        "with_release_type": str(THEATRICAL) if wide_only else f"{THEATRICAL_LIMITED}|{THEATRICAL}",
        "release_date.gte": (today - timedelta(weeks=weeks)).isoformat(),
        "release_date.lte": today.isoformat(),
    }
    movies, seen, page, pages = [], set(), 1, 1
    while page <= pages and page <= 10:
        data = tmdb_get("/discover/movie", page=page, **params)
        pages = data.get("total_pages", 1)
        for m in data.get("results", []):
            if m["id"] not in seen:
                seen.add(m["id"])
                movies.append(m)
        page += 1
    return movies


def details(tmdb_id, region):
    """Return (imdb_id, regional theatrical date, already on digital?, wide release?)."""
    try:
        d = tmdb_get(f"/movie/{tmdb_id}", append_to_response="release_dates")
    except Exception:
        return None, None, False, False
    today = date.today().isoformat()
    theatrical, digital, wide = [], False, False
    for country in d.get("release_dates", {}).get("results", []):
        if country.get("iso_3166_1") != region:
            continue
        for rel in country.get("release_dates", []):
            day = (rel.get("release_date") or "")[:10]
            if rel.get("type") in (THEATRICAL_LIMITED, THEATRICAL) and day:
                theatrical.append(day)
                wide = wide or rel.get("type") == THEATRICAL
            if rel.get("type") == DIGITAL and day and day <= today:
                digital = True
    return d.get("imdb_id"), (min(theatrical) if theatrical else None), digital, wide


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
    ap.add_argument("--weeks", type=int, default=10, help="only films released in theaters within the last N weeks")
    ap.add_argument("--wide-only", action="store_true", help="skip limited releases (small number of theaters)")
    ap.add_argument("--no-digital", action="store_true", help="skip films already released for digital rental/purchase")
    ap.add_argument("--sort", default="rating", choices=["rating", "votes", "popularity", "title"])
    ap.add_argument("--min-votes", type=int, default=2000, help="hide films with fewer IMDb votes (0 = show all)")
    ap.add_argument("--limit", type=int, default=0, help="show only the first N rows")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a table")
    a = ap.parse_args()

    movies = in_theaters(a.region, a.weeks, a.wide_only)
    with ThreadPoolExecutor(max_workers=8) as pool:
        info = list(pool.map(lambda m: details(m["id"], a.region), movies))
    ratings = load_ratings({i[0] for i in info if i[0]})

    rows = []
    for m, (iid, released, on_digital, wide) in zip(movies, info):
        if (a.no_digital and on_digital) or (a.wide_only and not wide):
            continue
        rating, votes = ratings.get(iid, (None, 0))
        if votes < a.min_votes:
            continue
        rows.append({
            "title": m.get("title"),
            "release_date": released or m.get("release_date"),
            "imdb_rating": rating,
            "imdb_votes": votes,
            "on_digital": on_digital,
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
    print(f"| # | Movie | In theaters since | IMDb | Votes |\n|---|---|---|---|---|")
    for n, r in enumerate(rows, 1):
        rating = f"{r['imdb_rating']:.1f}" if r["imdb_rating"] is not None else "n/a"
        title = f"[{r['title']}]({r['imdb_url']})" if r["imdb_url"] else r["title"]
        if r["on_digital"]:
            title += " (also on digital)"
        print(f"| {n} | {title} | {r['release_date'] or ''} | {rating} | {r['imdb_votes']:,} |")
    kind = "wide" if a.wide_only else "wide + limited"
    print(f"\n{len(rows)} films ({a.region}, {kind} releases from the last {a.weeks} weeks, "
          f"{a.min_votes:,}+ votes). Listings: TMDB. Ratings: IMDb datasets.")


if __name__ == "__main__":
    main()
