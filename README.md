# now-playing-ratings

A [Claude Code skill](https://code.claude.com/docs/en/skills) that lists movies currently playing in theaters along with their IMDb ratings and vote counts — without scraping imdb.com (which blocks automated access).

## How it works

- **[TMDB API](https://www.themoviedb.org/documentation/api)** (`/discover/movie`) supplies films with a theatrical release (limited or wide) in the given region within the last `--weeks` weeks (default 10), using that region's own release dates rather than a worldwide date.
- For each film, the script fetches its TMDB details and regional release dates to get the IMDb ID, the date it first reached theaters in that region, whether it's a wide release, and whether it's already out for digital rental/purchase.
- **[IMDb's official non-commercial datasets](https://datasets.imdbws.com/)** (`title.ratings.tsv.gz`, refreshed daily) supply the IMDb rating and vote count. Responses are cached locally for ~20 hours in `~/.cache/now-playing`.

## Requirements

- Python 3.8+, no extra packages required.
- A free TMDB credential set in the environment: `TMDB_TOKEN` (the "API Read Access Token") or `TMDB_API_KEY`. Get one at [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api).
- Network access to `api.themoviedb.org` and `datasets.imdbws.com`.

## Usage

```bash
python3 scripts/now_playing.py                        # US, last 10 weeks, 2,000+ votes, sorted by IMDb rating
python3 scripts/now_playing.py --weeks 3               # only films released in the last 3 weeks
python3 scripts/now_playing.py --wide-only --no-digital  # wide releases not yet available to rent/buy
python3 scripts/now_playing.py --min-votes 0           # include brand-new films with few or no votes
python3 scripts/now_playing.py --sort popularity --limit 15
python3 scripts/now_playing.py --region GB --json      # other country, machine-readable
```

| Flag | Description |
|---|---|
| `--region` | ISO country code for theatrical listings (default: `US`) |
| `--weeks` | Only films released in theaters within the last N weeks (default: `10`) |
| `--wide-only` | Skip limited releases (films in a small number of theaters) |
| `--no-digital` | Skip films already released for digital rental/purchase |
| `--sort` | `rating` (default), `votes`, `popularity`, or `title` |
| `--min-votes` | Hide films with fewer than N IMDb votes (default: `2000`; `0` shows all) |
| `--limit` | Max number of films to show |
| `--json` | Output machine-readable JSON instead of a table |

## Notes

- The "In theaters since" column is the film's earliest theatrical release date in the chosen region.
- Films already out for digital rental/purchase are marked "(also on digital)" (`on_digital` in JSON); they may be leaving theaters soon. Use `--no-digital` to hide them.
- The default `--min-votes 2000` hides very new releases and films IMDb hasn't rated yet. Use `--min-votes 0` to see them, keeping in mind a rating on few votes can shift a lot in the first week.
- A rating of "n/a" (only visible with `--min-votes 0`) means IMDb has no rating yet, or TMDB had no matching IMDb ID.
- Listings courtesy of TMDB; ratings courtesy of IMDb's datasets. This product uses the TMDB API but is not endorsed or certified by TMDB.

## Installing as a Claude Code skill

Copy or symlink this folder into your skills directory (e.g. `~/.claude/skills/now-playing-ratings`), or package it as a `.skill` zip and install via your Claude Code skills workflow.
