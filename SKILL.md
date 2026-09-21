---
name: now-playing-ratings
description: List the movies currently playing in theaters with their IMDb ratings and vote counts, fetched from the TMDB API and IMDb's official daily ratings dataset instead of scraping imdb.com (which blocks automated access). Use this whenever the user asks what's in theaters, what's playing now, new movies this week, cinema listings, or wants IMDb ratings/scores for current releases, even if they don't say "IMDb".
---

# Now Playing + IMDb Ratings

imdb.com disallows automated access, so don't try to fetch or scrape it. This skill uses two sources that allow it:

- **TMDB API** (`/movie/now_playing`) for which films are in theaters in a region, plus each film's IMDb ID.
- **IMDb non-commercial datasets** (`title.ratings.tsv.gz`, refreshed daily) for the IMDb rating and vote count. Cached for ~20 hours in `~/.cache/now-playing`.

## Requirements

- Python 3.8+, no extra packages.
- A free TMDB credential in the environment: `TMDB_TOKEN` (the "API Read Access Token") or `TMDB_API_KEY`. If neither is set, tell the user how to get one at themoviedb.org/settings/api rather than guessing.
- Network access to `api.themoviedb.org` and `datasets.imdbws.com`. If requests are blocked, say which domain failed.

## Running it

```bash
python3 scripts/now_playing.py                      # US, sorted by IMDb rating
python3 scripts/now_playing.py --min-votes 1000     # hide films with too few votes to be meaningful
python3 scripts/now_playing.py --sort popularity --limit 15
python3 scripts/now_playing.py --region GB --json   # other country, machine-readable
```

Pick flags from what the user asked: "top rated" → `--sort rating --min-votes 1000`; "what's big right now" → `--sort popularity`; a country → `--region`.

## Presenting results

- Show the table the script prints (titles link to IMDb). Keep commentary short.
- New releases often have few votes, so mention that a rating on a few hundred votes can shift a lot in the first week.
- "n/a" means IMDb has no rating yet (or TMDB had no IMDb ID); say so rather than inventing a number.
- TMDB's "now playing" window is roughly the last few weeks of releases, so it can include films on their way out and a few limited releases; it is a close match to, not a copy of, IMDb's own "In Theaters" page.
- Credit sources in one line: listings from TMDB, ratings from IMDb's datasets. TMDB's terms ask for attribution.
