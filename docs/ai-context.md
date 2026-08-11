# AI Context

## Purpose

This repository contains semantic commands for recurring personal workflows. Terminal, Raycast, Stream Deck, and scheduled-job integrations should remain thin invocation layers.

## Boundaries

* Machine configuration belongs in `dotfiles`.
* Personal infrastructure configuration belongs in `personal-cloud`.
* Do not add secrets, credentials, or personal data.

## Conventions

* Use small, executable, kebab-case commands.
* Prefer scripts for filesystem, CLI, API, and infrastructure work.
* Use Shortcuts when Apple integration makes them a better fit.
* Prefer inspectable implementations over UI automation.
* Keep commands independent of their launch surface.
* Document command requirements, side effects, and usage in `docs/commands.md`.

## Current command

`bin/push-changes`:

1. Runs `git add -A` in the current repository.
2. Generates a commit message from the staged diff using local Ollama.
3. Lets the user accept, edit, or reject the message.
4. Commits, rebases from `origin/<branch>`, and pushes.

The default model is `qwen2.5-coder:7b`; `GIT_COMMIT_MODEL` overrides it. Preserve the interactive and all-files staging behavior unless asked to change it.

## Working guidelines

* Read the affected command and `docs/commands.md` before changing behavior.
* Preserve unrelated working-tree changes.
* Update documentation with command changes.
* Validate shell commands with `bash -n bin/<command>`.
* Do not test with a real commit, rebase, or push unless explicitly requested.
* Do not assume an undefined test, installation, release, or compatibility policy.
