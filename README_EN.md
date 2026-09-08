# Research Workbench Assistant

[简体中文](README.md) · [Getting started (Chinese)](docs/GETTING_STARTED.md)

Keep research progress in your project after an AI conversation ends.

**v0.1.0-alpha.6** is an early local Codex Skill with a standard-library Python helper. It supports research records, checkpoints, versioned notes, and online Crossref discovery with a separate candidate queue. Instructions and generated views currently use Chinese; Codex can explain them in your preferred language.

Tasks now support todo/in_progress/done/cancelled, independently of research certainty. Completion requires evidence. The tasks command defaults to open tasks, while TASKS.md groups all current tasks. Older tasks remain unspecified, not assumed completed. Resume uses bounded summaries and source links rather than embedding paper notes. Back up existing workbenches, then render with the updated helper.

## Install

Requires local Codex, Python 3.10+, and Git. No extra Python dependencies or API key for the helper; your Codex account and usage limits still apply.

```sh
git clone https://github.com/z-liu-xiugou/research-workbench-assistant.git
cd research-workbench-assistant
python -X utf8 scripts/install.py
```

Installs only research-workbench into your user .agents/skills directory and refuses to overwrite existing skills. For project-local installation, pass --dest /path/to/project/.agents/skills. Restart Codex if discovery does not refresh. See [official documentation](https://learn.chatgpt.com/docs/build-skills).

Open your research project in Codex:

```text
$research-workbench Initialize a research workbench here. Ask about my research goal; do not invent progress or overwrite existing records.
```

After meaningful work, ask it to save progress, evidence and a checkpoint. In a new conversation:

```text
$research-workbench Resume from the saved checkpoint and only load evidence relevant to today's task.
```

## Boundaries

Built-in online discovery currently supports Crossref only. There is no PDF downloader/parser, other bundled search provider, Zotero integration, scheduler, interactive graph UI or multi-user collaboration. Candidates and generated notes do not imply human reading.

Only discover sends explicit query parameters to Crossref; it does not upload local documents or workbench records. Other commands are local. Never include confidential research details in queries. Using Codex or external tools is not fully offline AI. Workbenches ignore records in Git by default; this does not protect already-tracked files or forced additions. Back up important data.

## Online discovery

After initializing a workbench:

```sh
python -X utf8 skills/research-workbench/scripts/workbench.py discover --root demo-workbench --query "renewable energy forecasting" --year-start 2023 --year-end 2025 --limit 10
python -X utf8 skills/research-workbench/scripts/workbench.py candidates --root demo-workbench --state all
```

Each request saves an atomic search batch: query, source URL, retrieval time, metadata, duplicates and invalid-item reasons. DOI deduplication covers the current batch, earlier candidates and existing current notes. Review with candidate-review --doi DOI --decision kept (or excluded/pending) --reason REASON. Adding an actual paper note with the same DOI marks the candidate noted, not human-read.

Crossref public access needs no API key. Fetches only the first 1–50 relevance-ranked results, not exhaustive coverage. Network errors are not empty results; no automatic retries or full-text downloads. See [workflow details](skills/research-workbench/references/discovery.md) and [Crossref documentation](https://www.crossref.org/documentation/retrieve-metadata/rest-api/).

Events are source records; views can be rebuilt. Correct records by appending a supersedes revision, not editing history. Keep manual notes in PERSONAL_NOTES.md; rendering overwrites generated views. See [record format](skills/research-workbench/references/records.md).

## Test and contribute

```sh
python -X utf8 -m unittest discover -s tests -v
```

[Issues](https://github.com/z-liu-xiugou/research-workbench-assistant/issues) · [Discussions](https://github.com/z-liu-xiugou/research-workbench-assistant/discussions) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

Apache-2.0. Independent project, not an official OpenAI product.

Paper records now support optional authors, year, DOI, venue and tags. Duplicate current DOIs are rejected; supersedes revisions retain history. PAPER_INDEX.md lists current papers. DOI validation is local and syntactic, not an existence check. Papers without DOIs are not deduplicated.

## Backup and restore

backup/restore preserve managed configuration, events, PERSONAL_NOTES.md and PROJECT_MANUAL.md. Restore validates hashes, paths and record structure before copying into a new directory; existing destinations are rejected. Backups are plaintext and exclude papers, experiment data and other custom files. Back up those separately. See the [command reference](skills/research-workbench/references/records.md).

## Explicit research links

Records support links with a target event ID, relation and reason. related queries incoming/outgoing links; graph and RELATIONS.md/JSON expose the current relationship set. References keep their exact historical target, with latest-version hints. No automatic inference, scientific validation or interactive graph UI is included.
