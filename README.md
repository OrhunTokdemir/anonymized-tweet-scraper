# anonymized-tweet-scraper

A console program that pulls posts from **Twitter/X** (via [twscrape](https://github.com/vladkens/twscrape)) and **Ekşi Sözlük** (via Ekşi's own mobile API, using the [`eksiapi`](https://github.com/agmmnn/eksiapi) client). It anonymizes them and writes everything into one CSV file.

## Setup (Ubuntu)

```bash
sudo apt install python3-venv          # on Python 3.14 the package may be python3.14-venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m scraper
```

**Adding Twitter accounts:** go to the app's **Accounts** tab.
1. Log in at x.com in your browser.
2. Press F12 → Application (Chrome) or Storage (Firefox) → Cookies → `https://x.com`.
3. Paste the values of `auth_token` and `ct0` into the form and press **Save account**.

The app writes the account into `.env` (creating it from `.env.example` if needed, with permissions `600`) and tests it right away (✅/❌ in the log). **Test selected** and **Remove selected** work on the account highlighted in the list. Editing `.env` by hand still works too.

Use throwaway Twitter accounts, never your personal one. Ekşi needs no account.

## Usage

```bash
source .venv/bin/activate
python -m scraper
```

This opens a full-screen terminal app (mouse and keyboard both work):

```
┌ Anonymized Post Scraper ───────────────────────────────┐
│ [Scrape]  Offensive batch   Accounts                   │
│ ╭ Twitter / X ─────────────────────────────────────╮   │
│ │ Method   [ Search (latest)                ▾ ]    │   │
│ │ Query    [ yapay zeka lang:tr                 ]  │   │
│ │ Count    [ 10 ]                                  │   │
│ ╰──────────────────────────────────────────────────╯   │
│ ╭ Ekşi Sözlük ─────────────────────────────────────╮   │
│ │ Method   [ Keyword search over titles     ▾ ]    │   │
│ │ Query    [ yapay zeka                         ]  │   │
│ │ Order    [ Most-liked first               ▾ ]    │   │
│ │ Count    [ 2 ]                                   │   │
│ ╰──────────────────────────────────────────────────╯   │
│                     [ ] Shuffle rows  [Start scraping] │
│ ╭ log ─────────────────────────────────────────────╮   │
│ │ Twitter: 10/10   Ekşi: 2/2                       │   │
│ │ Wrote 12 anonymized posts to data/2026...csv     │   │
│ ╰──────────────────────────────────────────────────╯   │
└ ^s Start  ^l Clear log  ^q Quit ───────────────────────┘
```

**Tabs**

- **Scrape**: pick a method and count for each source. Set a count to 0 to skip that source.
- **Offensive batch**: see below.
- **Accounts**: add, test and remove Twitter accounts, and see their health (it never shows cookies or passwords).

**Twitter methods**

| Method | Input |
| --- | --- |
| Search (latest / top) | any X search query: `lang:tr`, `since:2026-01-01`, `-filter:retweets`, `min_faves:10` ... |
| A user's tweets (± replies) | `@handle` or profile URL |
| Replies to a tweet | tweet URL |
| List timeline | list URL |
| Trending topic | press **Load trends**, then pick one |

Follower/following lists exist in twscrape too, but they return accounts, not posts, so they are left out on purpose.

**Ekşi methods**: one topic (title, slug or URL), keyword search over titles, or gündem. Order: most-liked, oldest first, or today.

## Offensive-language batch (for ML)

This tab builds a Turkish dataset that mixes offensive-language **candidates** with **control** posts. Use it as raw material for an offensive-language classifier.

- **Lexicon**: `lexicons/tr_offensive.txt` is a seed list in three categories (profanity, insult, identity-based). Extend it. The format is explained at the top of the file. A trailing `$` makes a term whole-word only (`top$` won't match `toplantı`). Without `$`, a term also matches with suffixes (`kelime` matches `kelimeler`).
- **Matching** ignores case (Turkish I/ı, İ/i), leetspeak (`k3l1me`), letters split by dots or spaces (`k.e.l.i.m.e`) and stretched letters (`kelimeeee`). Matching runs on the anonymized text, so a username that contains a listed word never counts as a hit.
- **Twitter**: lexicon terms are combined into `(t1 OR t2 ...) lang:tr -filter:retweets` queries under X's length limit. The program fetches from every query so one word doesn't dominate. Control tweets come from a generic Turkish query that excludes lexicon words. A control tweet that still contains one moves to the offensive group.
- **Ekşi**: there is no site-wide full-text search, so the program scans gündem entries and sorts them by lexicon hits.
- **Offensive %** sets the mix (e.g. 50 means half offensive candidates, half control). Rows are shuffled. Near-duplicate texts are removed by default (important for ML: copies leak between train and test).
- **Extra CSV columns**: `sample_group` (`offensive_candidate` / `control`), `matched_terms`, `matched_categories`.
- **File name**: `data/YYYYMMDD-HHMMSS_offensive_tw<N>_eksi<M>_<lexicon>.csv`

> **These are weak labels.** A keyword hit is not the same as offensive content (a swear word between friends is often just banter), and many offensive posts contain no listed word (sarcasm, threats, new slang). Have the rows annotated by people, ideally two annotators with an agreement check, before training. The control group is "no lexicon hit", not "verified clean".
> The hand-annotated **OffensEval-2020 Turkish** dataset (Çöltekin, 2020; ~35k tweets) works well as a benchmark or extra training data next to your own batch.

## Output

**File name:** `data/YYYYMMDD-HHMMSS_tw<N>_eksi<M>_<slug>.csv` (the offensive batch adds `_offensive`)

- The timestamp comes first, so files sort chronologically.
- `N` and `M` are the actual row counts from each source.
- The slug is an ASCII form of your search terms.

The file is UTF-8 with a BOM, so Turkish characters display correctly in Excel and LibreOffice.

**Columns:** `row, source, method, query, topic, text, created_at, lang, like_count, repost_count, reply_count, quote_count, view_count, favorite_count, hashtags, post_type, sample_group, matched_terms, matched_categories, post_hash`

The `query` column is anonymized too: `from:someone` becomes `from:username`. For user, replies and list methods the column only says `@username`, `tweet-replies` or `list`.

## Anonymization

| Found in text                                          | Replaced with                  |
| ------------------------------------------------------ | ------------------------------ |
| `@mention` (Twitter or Ekşi)                           | `@username`                    |
| `(bkz: @nick)` on Ekşi                                 | `(bkz: @username)`             |
| Bare username / display name of any user seen in the run | `#username`                  |
| `x.com/<user>/...`, `eksisozluk.com/biri/<nick>`       | generic link                   |
| E-mail addresses, phone numbers                        | `[email]`, `[phone]`           |

No user ids, usernames, or post ids/URLs are written. `post_hash` is a salted HMAC of the post id. With a fixed `ANON_SALT` you can de-duplicate across runs, but nobody can turn the hash back into the post.

**Limits:** this is pseudonymization, not perfect anonymity. Exact tweet text plus a timestamp can often be found again with a web search. If you publish a dataset, consider rounding `created_at` or paraphrasing. Names shorter than 3 characters (display names shorter than 4) are not replaced as bare words, to avoid mangling ordinary text.

## Avoiding bans

- Tweets are fetched in chunks of `TW_ROTATE_EVERY` (default 40). Each chunk goes to the **least-recently-used** account (round-robin), with a random `TW_DELAY_MIN` to `TW_DELAY_MAX` second pause between chunks.
- twscrape also switches accounts automatically when one hits a rate limit.
- More accounts help, and a separate `TW_ACCOUNT_n_PROXY` per account helps most.

## Secrets

`.env`, `accounts.db` (twscrape stores session cookies there), and all `*.csv` files are gitignored. `.env.example` is committed. `AGENTS.md` tells AI agents never to read `.env`. `.claude/settings.json` also blocks Claude Code from reading it.

## Tests

```bash
python -m unittest discover -s tests
```

## Notes

- Ekşi Sözlük does not publish public API docs. `eksiapi` talks to the same `api.eksisozluk.com` endpoints the Android app uses, with an anonymous token. It may break when the app changes. If it does, `pip install -U eksiapi`.
- Scraping may conflict with the platforms' Terms of Service. Use it for research and respect KVKK/GDPR when storing data.
