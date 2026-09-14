# Focus Rails

Minimal side panels for focused work on an ultrawide display.

The rails are deliberately low-contrast and peripheral. They should be useful when glanced at, but never compete with the primary application.

## Layout

```text
[ left rail ] [ primary task window ] [ right rail ]
```

### Left rail

Context for the current task:

* WHAT
* WHY
* DONE WHEN
* NEXT

All fields are editable and persisted locally.

### Right rail

Session state and temporary working memory:

* count-up focus timer
* start / pause / reset
* free-text scratchpad
* local persistence

## Files

```text
focus-rails/
├── install.sh
├── launchd/
│   └── net.damienmurphy.rails-server.plist
├── left.html
├── README.md
├── right.html
└── serve
```

## Runtime

The rails are static HTML pages served locally on:

```text
http://localhost:20000
```

Endpoints:

```text
http://localhost:20000/left.html
http://localhost:20000/right.html
```

The server binds only to `127.0.0.1` and is not exposed to the local network.

`launchd` owns the server lifecycle:

```text
login
  ↓
LaunchAgent
  ↓
serve
  ↓
python3 -m http.server
  ↓
localhost:20000
```

The local HTTP server exists only to let Safari install each rail as a standalone web app.

## Install

Run:

```bash
./install.sh
```

The installer:

* makes `serve` executable
* generates the machine-specific LaunchAgent configuration
* installs it under `~/Library/LaunchAgents`
* loads the LaunchAgent
* starts the local server

Verify:

```bash
curl -I http://localhost:20000/left.html
```

## Operations

Check status:

```bash
launchctl print gui/$(id -u)/net.damienmurphy.rails-server
```

Restart:

```bash
launchctl kickstart -k gui/$(id -u)/net.damienmurphy.rails-server
```

View errors:

```bash
tail -f /tmp/rails-server.err
```

Stop:

```bash
launchctl bootout gui/$(id -u)/net.damienmurphy.rails-server
```

Reinstall after changing the LaunchAgent configuration:

```bash
./install.sh
```

Changes to `left.html` or `right.html` do not require reinstalling anything.

## Intended Usage

Each rail is installed from Safari as a standalone web app using its localhost URL.

Rectangle Pro owns window placement and saved layouts.

Typical workflow:

1. Log in; `launchd` starts the local rail server.
2. Open the Left Rail and Right Rail web apps.
3. Open the primary task application.
4. Apply a Rectangle Pro layout.
5. Work in the centre.
6. Use the rails only when context or scratch space is needed.

## Design Rules

* Centre application remains visually dominant.
* Rails use deliberately muted contrast.
* No notifications.
* No feeds.
* No dynamic dashboards.
* No unnecessary controls.
* Local-first.
* No build system unless one becomes necessary.
* No application framework unless one becomes necessary.
* Infrastructure stays proportional to the problem.

## Ownership

```text
Rectangle Pro  → geometry and workstates
Focus Rails    → peripheral context and scratch
Safari Web App → standalone runtime
launchd        → local server lifecycle
http.server    → static file serving
localStorage   → persistence
```

The rails are support surfaces, not secondary applications.

