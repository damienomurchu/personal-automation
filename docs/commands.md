# Commands

Implemented commands and candidates.

## Implemented

### `push-changes`

Stages all changes, generates a commit message with Ollama, asks for confirmation, commits, rebases from `origin`, and pushes the current branch.

```sh
scripts/push-changes
```

#### Requirements

* Git repository on a branch with an `origin` remote
* Bash and Ollama
* `qwen2.5-coder:7b`, or another model selected with `GIT_COMMIT_MODEL`

At the confirmation prompt:

* `y` or Enter commits and continues
* `e` edits the message
* `n` exits

`git add -A` stages all changes, including untracked files and deletions. Declining leaves them staged. A failed rebase or push leaves the local commit in place.

## Candidates

* `capture-blog-seed`
* `capture-follow-up`
* `capture-thought`
