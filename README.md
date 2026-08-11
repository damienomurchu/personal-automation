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
│   ├── ai-context.md
│   └── commands.md
├── bin/
│   ├── create-raycast-wrapper
│   └── push-changes
└── raycast/
    └── generated Raycast wrappers
```

See [`docs/commands.md`](docs/commands.md) for command usage and [`docs/ai-context.md`](docs/ai-context.md) for agent context.

Shared implementation code should live under `lib/` where needed.

## Usage

Run commands directly or add `bin/` to `PATH`:

```sh
/path/to/personal-automation/bin/push-changes
```

To expose a command from `bin/` in Raycast, generate a thin wrapper for it:

```sh
bin/create-raycast-wrapper cloud-status
```

Then add the repository's `raycast/` directory to Raycast's Script Commands search paths.

## Boundary

This repository defines **what I can make my environment do**.

Machine configuration belongs in `dotfiles`.

Personal infrastructure configuration belongs in `personal-cloud`.
