# Connect-Four — Multiplayer Socket Application
> CMPT 371 – Assignment 3 | Simon Fraser University

A real-time, two-player Connect-Four game built entirely on Python's **TCP Socket API**. One player runs the server; both players connect with a GUI client. All game logic lives on the server so neither client can cheat.

---

## Team Members

| Name | Student ID |
|------|-----------|
| Ha Thuy Anh (Kelly) Khuc | 301416841 |
| Kaung Si Thu | 301554181 |

---

## Video Demo

▶️ **[Watch the 2-minute demo here](https://youtu.be/PLACEHOLDER)**

---

## Architecture

```
┌──────────────┐    TCP / JSON    ┌──────────────────────────────────┐
│  GUI Client  │ ◄─────────────► │  Server  (authoritative engine)  │
│  Player Red  │                  │  • Matchmaking queue             │
└──────────────┘                  │  • Board state                   │
                                  │  • Win detection                 │
┌──────────────┐    TCP / JSON    │  • Turn enforcement              │
│  GUI Client  │ ◄─────────────► │                                  │
│ Player Yellow│                  └──────────────────────────────────┘
└──────────────┘
```

**Protocol messages (newline-delimited JSON):**

| Direction | Type | Payload |
|-----------|------|---------|
| Client → Server | `CONNECT` | Initial handshake |
| Client → Server | `MOVE` | `{ "col": <int> }` |
| Server → Client | `WELCOME` | `{ "payload": "Player X\|O" }` |
| Server → Client | `UPDATE` | `{ "board": [[...]], "turn": "X\|O", "status": "ongoing\|..." }` |

---

## Project Files

| File | Role |
|---|---|
| `server.py` | Authoritative game server — matchmaking, board logic, win detection, timestamped protocol logging |
| `gui_client.py` | Pygame GUI client with drop animations, glow effects, and HUD |
| `client.py` | Terminal fallback client (CLI, no GUI required) |
| `launcher.py` | One-click launcher — spawns server + 2 clients; streams live server logs into the launcher window |
| `test_server.py` | Unit tests for `check_winner` (30 cases across all win directions and draw) |
| `test_integration.py` | Integration tests — connects real mock clients to a live server (18 protocol tests) |
| `requirements.txt` | Python runtime dependencies |

---

## Requirements

- Python **3.9+**
- [`pygame-ce`](https://pypi.org/project/pygame-ce/) (Community Edition — drop-in replacement for pygame)

---

## Run Guide

All commands are run from inside the project folder.

### 1 — Clone the repository

```bash
git clone https://github.com/kelly2603/CMPT371_A3_Socket_App.git
cd CMPT371_A3_Socket_App
```

### 2 — Create and activate a virtual environment

```bash
python3 -m venv venv
```

**macOS / Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

### 3 — Install dependencies

```bash
python -m pip install -r requirements.txt
```

> **Note (Windows):** Use `python -m pip` instead of `pip` directly. On some Windows setups, `pip` installs packages into the system Python even when a venv is active, which causes `ModuleNotFoundError` when you run the game.

### 4 — Launch the game

#### Option A — One-click launcher (recommended)

```bash
python launcher.py
```

A window appears with the launcher controls and a live **SERVER LOG** panel at the bottom that streams all server activity in real time (connections, matchmaking, moves, and game results).

- **Launch Game** — starts the server and opens two game windows side by side.
- **Re-Launch** — kills any running processes and starts a fresh game.
- **Stop All** — terminates all spawned processes cleanly.

#### Option B — Manual launch (three separate terminals)

**Terminal 1 — Start the server:**
```bash
python server.py
```

**Terminal 2 — Player Red's client:**
```bash
python gui_client.py
```

**Terminal 3 — Player Yellow's client:**
```bash
python gui_client.py
```

#### Option C — Terminal-only (no GUI required)

```bash
# Terminal 1
python server.py

# Terminal 2
python client.py

# Terminal 3
python client.py
```

---

## How to Play

1. Both clients connect automatically and are assigned **Player Red** (moves first) or **Player Yellow**.
2. Click any **column** on the board to drop your disc.
3. First player to get **four discs in a row** (horizontal, vertical, or diagonal) wins.
4. If the board fills up with no winner, the game ends in a **Draw**.

---

## Testing

Install `pytest` first (not in `requirements.txt` since it's a dev dependency):

```bash
python -m pip install pytest
```

**Unit tests** — validates all `check_winner` logic without a running server:

```bash
python -m pytest test_server.py -v
```

**Integration tests** — spins up a real server and simulates two TCP clients end-to-end:

```bash
python -m pytest test_integration.py -v
```

Both suites also run automatically on every push and pull request to `main` via **GitHub Actions** (see `.github/workflows/tests.yml`).

---

## Limitations

| # | Limitation | Notes |
|---|-----------|-------|
| 1 | **Two players only** | The server matches exactly two clients per session. A third client connecting during a live game waits in the queue until the next session starts. |
| 2 | **Same machine / LAN only** | `HOST` is hardcoded to `127.0.0.1`. To play over a network, change `HOST` in `server.py` and `gui_client.py` to the server's LAN IP. |
| 3 | **No reconnection** | If a client disconnects mid-game, the session ends. The remaining player must re-launch. |
| 4 | **No persistence** | Game state is held in memory. Crashing the server loses all active session data. |
| 5 | **Port conflict on re-launch** | Handled via `SO_REUSEADDR`. If the port is still occupied, wait ~10 seconds and retry. |