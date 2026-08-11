# Personal Automation

Automation and command-line tooling for recurring personal workflows.

## Purpose

Provide a reusable command layer for actions that may be invoked from:

* Raycast
* Stream Deck
* the terminal
* scheduled jobs
* other automation

Commands should represent intent rather than a specific interface or implementation.

Examples:

* `capture-thought`
* `capture-seed`
* `open-project`
* `cloud-status`
* `backup-status`

## Design

* Prefer named semantic commands over raw hotkeys or UI automation.
* Keep Stream Deck and Raycast as thin invocation layers.
* Prefer scripts for filesystem, CLI, API and infrastructure operations.
* Use Shortcuts where macOS or Apple ecosystem integration makes them the better fit.
* Keep commands small, composable and independently executable.
* Avoid embedding automation logic in individual front ends.
* Prefer boring, inspectable implementations over fragile UI automation.
* Version-control the source of truth.

## Structure

```text
.
├── docs/
│   └── commands.md
└── ...
```

`docs/commands.md` tracks the command vocabulary, including commands that have not yet been implemented.

As the repository grows, executable commands should live under `bin/` and shared implementation code under `lib/` where needed.

## Boundary

This repository defines **what I can make my environment do**.

Machine configuration belongs in `dotfiles`.

Personal infrastructure configuration belongs in `personal-cloud`.

