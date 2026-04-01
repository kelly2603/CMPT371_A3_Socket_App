"""
CMPT 371 A3: Multiplayer Connect-Four Client (Premium GUI)
Architecture: JSON over TCP Protocol with animated Pygame rendering.

Visual features:
  - Smooth drop animation for placed pieces
  - Glowing hover preview in whichever column the mouse is over
  - Gradient dark background
  - Pulsing win-highlight on the final pieces
  - Clean HUD showing role, turn, and network status
"""

import socket
import json
import threading
import sys
import os
import math

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

HOST = '127.0.0.1'
PORT = 5050

# ── Layout ────────────────────────────────────────────────────────────────────
COLS, ROWS   = 7, 6
SQ           = 90          # cell size in pixels
RADIUS       = SQ // 2 - 6
HUD_HEIGHT   = 80          # header bar
WIN_W        = COLS * SQ   # 630
WIN_H        = ROWS * SQ + HUD_HEIGHT  # 620

# ── Colour Palette ────────────────────────────────────────────────────────────
BG_TOP       = (10,  12,  30)
BG_BOT       = (20,  25,  55)
BOARD_COL    = (18,  34,  90)
BOARD_EDGE   = (30,  55, 150)
EMPTY_COL    = (8,   14,  40)
EMPTY_EDGE   = (25,  45, 120)

RED_BASE     = (230, 55,  60)
RED_GLOW     = (255, 100, 100)
YLW_BASE     = (240, 195,  0)
YLW_GLOW     = (255, 230, 100)
WHITE        = (245, 245, 255)
GREY         = (130, 140, 170)
GREEN_TEXT   = (60,  210, 130)
YELLOW_TEXT  = (255, 215, 0)
RED_TEXT     = (255, 120, 120)
BLUE_TEXT    = (120, 140, 255)
SHADOW       = (0,   0,   0, 80)


def lerp(a, b, t):
    return a + (b - a) * t

def lerp_color(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))

def draw_gradient_rect(surface, top_color, bot_color, rect):
    """Draw a vertical gradient rectangle."""
    x, y, w, h = rect
    for i in range(h):
        t = i / max(h - 1, 1)
        color = lerp_color(top_color, bot_color, t)
        pygame.draw.line(surface, color, (x, y + i), (x + w - 1, y + i))

def draw_glowing_circle(surface, color, glow_color, center, radius, glow_radius):
    """Draw a filled circle with a soft glow halo."""
    glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
    for r in range(glow_radius, radius, -1):
        alpha = int(30 * (1 - (r - radius) / (glow_radius - radius)))
        pygame.draw.circle(glow_surf, (*glow_color, alpha), (glow_radius, glow_radius), r)
    surface.blit(glow_surf, (center[0] - glow_radius, center[1] - glow_radius))
    pygame.draw.circle(surface, color, center, radius)
    # Bright specular highlight
    highlight_pos = (center[0] - radius // 4, center[1] - radius // 4)
    highlight_r = radius // 4
    pygame.draw.circle(surface, lerp_color(color, (255, 255, 255), 0.55), highlight_pos, highlight_r)


class DropAnimation:
    """Tracks the smooth drop animation for a single piece."""
    def __init__(self, col, final_row, player):
        self.col       = col
        self.final_row = final_row
        self.player    = player
        self.y_frac    = 0.0          # 0 = top, final_row = destination
        self.speed     = 0.18         # fraction per frame (eased)
        self.done      = False

    def update(self):
        if self.done: return
        remaining = self.final_row - self.y_frac
        self.y_frac += max(remaining * 0.28, 0.4)
        if self.y_frac >= self.final_row:
            self.y_frac = self.final_row
            self.done = True


class PremiumClient:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Connect-4  ·  Multiplayer")
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        self.clock  = pygame.time.Clock()

        # Fonts
        self.font_title  = pygame.font.Font("fonts/Montserrat-SemiBold.ttf", 22)
        self.font_status = pygame.font.Font("fonts/Montserrat-SemiBold.ttf", 18)
        self.font_big    = pygame.font.Font("fonts/Montserrat-SemiBold.ttf", 32)

        # Game state (set by server messages)
        self.board      = [[' '] * COLS for _ in range(ROWS)]
        self.my_role    = None   # 'X' or 'O'
        self.turn       = None
        self.status_msg = "Connecting to server..."
        self.is_error   = False
        self.is_game_over = False

        # Animation state
        self.drop_anim    = None    # active DropAnimation, or None when idle
        self.hover_col    = None    # column index under the mouse cursor
        self.win_pulse    = 0.0     # oscillating value for the win-glow effect
        self._move_pending = False  # True while waiting for server to ack our move

        # Pre-bake the static gradient background surface
        self._bg = pygame.Surface((WIN_W, WIN_H))
        draw_gradient_rect(self._bg, BG_TOP, BG_BOT, (0, 0, WIN_W, WIN_H))

        # Sounds
        pygame.mixer.init()
        self.drop_sound = pygame.mixer.Sound("sounds/drop.mp3")
        self.win_sound  = pygame.mixer.Sound("sounds/win.mp3")
        self.lose_sound = pygame.mixer.Sound("sounds/lose.mp3")
        self._endgame_sound_played = False

        # Network
        self._connect()

    # ── Networking ──────────────────────────────────────────────────────────

    def _connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((HOST, PORT))
            self.sock.sendall((json.dumps({"type": "CONNECT"}) + '\n').encode())
            self.status_msg = "Connected — waiting for opponent…"
            threading.Thread(target=self._listen, daemon=True).start()
        except Exception as e:
            self.status_msg = f"Cannot connect: {e}"
            self.is_error   = True

    def _listen(self):
        """Background thread: reads JSON lines from the server."""
        buf = ""
        try:
            while True:
                chunk = self.sock.recv(2048).decode()
                if not chunk:
                    # Only show disconnect if the game didn't already end cleanly
                    if not self.is_game_over:
                        self.status_msg = "Server disconnected."
                    break
                buf += chunk
                while '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    if line.strip():
                        self._handle(json.loads(line))
        except Exception as e:
            if not self.is_game_over:
                self.status_msg = f"Network error: {e}"

    def _handle(self, msg):
        """Process incoming server message (called from listener thread)."""
        if msg["type"] == "WELCOME":
            self.my_role    = msg["payload"][-1]   # 'X' or 'O'
            colour_name     = "Red" if self.my_role == 'X' else "Yellow"
            self.status_msg = f"You are Player {colour_name}"

        elif msg["type"] == "UPDATE":
            new_board = msg["board"]

            # Detect which cell changed so we can animate it
            for r in range(ROWS):
                for c in range(COLS):
                    if new_board[r][c] != self.board[r][c] and new_board[r][c] != ' ':
                        self.drop_anim = DropAnimation(c, r, new_board[r][c])
                    
                    if new_board[r][c] == self.my_role:
                        self.drop_sound.play()

            self.board         = new_board
            self.turn          = msg["turn"]
            status_raw         = msg["status"]
            self.is_error      = False
            self._move_pending = False   # Server acknowledged our move; unlock input

            if status_raw != "ongoing":
                self.is_game_over = True
                self.status_msg   = status_raw
                self.is_error     = False

                # PLay sound
                if not self._endgame_sound_played:
                    if "won" in self.status_msg: 
                        self.win_sound.play()
                    elif "lost" in self.status_msg:
                        self.lose_sound.play()
                    self._endgame_sound_played = True
            elif self.turn == self.my_role:
                self.status_msg = "Your turn — click a column!"
                self.is_error   = False
            else:
                self.status_msg = "Opponent's turn…"
                self.is_error   = False

    def _send_move(self, col):
        """Send a MOVE message to the server."""
        # Block clicks only while an animation is actively running (not None and not finished)
        anim_in_progress = self.drop_anim is not None and not self.drop_anim.done
        if self.turn != self.my_role or self.is_game_over or anim_in_progress or self._move_pending:
            return
        try:
            msg = json.dumps({"type": "MOVE", "col": col}) + '\n'
            self.sock.sendall(msg.encode())
            self._move_pending = True   # Lock out further clicks until server responds
            self.status_msg = "Move sent…"
        except Exception as e:
            self.status_msg = f"Send error: {e}"

    # ── Drawing helpers ────────────────────────────────────────────────────

    def _disc_color(self, player):
        return (RED_BASE, RED_GLOW) if player == 'X' else (YLW_BASE, YLW_GLOW)

    def _col_center_x(self, c):
        return c * SQ + SQ // 2

    def _row_center_y(self, r):
        return HUD_HEIGHT + r * SQ + SQ // 2

    def _draw_hud(self):
        """Draw the top status bar."""
        pygame.draw.rect(self.screen, (12, 16, 45), (0, 0, WIN_W, HUD_HEIGHT))
        pygame.draw.line(self.screen, BOARD_EDGE, (0, HUD_HEIGHT - 1), (WIN_W, HUD_HEIGHT - 1), 2)

        # Role badge on the left
        if self.my_role:
            c, g = self._disc_color(self.my_role)
            colour_name = "Red" if self.my_role == 'X' else "Yellow"
            pygame.draw.circle(self.screen, c, (32, HUD_HEIGHT // 2), 16)
            r_text = self.font_status.render(f"Player {colour_name}", True, WHITE)
            self.screen.blit(r_text, (56, HUD_HEIGHT // 2 - r_text.get_height() // 2))

        # Status message centred
        if not self.is_game_over:
            if self.is_error:
                col = RED_TEXT
            else:
                col = BLUE_TEXT
            surf = self.font_status.render(self.status_msg, True, col)
            self.screen.blit(surf, surf.get_rect(center=(WIN_W // 2, HUD_HEIGHT // 2)))

    def _draw_board(self):
        """Draw the board frame and all static (non-animated) cells."""
        board_rect = pygame.Rect(0, HUD_HEIGHT, WIN_W, ROWS * SQ)

        # Board background
        pygame.draw.rect(self.screen, BOARD_COL, board_rect, border_radius=12)
        pygame.draw.rect(self.screen, BOARD_EDGE, board_rect, 3, border_radius=12)

        pulse = (math.sin(self.win_pulse) + 1) / 2   # 0-1

        for r in range(ROWS):
            for c in range(COLS):
                cx = self._col_center_x(c)
                cy = self._row_center_y(r)
                val = self.board[r][c]

                # Skip cell being animated — it'll be drawn as the falling disc
                if (self.drop_anim and not self.drop_anim.done
                        and c == self.drop_anim.col and r == self.drop_anim.final_row):
                    val = ' '

                if val == ' ':
                    # Hover-column highlight: show a faint preview disc
                    if self.hover_col == c and self.turn == self.my_role and not self.is_game_over:
                        base, glow = self._disc_color(self.my_role)
                        preview = lerp_color(EMPTY_COL, base, 0.18)
                        pygame.draw.circle(self.screen, preview, (cx, cy), RADIUS)
                        pygame.draw.circle(self.screen, EMPTY_EDGE, (cx, cy), RADIUS, 2)
                    else:
                        pygame.draw.circle(self.screen, EMPTY_COL, (cx, cy), RADIUS)
                        pygame.draw.circle(self.screen, EMPTY_EDGE, (cx, cy), RADIUS, 2)
                else:
                    base, glow_c = self._disc_color(val)
                    r_draw = RADIUS
                    if self.is_game_over:
                        # Pulse all placed pieces on game-over
                        r_draw = RADIUS + int(pulse * 4)
                        base = lerp_color(base, glow_c, pulse * 0.5)
                    draw_glowing_circle(self.screen, base, glow_c, (cx, cy), r_draw, r_draw + 8)

    def _draw_drop_animation(self):
        """Draw the currently falling disc (if any)."""
        anim = self.drop_anim
        if anim is None or anim.done:
            return
        c  = anim.col
        cx = self._col_center_x(c)
        # Interpolate y from just above the board (row -1) to final_row
        cy = self._row_center_y(anim.y_frac)
        base, glow = self._disc_color(anim.player)
        draw_glowing_circle(self.screen, base, glow, (int(cx), int(cy)), RADIUS, RADIUS + 8)

    def _draw_game_over_overlay(self):
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # Game over text
        if "won" in self.status_msg:
            text = self.font_big.render(self.status_msg, True, GREEN_TEXT)
        elif "lost" in self.status_msg:
            text = self.font_big.render(self.status_msg, True, RED_TEXT)
        else:
            text = self.font_big.render("Game Over", True, BLUE_TEXT)

        self.screen.blit(text, text.get_rect(center=(WIN_W // 2, WIN_H // 2)))

        # Restart / exit hint
        sub = self.font_status.render("Close window to exit", True, (200, 200, 200))
        self.screen.blit(sub, sub.get_rect(center=(WIN_W // 2, WIN_H // 2 + 40)))

    # ── Main Loop ─────────────────────────────────────────────────────────

    def run(self):
        while True:
            dt = self.clock.tick(60)

            # ── Events ──
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    try: self.sock.close()
                    except: pass
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.MOUSEMOTION:
                    mx = event.pos[0]
                    self.hover_col = mx // SQ if mx < WIN_W else None

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if event.pos[1] > HUD_HEIGHT:   # Click is on the board
                        col = event.pos[0] // SQ
                        if 0 <= col < COLS:
                            self._send_move(col)

            # ── Update ──
            if self.drop_anim and not self.drop_anim.done:
                self.drop_anim.update()
            # Clear finished animation so it no longer blocks future moves
            if self.drop_anim and self.drop_anim.done:
                self.drop_anim = None

            if self.is_game_over:
                self.win_pulse += 0.06

            # ── Render ──
            self.screen.blit(self._bg, (0, 0))
            self._draw_hud()
            self._draw_board()
            self._draw_drop_animation()
            if self.is_game_over:
                self._draw_game_over_overlay()
            pygame.display.flip()


if __name__ == "__main__":
    PremiumClient().run()
