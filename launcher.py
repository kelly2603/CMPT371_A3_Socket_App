"""
CMPT 371 A3: Game Launcher
Spawns the server and two GUI clients; streams live server logs into the launcher window.
"""

import subprocess
import sys
import os
import time
import threading

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

pygame.init()

# ── Colors ────────────────────────────────────────────────────────────────────
BG_COLOR     = (15, 15, 30)
TITLE_COLOR  = (230, 230, 255)
BTN_COLOR    = (50, 120, 255)
BTN_HOVER    = (90, 160, 255)
BTN_TEXT     = (255, 255, 255)
STATUS_OK    = (100, 255, 150)
STATUS_ERR   = (255, 80, 80)
PANEL_BG     = (8, 10, 24)
PANEL_BORDER = (35, 48, 105)
PANEL_HDR_BG = (18, 22, 55)
HDR_COLOR    = (110, 125, 195)

# Tag → log line color
TAG_COLORS = {
    '[TCP]':       (70,  210, 255),
    '[HANDSHAKE]': (90,  255, 175),
    '[MATCH]':     (80,  255, 110),
    '[SESSION]':   (130, 215, 130),
    '[PROTOCOL]':  (155, 175, 255),
    '[RECV]':      (215, 215, 215),
    '[LOGIC]':     (255, 215, 70),
    '[SHUTDOWN]':  (255, 80,  80),
    '[ERROR]':     (255, 80,  80),
}

# ── Layout ────────────────────────────────────────────────────────────────────
WIDTH, HEIGHT   = 610, 530
PANEL_Y         = 265          # top of log panel
PANEL_H         = HEIGHT - PANEL_Y - 10
PANEL_INNER_Y   = PANEL_Y + 24  # below the header row
LOG_LINE_H      = 17
MAX_VISIBLE     = (PANEL_H - 24) // LOG_LINE_H   # lines that fit

# ── Fonts ─────────────────────────────────────────────────────────────────────
FONT_TITLE = pygame.font.SysFont("Helvetica", 28, bold=True)
FONT_BTN   = pygame.font.SysFont("Helvetica", 20, bold=True)
FONT_SUB   = pygame.font.SysFont("Helvetica", 15)
FONT_LOG   = pygame.font.SysFont("Courier New", 12)
FONT_HDR   = pygame.font.SysFont("Courier New", 11, bold=True)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Connect-4 Launcher")

PYTHON   = sys.executable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── State ─────────────────────────────────────────────────────────────────────
status_msg      = "Click Launch to start the game!"
status_is_error = False
launched        = False
processes       = []

log_lines = []        # list of (text, color)
log_lock  = threading.Lock()
MAX_LOG   = 500


def _tag_color(line):
    for tag, col in TAG_COLORS.items():
        if tag in line:
            return col
    return (165, 170, 200)


def _read_server_output(proc):
    """Background daemon thread: pipe server stdout into log_lines."""
    try:
        for raw in iter(proc.stdout.readline, b''):
            text = raw.decode('utf-8', errors='replace').rstrip()
            if text:
                with log_lock:
                    log_lines.append((text, _tag_color(text)))
                    if len(log_lines) > MAX_LOG:
                        log_lines.pop(0)
    except Exception:
        pass


def launch():
    global status_msg, status_is_error, launched, processes

    # Terminate any previously spawned processes
    for p in processes:
        try: p.terminate()
        except: pass
    processes.clear()

    try:
        # Spawn server with stdout piped so we can read its logs
        server = subprocess.Popen(
            [PYTHON, os.path.join(BASE_DIR, "server.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        processes.append(server)

        # Start background thread to stream server output
        threading.Thread(target=_read_server_output, args=(server,), daemon=True).start()

        # Give server time to bind before clients connect
        time.sleep(1.2)

        # Spawn two GUI clients
        for _ in range(2):
            client = subprocess.Popen(
                [PYTHON, os.path.join(BASE_DIR, "gui_client.py")],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            processes.append(client)
            time.sleep(0.2)

        status_msg      = "Server + 2 clients launched!"
        status_is_error = False
        launched        = True

    except Exception as e:
        status_msg      = f"Error: {e}"
        status_is_error = True


def stop():
    global status_msg, status_is_error, launched, processes
    for p in processes:
        try: p.terminate()
        except: pass
    processes.clear()
    launched        = False
    status_msg      = "Stopped all processes."
    status_is_error = False


def draw_log_panel():
    panel_rect = pygame.Rect(8, PANEL_Y, WIDTH - 16, PANEL_H)

    # Panel background
    pygame.draw.rect(screen, PANEL_BG, panel_rect, border_radius=6)

    # Header bar
    hdr_rect = pygame.Rect(8, PANEL_Y, WIDTH - 16, 22)
    pygame.draw.rect(screen, PANEL_HDR_BG, hdr_rect, border_radius=6)
    hdr_surf = FONT_HDR.render("● SERVER LOG", True, HDR_COLOR)
    screen.blit(hdr_surf, (16, PANEL_Y + 5))

    # Border
    pygame.draw.rect(screen, PANEL_BORDER, panel_rect, 1, border_radius=6)

    # Clip to content area so long lines don't overflow
    clip_rect = pygame.Rect(8, PANEL_INNER_Y, WIDTH - 16, PANEL_H - 24)
    screen.set_clip(clip_rect)

    with log_lock:
        visible = log_lines[-MAX_VISIBLE:] if len(log_lines) > MAX_VISIBLE else log_lines[:]

    y = PANEL_INNER_Y + 3
    for text, color in visible:
        surf = FONT_LOG.render(text, True, color)
        screen.blit(surf, (14, y))
        y += LOG_LINE_H

    screen.set_clip(None)


# ── Main Loop ─────────────────────────────────────────────────────────────────
clock   = pygame.time.Clock()
running = True

while running:
    screen.fill(BG_COLOR)
    mouse_pos = pygame.mouse.get_pos()

    # Title
    title = FONT_TITLE.render("Connect-4 Launcher", True, TITLE_COLOR)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, 48)))

    sub = FONT_SUB.render("Spins up 1 server + 2 GUI clients instantly", True, (145, 150, 200))
    screen.blit(sub, sub.get_rect(center=(WIDTH // 2, 80)))

    # Launch button
    launch_rect = pygame.Rect(WIDTH // 2 - 125, 110, 250, 52)
    hover = launch_rect.collidepoint(mouse_pos)
    pygame.draw.rect(screen, BTN_HOVER if hover else BTN_COLOR, launch_rect, border_radius=10)
    btn_label = "Re-Launch" if launched else "Launch Game"
    screen.blit(FONT_BTN.render(btn_label, True, BTN_TEXT),
                FONT_BTN.render(btn_label, True, BTN_TEXT).get_rect(center=launch_rect.center))

    # Stop button
    stop_rect = pygame.Rect(WIDTH // 2 - 125, 175, 250, 42)
    stop_hover = stop_rect.collidepoint(mouse_pos)
    pygame.draw.rect(screen, (200, 60, 60) if stop_hover else (155, 38, 38), stop_rect, border_radius=8)
    screen.blit(FONT_BTN.render("Stop All", True, BTN_TEXT),
                FONT_BTN.render("Stop All", True, BTN_TEXT).get_rect(center=stop_rect.center))

    # Status message
    col  = STATUS_ERR if status_is_error else STATUS_OK
    surf = FONT_SUB.render(status_msg, True, col)
    screen.blit(surf, surf.get_rect(center=(WIDTH // 2, 235)))

    # Log panel
    draw_log_panel()

    # Events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            stop()
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if launch_rect.collidepoint(mouse_pos):
                launch()
            elif stop_rect.collidepoint(mouse_pos):
                stop()

    pygame.display.update()
    clock.tick(60)

pygame.quit()
sys.exit()
