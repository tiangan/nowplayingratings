---
name: now-playing-ratings
description: List the movies currently playing in theaters with their IMDb ratings and vote counts, fetched from the TMDB API and IMDb's official daily ratings dataset instead of scraping imdb.com (which blocks automated access). Use this whenever the user asks what's in theaters, what's playing now, new movies this week, cinema listings, or wants IMDb ratings/scores for current releases, even if they don't say "IMDb".
---

# Now Playing + IMDb Ratings

imdb.com disallows automated access, so don't try to fetch or scrape it. This skill uses two sources that allow it:

- **TMDB API** (`/discover/movie`) for films with a theatrical release (limited or wide) in the region within the last `--weeks` weeks (default 10), using that region's own release dates. Per-film details supply the IMDb ID, the regional theatrical date, whether it's a wide release, and whether it's already on digital.
- **IMDb non-commercial datasets** (`title.ratings.tsv.gz`, refreshed daily) for the IMDb rating and vote count. Cached for ~20 hours in `~/.cache/now-playing`.

## Requirements

- Python 3.8+, no extra packages.
- A free TMDB credential in the environment: `TMDB_TOKEN` (the "API Read Access Token") or `TMDB_API_KEY`. If neither is set, tell the user how to get one at themoviedb.org/settings/api rather than guessing.
- Network access to `api.themoviedb.org` and `datasets.imdbws.com`. If requests are blocked, say which domain failed.

## Running it

```bash
python3 scripts/now_playing.py                        # US, last 10 weeks, 2,000+ votes, sorted by IMDb rating
python3 scripts/now_playing.py --weeks 2 --min-votes 0 # brand-new releases, even with few votes
python3 scripts/now_playing.py --wide-only --no-digital  # wide releases not yet available to rent/buy
python3 scripts/now_playing.py --sort popularity --limit 15
python3 scripts/now_playing.py --region GB --json      # other country, machine-readable
```

Pick flags from what the user asked: "top rated" → `--sort rating` (the default `--min-votes 2000` already drops thin ratings); "what's big right now" → `--sort popularity`; a country → `--region`; "just this week" or "brand new" → a small `--weeks` (e.g. `1` or `2`) with `--min-votes 0`, since new films rarely have 2,000 votes yet; "at my local multiplex" / "widely released" → `--wide-only`; "only in theaters" / "not streaming yet" → `--no-digital`.

## Presenting results

- Show the table the script prints (titles link to IMDb). Keep commentary short.
- "In theaters since" is the film's earliest theatrical date in that region. "(also on digital)" means it's already out to rent/buy and may be leaving theaters soon.
- By default films with under 2,000 IMDb votes are hidden. If the user is after new releases and the list looks thin, rerun with `--min-votes 0` and mention that ratings on few votes can shift a lot in the first week.
- "n/a" (only shown with `--min-votes 0`) means IMDb has no rating yet (or TMDB had no IMDb ID); say so rather than inventing a number.
- Credit sources in one line: listings from TMDB, ratings from IMDb's datasets. TMDB's terms ask for attribution.
