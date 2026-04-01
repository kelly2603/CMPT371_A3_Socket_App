# CMPT 371 A3 - Connect-Four Server

import socket
import threading
import json

HOST = '127.0.0.1'
PORT = 5050

lobby = []


def check_winner(board):
    # check rows
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

    # check columns
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

    # TODO: add diagonal checks

    # draw check
    if all(cell != ' ' for row in board for cell in row):
        return 'Draw'
    return None


def run_game(sock_red, addr_red, sock_yel, addr_yel):
    print(f"game started: {addr_red} vs {addr_yel}")

    sock_red.sendall((json.dumps({"type": "WELCOME", "payload": "Player X"}) + '\n').encode('utf-8'))
    sock_yel.sendall((json.dumps({"type": "WELCOME", "payload": "Player O"}) + '\n').encode('utf-8'))

    board = [[' '] * 7 for _ in range(6)]
    turn = 'X'

    update_msg = json.dumps({"type": "UPDATE", "board": board, "turn": turn, "status": "ongoing"}) + '\n'
    sock_red.sendall(update_msg.encode('utf-8'))
    sock_yel.sendall(update_msg.encode('utf-8'))

    conns = {'X': sock_red, 'O': sock_yel}

    while True:
        cur_sock = conns[turn]
        try:
            data = cur_sock.recv(1024).decode('utf-8')
        except (ConnectionResetError, OSError):
            print("a player disconnected, ending game")
            break
        if not data:
            break

        first_line = data.strip().split('\n')[0]
        msg = json.loads(first_line)

        if msg["type"] == "MOVE":
            c = msg["col"]

            # gravity: find bottom-most empty row
            r = None
            for i in range(5, -1, -1):
                if board[i][c] == ' ':
                    r = i
                    break

            if r is None:
                print(f"column {c} full, skipping")
                continue

            board[r][c] = turn
            winner = check_winner(board)
            status = "ongoing"

            if winner:
                if winner == 'Draw':
                    status = "It's a Draw!"
                else:
                    status = f"Player {winner} wins!"
                print(f"winner: {winner}")
            else:
                turn = 'O' if turn == 'X' else 'X'

            # send same status to both for now
            update_msg = json.dumps({"type": "UPDATE", "board": board, "turn": turn, "status": status}) + '\n'
            sock_red.sendall(update_msg.encode('utf-8'))
            sock_yel.sendall(update_msg.encode('utf-8'))

            if winner:
                break

    sock_red.close()
    sock_yel.close()


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"listening on {HOST}:{PORT}")

    try:
        while True:
            conn, addr = server.accept()
            print(f"connected: {addr}")
            data = conn.recv(1024).decode('utf-8')

            if "CONNECT" in data:
                lobby.append((conn, addr))
                print(f"lobby size: {len(lobby)}")

                if len(lobby) >= 2:
                    red_sock, addr_red = lobby.pop(0)
                    yel_sock, addr_yel = lobby.pop(0)
                    print("matched 2 players, starting game thread")
                    threading.Thread(target=run_game, args=(red_sock, addr_red, yel_sock, addr_yel)).start()

    except KeyboardInterrupt:
        print("shutting down")
    finally:
        server.close()


if __name__ == "__main__":
    start_server()
