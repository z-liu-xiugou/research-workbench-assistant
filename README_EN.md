# Research Workbench Assistant

> **Pre-alpha / open development:** This repository currently contains the product scope, architecture, reusable research-workbench templates, and implementation roadmap. It does not yet provide an installable assistant.

Research Workbench Assistant is an open-source project for graduate students and researchers who use AI across long-running research projects.

Its core idea is simple: an AI conversation ends, but a research project does not. Research goals, confirmed facts, progress, decisions, unresolved questions, experiments, literature, and artifacts should remain local, auditable, and recoverable in the next conversation.

## Problems we want to solve

- Resume research context in a new AI conversation without explaining the whole project again.
- Separate confirmed facts, work in progress, plans, candidates, unresolved questions, and AI suggestions.
- Maintain append-only work logs and structured ledgers for tasks, decisions, issues, experiments, and artifacts.
- Discover literature, maintain screening queues, and respect copyright and access controls.
- Generate synchronized human-readable Markdown notes and machine-readable JSON records.
- Build an evidence-backed memory network connecting papers, claims, methods, datasets, experiments, and research tasks.
- Rebuild readable workbench views from structured local records.

## Current status

- Product scope and architecture: available.
- Generic research-workbench templates: available.
- Migration baseline from a private working prototype: verified locally and excluded from Git.
- Installable Python package: planned.
- Literature discovery and research-memory graph: planned.
- Codex Skills and plugin distribution: planned.

See the [roadmap](docs/OPEN_SOURCE_ROADMAP.md) and [product scope](docs/PRODUCT_SCOPE.md). Most design documents are currently written in Chinese; English documentation will expand with implementation.

## Privacy and research integrity

The project will not publish users' papers, research data, private notes, credentials, or local paths. It will not bypass paywalls, authentication, CAPTCHAs, or institutional access controls. AI-generated notes are not treated as human-confirmed facts or as proof that a paper has been read.

## Contributing

The project is in early design. Real graduate-research workflows, schema proposals, cross-platform requirements, and small implementation contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## License

Apache License 2.0. See [LICENSE](LICENSE).
