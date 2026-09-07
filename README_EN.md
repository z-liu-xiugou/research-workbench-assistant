# Research Workbench Assistant

[简体中文](README.md) · [Getting started (Chinese)](docs/GETTING_STARTED.md)

Keep research progress in your project after an AI conversation ends.

**v0.1.0-alpha.1** is an early local Codex Skill with a standard-library Python helper. It creates a workbench, records progress and checkpoints, keeps revision history, searches local records, and renders supplied paper notes as Markdown and JSON. Instructions and generated views currently use Chinese; Codex can explain them in your preferred language.

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

No built-in online paper search, PDF parser, DOI deduplication, Zotero integration, scheduler, graph visualization or multi-user collaboration yet. Codex may use separately available tools, but they are not bundled here. Generated notes do not mean the user has read the paper.

The helper makes no network requests. Using Codex or external tools is not fully offline AI. Workbenches ignore records in Git by default; this does not protect already-tracked files or forced additions. Back up important data.

Events are source records; views can be rebuilt. Correct records by appending a supersedes revision, not editing history. Keep manual notes in PERSONAL_NOTES.md; rendering overwrites generated views. See [record format](skills/research-workbench/references/records.md).

## Test and contribute

```sh
python -X utf8 -m unittest discover -s tests -v
```

[Issues](https://github.com/z-liu-xiugou/research-workbench-assistant/issues) · [Discussions](https://github.com/z-liu-xiugou/research-workbench-assistant/discussions) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

Apache-2.0. Independent project, not an official OpenAI product.
