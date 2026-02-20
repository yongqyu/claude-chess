# chess-coach

Interactive chess in your terminal with real-time coaching, ELO tracking,
and an adaptive AI opponent.

## Features

- ANSI chess board rendered directly in the terminal
- Three difficulty levels: beginner, intermediate, advanced
- ELO-based adaptive difficulty (auto-calibrates after each game)
- Real-time coaching: move quality, best alternative, opening names
- Play mode and Coach mode
- Post-game review saved as Markdown

## Prerequisites

```bash
pip install chess --break-system-packages -q
```

## Usage

Once installed, start a new Claude Code session and say:

> "Let's play chess" or "I want chess coaching"

Claude will load your profile, recommend a difficulty level, and start a game.

## Game Data

All game state is stored in `~/.chess_coach/`:

```
~/.chess_coach/
  current_game.json   Active game
  profile.json        ELO history and current level
  games/              Archived completed games
  reviews/            Post-game Markdown reviews
```
