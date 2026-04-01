# CMPT 371 A3 - Connect-Four GUI Client

import socket
import json
import threading
import sys

import pygame

HOST = '127.0.0.1'
PORT = 5050

COLS, ROWS = 7, 6
SQ = 90
RADIUS = SQ // 2 - 8
HUD_HEIGHT = 60
WIN_W = COLS * SQ
WIN_H = ROWS * SQ + HUD_HEIGHT

# basic colours
BG_COLOR = (30, 30, 50)
BOARD_COLOR = (20, 40, 100)
EMPTY_COLOR = (10, 15, 40)
RED_COLOR = (220, 50, 50)
YLW_COLOR = (230, 190, 0)
WHITE = (240, 240, 240)
GREY = (140, 140, 160)


class GameClient:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("Connect Four")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 20)
        self.font_big = pygame.font.SysFont("Arial", 28, bold=True)

        self.board = [[' '] * COLS for _ in range(ROWS)]
        self.my_role = None
        self.turn = None
        self.status_msg = "Connecting..."
        self.is_game_over = False

        self._move_pending = False

        self._connect()

    def _connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((HOST, PORT))
            self.sock.sendall((json.dumps({"type": "CONNECT"}) + '\n').encode('utf-8'))
            t = threading.Thread(target=self._listen, daemon=True)
            t.start()
        except Exception as e:
            self.status_msg = f"Connection failed: {e}"

    def _listen(self):
        try:
            while True:
                data = self.sock.recv(2048).decode('utf-8')
                if not data:
                    break
                # just split on newlines and handle each message
                # might miss messages if they arrive together but works for now
                for line in data.strip().split('\n'):
                    if line:
                        self._handle(json.loads(line))
        except Exception as e:
            self.status_msg = f"Disconnected: {e}"

    def _handle(self, msg):
        if msg["type"] == "WELCOME":
            self.my_role = msg["payload"]
            self.status_msg = f"You are {self.my_role}. Waiting for opponent..."

        elif msg["type"] == "UPDATE":
            self.board = msg["board"]
            self.turn = msg["turn"]
            self.status_msg = msg["status"]
            self._move_pending = False

            if msg["status"] != "ongoing":
                self.is_game_over = True

    def _send_move(self, col):
        if self._move_pending or self.is_game_over:
            return
        my_token = 'X' if self.my_role == "Player X" else 'O'
        if self.turn != my_token:
            return
        self._move_pending = True
        self.sock.sendall((json.dumps({"type": "MOVE", "col": col}) + '\n').encode('utf-8'))

    def _draw(self):
        self.screen.fill(BG_COLOR)

        # draw hud
        hud_surf = pygame.Surface((WIN_W, HUD_HEIGHT))
        hud_surf.fill((15, 20, 45))
        self.screen.blit(hud_surf, (0, 0))

        # status text
        color = WHITE
        if self.is_game_over:
            color = (100, 220, 100)
        status_surf = self.font.render(self.status_msg, True, color)
        self.screen.blit(status_surf, (10, HUD_HEIGHT // 2 - status_surf.get_height() // 2))

        # draw board background
        board_rect = pygame.Rect(0, HUD_HEIGHT, WIN_W, ROWS * SQ)
        pygame.draw.rect(self.screen, BOARD_COLOR, board_rect)

        # draw cells
        for row in range(ROWS):
            for col in range(COLS):
                cx = col * SQ + SQ // 2
                cy = HUD_HEIGHT + row * SQ + SQ // 2
                cell = self.board[row][col]

                if cell == 'X':
                    color = RED_COLOR
                elif cell == 'O':
                    color = YLW_COLOR
                else:
                    color = EMPTY_COLOR

                pygame.draw.circle(self.screen, color, (cx, cy), RADIUS)

        pygame.display.flip()

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.MOUSEBUTTONDOWN and not self.is_game_over:
                    mx, my = event.pos
                    if my > HUD_HEIGHT:
                        col = mx // SQ
                        self._send_move(col)

            self._draw()
            self.clock.tick(30)


if __name__ == "__main__":
    GameClient().run()
