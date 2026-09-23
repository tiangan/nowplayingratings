# now-playing-ratings

A [Claude Code skill](https://code.claude.com/docs/en/skills) that lists movies currently playing in theaters along with their IMDb ratings and vote counts — without scraping imdb.com (which blocks automated access).

## How it works

- **[TMDB API](https://www.themoviedb.org/documentation/api)** (`/movie/now_playing`) supplies which films are currently in theaters for a given region, plus each film's IMDb ID.
- TMDB's `now_playing` window is looser than "in theaters today" — it can include films that release later this week and films that released weeks ago. The script re-filters by `release_date` to drop anything not yet released or older than `--max-age-days` (default 45), so the list matches what's actually playing.
- **[IMDb's official non-commercial datasets](https://datasets.imdbws.com/)** (`title.ratings.tsv.gz`, refreshed daily) supply the IMDb rating and vote count. Responses are cached locally for ~20 hours in `~/.cache/now-playing`.

## Requirements

- Python 3.8+, no extra packages required.
- A free TMDB credential set in the environment: `TMDB_TOKEN` (the "API Read Access Token") or `TMDB_API_KEY`. Get one at [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api).
- Network access to `api.themoviedb.org` and `datasets.imdbws.com`.

## Usage

```bash
python3 scripts/now_playing.py                      # US, sorted by IMDb rating
python3 scripts/now_playing.py --min-votes 1000      # hide films with too few votes to be meaningful
python3 scripts/now_playing.py --sort popularity --limit 15
python3 scripts/now_playing.py --region GB --json    # other country, machine-readable
python3 scripts/now_playing.py --max-age-days 21     # only films released in the last 3 weeks
```

| Flag | Description |
|---|---|
| `--region` | ISO country code for theatrical listings (default: `US`) |
| `--sort` | `rating` (default), `votes`, `popularity`, or `title` |
| `--min-votes` | Filter out films with fewer than N IMDb votes |
| `--limit` | Max number of films to show |
| `--max-age-days` | Hide films released more than N days ago (default: `45`; `0` disables the filter) |
| `--json` | Output machine-readable JSON instead of a table |

## Notes

- New releases often have few votes, so an IMDb rating can shift significantly in the first week.
- A rating of "n/a" means IMDb has no rating yet, or TMDB had no matching IMDb ID.
- TMDB's "now playing" window is padded with films that haven't released yet or already left theaters; the script filters those out by `release_date` so the results reflect what's actually playing now (tune with `--max-age-days`).
- Listings courtesy of TMDB; ratings courtesy of IMDb's datasets. This product uses the TMDB API but is not endorsed or certified by TMDB.

## Installing as a Claude Code skill

Copy or symlink this folder into your skills directory (e.g. `~/.claude/skills/now-playing-ratings`), or package it as a `.skill` zip and install via your Claude Code skills workflow.
