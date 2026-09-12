# Focus Rails

Minimal side panels for focused work on an ultrawide display.

The rails are deliberately low-contrast and peripheral. They should be useful when glanced at, but never compete with the primary application.

## Layout

```text
[ left rail ] [ primary task window ] [ right rail ]
```

### Left rail

Context for the current task:

- WHAT
- WHY
- DONE WHEN
- NEXT

All fields are editable and persisted locally.

### Right rail

Session state and temporary working memory:

- count-up focus timer
- start / pause / reset
- free-text scratchpad
- local persistence

## Files

```text
focus-rails/
├── left-rail.html
└── right-rail.html
```

## Intended Usage

Each rail will be installed as a standalone PWA.

Rectangle Pro owns window placement and saved layouts.

Typical workflow:

1. Open both rail PWAs.
2. Open the primary task application.
3. Apply a Rectangle Pro layout.
4. Work in the centre.
5. Use the rails only when context or scratch space is needed.

## Design Rules

- Centre application remains visually dominant.
- Rails use deliberately muted contrast.
- No notifications.
- No feeds.
- No dynamic dashboards.
- No unnecessary controls.
- Local-first.
- No build system unless one becomes necessary.

## Ownership

```text
Rectangle Pro → geometry and workstates
Focus Rails   → peripheral context and scratch
Browser/PWA   → runtime
localStorage  → persistence
```

The rails are support surfaces, not secondary applications.

