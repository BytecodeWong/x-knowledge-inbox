# Contributing

Thanks for helping improve `x-knowledge-inbox`.

1. Create a focused issue describing the risk or false positive.
2. Add a regression test for every behavior change.
3. Keep the MVP local-first and dependency-free at runtime.
4. Run `PYTHONPATH=src python -m unittest discover -s tests -v` before opening a pull request.

Security-sensitive changes should be discussed privately first; see `SECURITY.md`.
