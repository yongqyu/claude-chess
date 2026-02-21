# claude-chess

A Claude Code plugin that turns Claude into an interactive chess coach with
ANSI terminal board, adaptive AI, ELO tracking, and real-time coaching.

<img width="1242" height="929" alt="image" src="https://github.com/user-attachments/assets/5a86f087-5329-434d-ae4f-70db7173aab0" />

## Installation

### Option A — Claude Code commands (preferred)

```
/plugin marketplace add yongqyu/claude-chess
/plugin install chess-coach@claude-chess
```

### Option B — Install script (if Option A doesn't work)

```bash
curl -fsSL https://raw.githubusercontent.com/yongqyu/claude-chess/main/install.sh | bash
```

Or clone and run locally:

```bash
git clone https://github.com/yongqyu/claude-chess.git
bash claude-chess/install.sh
```

### Finish setup

```bash
pip install chess --break-system-packages -q   # Python dependency (once)
```

Start a new Claude Code session and say:

> "Let's play chess"

## What's Included

| Plugin | Description |
|--------|-------------|
| `chess-coach` | Full chess game with coaching, ELO tracking, and adaptive difficulty |

## License

MIT
