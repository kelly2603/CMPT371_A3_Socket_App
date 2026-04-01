# CMPT 371 A3 - Connect-Four Server
# Handles matchmaking, game sessions, and all game logic.

import socket
import threading
import json
import datetime

# Server configuration
HOST = '127.0.0.1'
PORT = 5050

# queue to hold connected clients waiting for an opponent
matchmaking_queue = []


def ts():
    # timestamp helper for log output
    return datetime.datetime.now().strftime("%H:%M:%S")


def check_winner(board):
    # checks rows, columns, and diagonals for a 4-in-a-row
    # also checks if the board is full (draw)
    # done server-side so clients can't mess with the result
    # Check Rows
    for i in range(6):
        xcount = 0
        ocount = 0
        for j in range(7):
            if board[i][j] == ' ':
                xcount = 0
                ocount = 0
                continue
            if board[i][j] == 'X':
                xcount += 1
                ocount = 0
            else:
                ocount += 1
                xcount = 0
            if xcount >= 4: return 'X'
            elif ocount >= 4: return 'O'

    # Check Columns
    for j in range(7):
        xcount = 0
        ocount = 0
        for i in range(6):
            if board[i][j] == ' ':
                xcount = 0
                ocount = 0
                continue
            if board[i][j] == 'X':
                xcount += 1
                ocount = 0
            else:
                ocount += 1
                xcount = 0
            if xcount >= 4: return 'X'
            elif ocount >= 4: return 'O'

    # Check diagonals (down-right)
    DRstartPos = [(0,0),(0,1),(0,2),(0,3),
                  (1,0),(1,1),(1,2),(1,3),
                  (2,0),(2,1),(2,2),(2,3)]

    # Check diagonals (up-right)
    URstartPos = [(3,0),(3,1),(3,2),(3,3),
                  (4,0),(4,1),(4,2),(4,3),
                  (5,0),(5,1),(5,2),(5,3)]

    for pos in DRstartPos:
        i, j = pos
        if board[i][j] == board[i+1][j+1] == board[i+2][j+2] == board[i+3][j+3] != ' ':
            return board[i][j]

    for pos in URstartPos:
        i, j = pos
        if board[i][j] == board[i-1][j+1] == board[i-2][j+2] == board[i-3][j+3] != ' ':
            return board[i][j]

    # Check for a draw (no empty spaces left)
    if all(cell != ' ' for row in board for cell in row):
        return 'Draw'
    return None


def game_session(conn_x, addr_x, conn_o, addr_o):
    # runs in its own thread so multiple games can happen at the same time
    x_str = f"{addr_x[0]}:{addr_x[1]}"
    o_str = f"{addr_o[0]}:{addr_o[1]}"

    print(f"[{ts()}] [SESSION] Game session started — Player X: {x_str}  |  Player O: {o_str}", flush=True)

    # send each player their role
    conn_x.sendall((json.dumps({"type": "WELCOME", "payload": "Player X"}) + '\n').encode('utf-8'))
    print(f"[{ts()}] [PROTOCOL] WELCOME -> Player X ({x_str})", flush=True)
    conn_o.sendall((json.dumps({"type": "WELCOME", "payload": "Player O"}) + '\n').encode('utf-8'))
    print(f"[{ts()}] [PROTOCOL] WELCOME -> Player O ({o_str})", flush=True)

    # set up the board and send the initial state
    board = [[' '] * 7 for _ in range(6)]
    turn = 'X'

    update_msg = json.dumps({"type": "UPDATE", "board": board, "turn": turn, "status": "ongoing"}) + '\n'
    conn_x.sendall(update_msg.encode('utf-8'))
    conn_o.sendall(update_msg.encode('utf-8'))
    print(f"[{ts()}] [PROTOCOL] initial UPDATE sent, turn=X", flush=True)

    sockets = {'X': conn_x, 'O': conn_o}
    addrs = {'X': x_str, 'O': o_str}

    while True:
        active_socket = sockets[turn]

        data = active_socket.recv(1024).decode('utf-8')
        if not data:
            break

        # take only the first JSON line in case multiple arrived together
        clean_data = data.strip().split('\n')[0]
        msg = json.loads(clean_data)

        if msg["type"] == "MOVE":
            c = msg["col"]

            # gravity: find the bottom-most open row
            r = None
            for i in range(5, -1, -1):
                if board[i][c] == ' ':
                    r = i
                    break

            if r is None:
                print(f"[{ts()}] [LOGIC] Column {c} is full — move from Player {turn} rejected", flush=True)
                continue

            print(f"[{ts()}] [RECV] MOVE from Player {turn} ({addrs[turn]}): col={c}", flush=True)

            # Update authoritative state
            board[r][c] = turn
            winner = check_winner(board)
            status_x = "ongoing"
            status_o = "ongoing"

            if winner:
                if winner == 'Draw':
                    status_x = "It's a Draw!"
                    status_o = "It's a Draw!"
                else:
                    if winner == 'X':
                        status_x = "Congratulations, you won!"
                        status_o = "You lost! Better luck next time."
                        stat = "Player X won"
                    else:
                        status_o = "Congratulations, you won!"
                        status_x = "You lost! Better luck next time."
                        stat = "Player O won"
                    
                print(f"[{ts()}] [LOGIC] Placed {turn} at (row={r}, col={c}) — result: {stat}", flush=True)
            else:
                print(f"[{ts()}] [LOGIC] Placed {turn} at (row={r}, col={c}) — win check: ongoing", flush=True)
                turn = 'O' if turn == 'X' else 'X'

            # Broadcast updated state to both clients
            update_msg_x = json.dumps({"type": "UPDATE", "board": board, "turn": turn, "status": status_x}) + '\n'
            update_msg_o = json.dumps({"type": "UPDATE", "board": board, "turn": turn, "status": status_o}) + '\n'
            conn_x.sendall(update_msg_x.encode('utf-8'))
            conn_o.sendall(update_msg_o.encode('utf-8'))

            if winner:
                print(f"[{ts()}] [PROTOCOL] Final UPDATE broadcast — status={stat}", flush=True)
            else:
                print(f"[{ts()}] [PROTOCOL] UPDATE broadcast — turn={turn}, status=ongoing", flush=True)

            # Safety net: drain any extra buffered messages from the player who just moved
            just_moved = sockets['O' if turn == 'X' else 'X']
            just_moved.setblocking(False)
            try:
                while just_moved.recv(4096):
                    pass
            except:
                pass
            just_moved.setblocking(True)

            if winner:
                break

    print(f"[{ts()}] [SESSION] Session terminated — sockets closed", flush=True)
    conn_x.close()
    conn_o.close()


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[{ts()}] [TCP] Server bound to {HOST}:{PORT} — listening for connections", flush=True)

    try:
        while True:
            conn, addr = server.accept()
            print(f"[{ts()}] [TCP] Accepted connection from {addr[0]}:{addr[1]}", flush=True)
            data = conn.recv(1024).decode('utf-8')

            if "CONNECT" in data:
                matchmaking_queue.append((conn, addr))
                print(f"[{ts()}] [HANDSHAKE] CONNECT received from {addr[0]}:{addr[1]} — queue size: {len(matchmaking_queue)}", flush=True)

                if len(matchmaking_queue) >= 2:
                    player_x, addr_x = matchmaking_queue.pop(0)
                    player_o, addr_o = matchmaking_queue.pop(0)
                    print(f"[{ts()}] [MATCH] 2 players queued — spawning GameSession thread", flush=True)
                    threading.Thread(target=game_session, args=(player_x, addr_x, player_o, addr_o)).start()

    except KeyboardInterrupt:
        print(f"[{ts()}] [SHUTDOWN] Server closing...", flush=True)
    finally:
        server.close()


if __name__ == "__main__":
    start_server()