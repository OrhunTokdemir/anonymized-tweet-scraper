# Security policy

## Supported versions

Only the latest release gets security fixes.

## Reporting a vulnerability

**Please don't open a public issue for security problems.**

Report them privately through GitHub: open the repository's **Security** tab → **Report a vulnerability** (GitHub private vulnerability reporting). You'll get an answer as soon as the maintainer can. This is a one-person research project, so please allow a few days.

Include a description, the steps to reproduce, and the affected version. **Never include real cookies, tokens, `.env` contents, or scraped posts**, not even in a private report. Use made-up values.

## What counts

- **Credential exposure:** account cookies, tokens or `.env` contents leaking into logs, CSV files, file names, error messages, or builds.
- **Anonymization bypass:** a username, display name, profile link, user or post id, e-mail address or phone number that ends up in the output despite the rules in the README's [Anonymization](README.md#anonymization) section. The limits listed under [Known limitations](README.md#known-limitations) are known and documented; they are not vulnerabilities, but suggestions for improving them are welcome as normal issues.
- **Unsafe file handling:** for example writing outside the app folder, or overwriting user files unexpectedly.

Getting blocked or suspended by a platform is not a security issue (see Ethics & Legal in the README).
