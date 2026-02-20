# How to Play — Chess Coach

## Making a Move

Just type your move in the chat. Claude accepts three formats:

### 1. Standard Algebraic Notation (SAN) — most common

**Pawn moves** — type the destination square:

| You type | Meaning |
|----------|---------|
| `e4` | Move the e-pawn to e4 |
| `d4` | Move the d-pawn to d4 |
| `exd5` | Pawn on e captures on d5 |

**Piece moves** — capital letter + destination square:

| Letter | Piece | Example | Meaning |
|--------|-------|---------|---------|
| `N` | Knight | `Nf3` | Knight to f3 |
| `B` | Bishop | `Bc4` | Bishop to c4 |
| `R` | Rook | `Re1` | Rook to e1 |
| `Q` | Queen | `Qd3` | Queen to d3 |
| `K` | King | `Ke2` | King to e2 |

**Special moves:**

| You type | Meaning |
|----------|---------|
| `O-O` | Castle kingside (short) |
| `O-O-O` | Castle queenside (long) |
| `Nxe5` | Knight captures on e5 |
| `e8=Q` | Pawn promotes to Queen |

### 2. UCI Notation — from-square + to-square

| You type | Meaning |
|----------|---------|
| `e2e4` | Pawn from e2 to e4 |
| `g1f3` | Knight from g1 to f3 |

### 3. Natural language — just describe it

| You say | What happens |
|---------|-------------|
| `pawn to e4` | Moves the e-pawn to e4 |
| `knight to f3` | Moves a knight to f3 |
| `castle kingside` | Kingside castling |
| `queenside castle` | Queenside castling |

---

## Reading the Board

```
    a   b   c   d   e   f   g   h
  ┌───┬───┬───┬───┬───┬───┬───┬───┐
8 │ ♜ │ ♞ │ ♝ │ ♛ │ ♚ │ ♝ │ ♞ │ ♜ │   ← Black pieces
  ├───┼───┼───┼───┼───┼───┼───┼───┤
7 │ ♟ │ ♟ │ ♟ │ ♟ │ ♟ │ ♟ │ ♟ │ ♟ │   ← Black pawns
  ...
2 │ ♙ │ ♙ │ ♙ │ ♙ │ ♙ │ ♙ │ ♙ │ ♙ │   ← White pawns
  ├───┼───┼───┼───┼───┼───┼───┼───┤
1 │ ♖ │ ♘ │ ♗ │ ♕ │ ♔ │ ♗ │ ♘ │ ♖ │   ← White pieces
  └───┴───┴───┴───┴───┴───┴───┴───┘
    a   b   c   d   e   f   g   h
```

- **Files** (columns): a–h, left to right
- **Ranks** (rows): 1–8, White starts at 1–2, Black at 7–8
- Each square is named file + rank: `e4`, `g7`, `b1`, etc.

### Piece symbols

| White | Black | Piece |
|-------|-------|-------|
| ♔ | ♚ | King |
| ♕ | ♛ | Queen |
| ♖ | ♜ | Rook |
| ♗ | ♝ | Bishop |
| ♘ | ♞ | Knight |
| ♙ | ♟ | Pawn |

---

## Coaching Feedback

After each move Claude shows:

- **Move quality**: ✨ Brilliant / ✅ Good / ⚠️ Inaccuracy / ❌ Mistake / 💀 Blunder
- **Win rate**: White's estimated winning probability
- **Best alternative**: If a better move existed, Claude suggests it
- **Opening name**: Detected once enough moves are played
- **Warnings**: Undefended pieces, checks, threats

---

## Game Modes

| Mode | How it works |
|------|-------------|
| **Play** | You and the AI alternate moves with coaching after each |
| **Coach** | Claude suggests moves and explains before you commit |

---

## Difficulty Levels

| Level | What the AI does |
|-------|-----------------|
| **Beginner** | Plays shallow, occasionally blunders on purpose |
| **Intermediate** | Solid play, 2-move lookahead |
| **Advanced** | Stronger play, 3-move lookahead |

Difficulty auto-adjusts after each game based on your ELO estimate.

---

## ELO Tracking

After each game, Claude estimates your ELO based on:
- **ACPL** (Average Centipawn Loss) — how far your moves deviated from best
- **Blunder rate** — how often you dropped 1.5+ pawns in a move

Your ELO history is saved to `~/.chess_coach/profile.json` and used to
recommend the right difficulty for your next game.
