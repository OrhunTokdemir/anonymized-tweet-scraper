# Contributing

Thanks for helping. Bug reports, documentation fixes and code changes are all welcome.

## Never commit secrets or data

- **Never commit `.env`, `accounts.db` (or any `*.db`), or CSV files.** `.env` holds account cookies, `accounts.db` holds twscrape's session cookies, and CSVs contain posts by real people. All of them are gitignored. Don't weaken those rules.
- Only `.env.example` is committed. If you add a setting, add it there with an empty or placeholder value and document it in the README's Configuration table.
- Don't paste cookies, `.env` contents, or scraped posts into issues, pull requests or commit messages.

## Setup

Requires Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m scraper
```

## Tests

```bash
python -m unittest discover -s tests
```

- Tests must run **without network access or real accounts**. Use fakes (see `tests/test_twitter.py`) and temporary files (see `tests/test_envfile.py`). Never touch the real `.env`.
- CI runs the tests on Ubuntu and Windows with Python 3.11–3.14. Please make sure they pass before you open a pull request.

## Code guidelines

- Match the style of the surrounding code: type hints, short docstrings, `from __future__ import annotations`.
- Core modules (`twitter.py`, `eksi.py`, `offensive.py`, `output.py`) report progress through the `progress(str)` callback. Never call `print()` from them; it corrupts the terminal UI.
- **All output goes through `scraper/anonymize.py`.** Don't add columns with user ids, usernames, display names, profile URLs, or raw post ids/URLs.
- If you change an anonymization rule, add a test in `tests/test_anonymize.py` and update `docs/anonymization.md`.
- If you change a column, update `scraper/models.py`, `docs/output-schema.md` and the README.
- Use `scraper/paths.py` (`APP_DIR`, `RESOURCE_DIR`) instead of `__file__` for file paths, so frozen builds work.
- Only `scraper/envfile.py` may write `.env`.
- Don't add features whose purpose is to get around platform rate limits, blocks or suspensions (see Ethics & Legal in the README).

## Releases

- Add your change under `## [Unreleased]` in `CHANGELOG.md`.
- For a release, bump `version` and `date-released` in `CITATION.cff`, and move the changelog entries under the new version.

## Conduct

By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
