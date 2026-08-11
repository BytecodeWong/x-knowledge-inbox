# Security policy

## Scope

`x-knowledge-inbox` is a local-first knowledge inbox. The MVP reads user-selected import files and stores them in a local SQLite database. It does not scrape X, execute imported text, automate X actions, or send data to a remote service.

## Reporting a vulnerability

Please open a private security advisory on GitHub when the repository is published. Include the affected version, a minimal reproduction, impact, and a proposed mitigation if available. Do not include live credentials, private X exports, or personal data in an issue or pull request.

## Limitations

Imported posts and notes are untrusted content. The MVP treats them as data only. A future AI connector must preserve this boundary, avoid executing instructions found in posts, and require explicit consent before any network request.
