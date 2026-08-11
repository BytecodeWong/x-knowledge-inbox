# Codex for Open Source application draft

This draft must be updated with real GitHub evidence after the public repository has users, issues, and releases. Do not invent Stars, downloads, or adoption numbers.

## Describe your role

Primary maintainer. I created and maintain the repository, review changes, triage issues, maintain releases, and own the project’s privacy, security, and documentation practices.

## Why does this repository qualify?

`x-knowledge-inbox` is an open-source, local-first tool for turning X bookmarks into searchable, reviewable knowledge. It addresses a concrete gap: people save useful posts but cannot reliably retrieve, process, or reuse them. The MVP supports JSON/CSV import, deduplication, search, review states, digests, local web access, and Markdown/JSON export. I maintain the code, tests, documentation, and releases. Evidence: [verified GitHub URL and metrics].

## Why does the project need Codex Security?

The application processes untrusted post text and links, local exports, and user notes. Future AI-assisted tagging or summaries must not follow instructions embedded in posts, leak local data, or make network requests without consent. Codex Security could help review import boundaries, local web endpoints, token handling if an official API connector is added, and prompt-injection defenses. Findings would become reviewed patches and regression tests.

## How will you use API credits for your project?

I will use credits for maintainer work: improving import compatibility, generating regression tests from real anonymized fixtures, reviewing pull requests, preparing release notes, improving search and digest quality, and maintaining documentation. The product will not use X content to train models. User data will remain local by default, and generated changes will be reviewed before release.

## Anything else we should know?

The MVP deliberately avoids scraping X or automating posts, replies, likes, follows, or messages. It works with user-selected links and user-owned exports, stores data locally, and provides explicit export and deletion paths. The roadmap may add an official API connector only after reviewing X platform requirements and privacy implications.
