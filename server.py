"""
CMPT 371 A3: Multiplayer Tic-Tac-Toe Server
Architecture: TCP Sockets with Multithreaded Session Management
Reference: Socket boilerplate adapted from "TCP Echo Server" tutorial.
"""

import socket
import threading
import json

# Server configuration
HOST = '127.0.0.1'
PORT = 5050

# Matchmaking Queue: Temporarily holds connected client sockets until 
# two players are available to form a GameSession.
matchmaking_queue = []

def check_winner(board):
    """
    Basic win and draw validation.
    Enforces the "Single Source of Truth" rule: the server calculates wins 
    so clients cannot cheat by modifying their local memory.
    """
    # Check Rows
    for i in range(6):
        # i = row, j = col
        # for each row, add to count and check if any player won
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
    xcount = 0
    ocount = 0
    for j in range(7):
        # i = row, j = col
        # for each col, add to count and check if any player won
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

    # Check diagonals

    # xcount = 0
    # ocount = 0
    # # i = row, j = col
    # colList = [0,1,2,3,4,5,6]
    # rowList = [0,1,2,3,4,5]
    # for x in range(3):
    #     for i in rowList:
    #         for j in colList:
    #             if board[i][j] == ' ':
    #                 continue
    #             if board[i][j] == 'X':
    #                 xcount += 1
    #                 ocount = 0
    #             else:
    #                 ocount += 1
    #                 xcount = 0

    #             if xcount >= 4: return 'X'
    #             elif ocount >= 4: return 'O'
        
    DRstartPos = [(0,0),(0,1),(0,2),(0,3),
                  (1,0),(1,1),(1,2),(1,3),
                  (2,0),(2,1),(2,2),(2,3)
                 ]
    
    URstartPos = [(3,0),(3,1),(3,2),(3,3),
                  (4,0),(4,1),(4,2),(4,3),
                  (5,0),(5,1),(5,2),(5,3)
                 ]
    
    for pos in DRstartPos:
        i, j = pos
        if board[i][j] == board[i+1][j+1] == board[i+2][j+2] == board[i+3][j+3] != ' ': return board[i][j]

    for pos in URstartPos:
        i, j = pos
        if board[i][j] == board[i-1][j+1] == board[i-2][j+2] == board[i-3][j+3] != ' ': return board[i][j]


    # Check for a draw (no empty spaces left)
    if all(cell != ' ' for row in board for cell in row): return 'Draw'
    return None

def game_session(conn_x, conn_o):
    """
    Isolated game loop for two matched players running on a background thread.
    This guarantees concurrent sessions do not block each other.
    """
    # Protocol: Assign roles using the "WELCOME" message.
    # Note: \n is appended to act as a TCP message boundary.
    conn_x.sendall((json.dumps({"type": "WELCOME", "payload": "Player X"}) + '\n').encode('utf-8'))
    conn_o.sendall((json.dumps({"type": "WELCOME", "payload": "Player O"}) + '\n').encode('utf-8'))
    
    # Initialize the authoritative game state
    board = [
        [' ', ' ', ' ', ' ', ' ', ' ', ' '], 
        [' ', ' ', ' ', ' ', ' ', ' ', ' '], 
        [' ', ' ', ' ', ' ', ' ', ' ', ' '], 
        [' ', ' ', ' ', ' ', ' ', ' ', ' '], 
        [' ', ' ', ' ', ' ', ' ', ' ', ' '], 
        [' ', ' ', ' ', ' ', ' ', ' ', ' ']
        ]
    turn = 'X'
    
    # Broadcast initial empty board to both players
    update_msg = json.dumps({"type": "UPDATE", "board": board, "turn": turn, "status": "ongoing"}) + '\n'
    conn_x.sendall(update_msg.encode('utf-8'))
    conn_o.sendall(update_msg.encode('utf-8'))
    
    # Map roles to their respective socket objects
    sockets = {'X': conn_x, 'O': conn_o}
    
    while True:
        active_socket = sockets[turn]
        # Block and wait for the active player to send their move
        data = active_socket.recv(1024).decode('utf-8')
        if not data:
            break
        
        # If multiple messages arrive buffered together in the TCP stream, 
        # we only process the first valid one using the \n boundary.
        clean_data = data.strip().split('\n')[0]
        msg = json.loads(clean_data)
        
        # Protocol: Process the "MOVE" action
        if msg["type"] == "MOVE":
            c = msg["col"]
            
            # Compute the lowest empty row in the chosen column.
            # r is initialized to None so we can safely detect a full column.
            r = None
            for i in range(5,-1,-1):
                if board[i][c] == ' ':
                    r = i
                    break
            if r is None:
                continue

            # Update authoritative state
            board[r][c] = turn  
            
            # Check for win/draw after the move
            winner = check_winner(board)
            status = "ongoing"
            if winner:
                if winner == 'Draw':
                    status = "Draw!"
                else:
                    colour = "Red" if winner == 'X' else "Yellow"
                    status = f"Player {colour} wins!"
            else:
                # Swap turns if the game is still ongoing
                turn = 'O' if turn == 'X' else 'X'
                
            # Broadcast the updated state to both clients simultaneously
            update_msg = json.dumps({"type": "UPDATE", "board": board, "turn": turn, "status": status}) + '\n'
            conn_x.sendall(update_msg.encode('utf-8'))
            conn_o.sendall(update_msg.encode('utf-8'))

            # Safety net: drain any extra buffered messages from the player who
            # just moved so that queued clicks cannot auto-play in a future turn.
            just_moved = sockets['O' if turn == 'X' else 'X']  # the player whose turn just ended
            just_moved.setblocking(False)
            try:
                while just_moved.recv(4096):
                    pass
            except:
                pass
            just_moved.setblocking(True)

            # Terminate the loop if the game has concluded
            if winner:
                break
                
    # Safely close the sockets when the session ends
    conn_x.close()
    conn_o.close()

# =================== DONT NEED TO UPDATE ======================
def start_server():
    """
    Main server event loop. Binds the socket and populates the matchmaking queue.
    """
    # Initialize an IPv4 (AF_INET) TCP (SOCK_STREAM) socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Allow immediate reuse of the port after the previous server process is killed.
    # Without this, re-launching within ~60s causes "Address already in use".
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[STARTING] Server is listening on {HOST}:{PORT}")
    
    try:
        while True:
            # Block until a new client connects
            conn, addr = server.accept()
            data = conn.recv(1024).decode('utf-8')
            
            # Protocol: Check for the initial "CONNECT" handshake
            if "CONNECT" in data:
                matchmaking_queue.append(conn)
                print(f"[QUEUE] Player added. Queue size: {len(matchmaking_queue)}")
                
                # Session Management: When 2 players are queued, match them up
                if len(matchmaking_queue) >= 2:
                    player_x = matchmaking_queue.pop(0)
                    player_o = matchmaking_queue.pop(0)
                    # Spawn an isolated GameSession thread for the matched pair
                    print("[MATCH] 2 Players found. Spawning GameSession thread.")
                    threading.Thread(target=game_session, args=(player_x, player_o)).start()
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C
        print("\n[SHUTDOWN] Server closing...")
    finally:
        server.close()

if __name__ == "__main__":
    start_server()