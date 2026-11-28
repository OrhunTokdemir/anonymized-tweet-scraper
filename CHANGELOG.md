# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- Starting the program without a terminal (for example by double-clicking it in a file manager) no longer leaves an invisible process using a full CPU core. It now reopens itself in a new terminal window on both Linux and Windows. On Windows a double-click opens it in Windows Terminal when installed, instead of the old console window that displays the app poorly. If no terminal can be opened, it exits right away with a message (a desktop notification on Linux, a message box on Windows).

## [1.1.0] - 2026-11-28

### Changed
- Replaced `TERMS_OF_USE.md` with non-binding responsible-use guidelines (`RESPONSIBLE_USE.md`, English and Turkish). The MIT License is the only license; the non-commercial and "accept to use" conditions were removed.
- The first-start screen is now an informational notice that you close with "I have read the responsible-use guidelines" instead of a terms-acceptance gate. It is recorded locally in `guidelines-read.txt` and shown again when the guidelines change.
- New `--guidelines` flag prints the guidelines (`--terms` still works as an alias). `--paths` shows "Responsible use" instead of "Terms of use".
- Clarified rate-limit and multi-account wording in the README, `.env.example` and the Accounts & settings tab: the scraper respects X's rate limits and is not designed to evade blocks or suspensions.

### Added
- DOI shown in the README's citation section (it was already in `CITATION.cff` and the badge).
- AI-assistance disclosure in the README.
- README states near the top that the output is pseudonymized, not fully anonymous.

## [1.0.0] - 2026-11-28

First public release for research use.

### Added
- Terminal app (`python -m scraper`) that collects posts from Twitter/X (via twscrape) and Ekşi Sözlük (via `eksiapi`) into one pseudonymized CSV.
- Offensive-language batch: a Turkish dataset that mixes lexicon-matched candidates with control posts (weak labels), with the seed lexicon `lexicons/tr_offensive.txt`.
- Accounts & settings tab for adding, testing and removing Twitter accounts, and for choosing the CSV output folder.
- Ready-made programs for Linux (tested on Ubuntu 26.04.1) and Windows 10/11, each as a **standard** download (settings in the per-user folder, CSVs in `Documents/anonymized-posts`) and a **portable** download (everything in its own folder, CSVs in `data/`). Built and published by `.github/workflows/release.yml` with SHA-256 checksums.
- Terms of use (`TERMS_OF_USE.md`, English and Turkish) that must be accepted on first start and again when they change. Acceptance is stored only locally.
- Informational flags: `--version`, `--paths` (where settings, accounts and CSVs are stored), `--terms`, `--help`.
- Cross-platform build script `build.py`, which also smoke-tests the program and packages both downloads (`build.sh` now calls it).
- Rows stream to disk; stopped or crashed runs still save what they collected, and runs can append to an existing file.
- README documentation of the anonymization rules and their limits, the CSV columns, and the offensive-batch method and biases.
- README sections: Ethics & Legal (X Terms of Service, EU DSA Art. 40, KVKK/GDPR, special-category data), a responsible-use checklist, known limitations, and how to cite.
- `CITATION.cff`, CI on Ubuntu and Windows (Python 3.11–3.14), and contributor documentation.

### Changed
- README describes rate limits as something to respect, not to get around. Advice to use more accounts or proxies to lower ban risk was removed.
- twscrape updated to 0.21.1. All runtime dependencies are pinned.

### Fixed
- Anonymization: X profile and status links were not redacted when the username started with "home" or "search" (e.g. `x.com/homer_s/status/…`).
- Anonymization: dates, times, large numbers and search filters such as `since:2026-01-01` were wrongly replaced with `[phone]`. A phone number now needs at least 10 digits and may not start with a date. A leading `(` is now part of the match, so no stray bracket is left behind.
- Accounts & settings tab: **Test selected** reported ✅ for accounts that can log in but that X refuses to search for (e.g. suspended accounts). The test now also runs one search and shows X's reason.
- A Twitter search that returns no tweets now logs a hint instead of silently writing an empty result.

[Unreleased]: https://github.com/OrhunTokdemir/anonymized-tweet-scraper/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/OrhunTokdemir/anonymized-tweet-scraper/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/OrhunTokdemir/anonymized-tweet-scraper/releases/tag/v1.0.0
