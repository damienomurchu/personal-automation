# Commands

Implemented commands and candidates.

## Implemented

### `create-raycast-wrapper`

Creates an executable Raycast Script Command in `raycast/` for an existing command in `bin/`.

```sh
bin/create-raycast-wrapper <script-name>
```

For example:

```sh
bin/create-raycast-wrapper cloud-status
```

The generated wrapper:

* uses the source command's kebab-case or snake_case filename to create a title such as `Cloud Status`
* appears in the `Personal Automation` Raycast package
* runs in compact mode
* forwards all arguments to the source command

#### Requirements

* The repository must be located at `~/src/personal/personal-automation`.
* The named source command must exist in `bin/` and be executable.
* The target name in `raycast/` must not already exist; the command never overwrites an existing wrapper.

The command creates the `raycast/` directory when needed and marks the generated wrapper executable. Add that directory to Raycast's Script Commands search paths to make generated commands available in Raycast.

### `push-changes`

Stages all changes, generates a commit message with Ollama, asks for confirmation, commits, rebases from `origin`, and pushes the current branch.

```sh
bin/push-changes
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
