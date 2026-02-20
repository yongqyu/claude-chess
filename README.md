# claude-chess

A Claude Code plugin that turns Claude into an interactive chess coach with
ANSI terminal board, adaptive AI, ELO tracking, and real-time coaching.

## Installation

**Step 1:** Register this repo as a plugin marketplace in Claude Code:

```
/plugin marketplace add yongqyu/claude-chess
```

**Step 2:** Install the chess-coach plugin:

```
/plugin install chess-coach@claude-chess
```

**Step 3:** Install the Python dependency (once):

```bash
pip install chess --break-system-packages -q
```

**Step 4:** Start a new Claude Code session and say:

> "Let's play chess"

## What's Included

| Plugin | Description |
|--------|-------------|
| `chess-coach` | Full chess game with coaching, ELO tracking, and adaptive difficulty |

## License

MIT
