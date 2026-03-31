"""
test_server.py — Unit tests for server-side game logic.

Tests check_winner() exhaustively across all win directions,
draw conditions, and non-winning states.

Run with:
    python -m pytest test_server.py -v
  or
    python test_server.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from server import check_winner

# ── Helpers ───────────────────────────────────────────────────────────────────

def empty_board():
    return [[' '] * 7 for _ in range(6)]

def place(board, pieces):
    """Place pieces directly: pieces = list of (row, col, player)."""
    for r, c, p in pieces:
        board[r][c] = p
    return board


# ── Test Class ────────────────────────────────────────────────────────────────

class TestCheckWinner(unittest.TestCase):

    # ── No winner ─────────────────────────────────────────────────────────────

    def test_empty_board_returns_none(self):
        self.assertIsNone(check_winner(empty_board()))

    def test_one_piece_no_winner(self):
        b = place(empty_board(), [(5, 3, 'X')])
        self.assertIsNone(check_winner(b))

    def test_three_in_a_row_no_winner(self):
        b = place(empty_board(), [(5, 0, 'X'), (5, 1, 'X'), (5, 2, 'X')])
        self.assertIsNone(check_winner(b))

    def test_three_in_column_no_winner(self):
        b = place(empty_board(), [(3, 0, 'O'), (4, 0, 'O'), (5, 0, 'O')])
        self.assertIsNone(check_winner(b))

    def test_gap_breaks_horizontal_run(self):
        # X X _ X — gap at col 2, should not count as 4
        b = place(empty_board(), [(5, 0, 'X'), (5, 1, 'X'), (5, 3, 'X')])
        self.assertIsNone(check_winner(b))

    def test_mixed_row_no_winner(self):
        b = place(empty_board(), [
            (5, 0, 'X'), (5, 1, 'O'), (5, 2, 'X'), (5, 3, 'O')
        ])
        self.assertIsNone(check_winner(b))

    # ── Horizontal wins ───────────────────────────────────────────────────────

    def test_horizontal_win_x_row0_cols0_3(self):
        b = place(empty_board(), [(0, c, 'X') for c in range(4)])
        self.assertEqual(check_winner(b), 'X')

    def test_horizontal_win_x_row5_cols3_6(self):
        b = place(empty_board(), [(5, c, 'X') for c in range(3, 7)])
        self.assertEqual(check_winner(b), 'X')

    def test_horizontal_win_o_row0_cols0_3(self):
        b = place(empty_board(), [(0, c, 'O') for c in range(4)])
        self.assertEqual(check_winner(b), 'O')

    def test_horizontal_win_o_row3_cols2_5(self):
        b = place(empty_board(), [(3, c, 'O') for c in range(2, 6)])
        self.assertEqual(check_winner(b), 'O')

    def test_horizontal_win_middle_row(self):
        # X wins in the middle of the board (not bottom row)
        b = place(empty_board(), [(2, c, 'X') for c in range(4)])
        self.assertEqual(check_winner(b), 'X')

    def test_horizontal_win_rightmost_cols(self):
        b = place(empty_board(), [(5, c, 'X') for c in range(3, 7)])
        self.assertEqual(check_winner(b), 'X')

    # ── Vertical wins ─────────────────────────────────────────────────────────

    def test_vertical_win_x_col0_rows2_5(self):
        b = place(empty_board(), [(r, 0, 'X') for r in range(2, 6)])
        self.assertEqual(check_winner(b), 'X')

    def test_vertical_win_x_col6_rows0_3(self):
        b = place(empty_board(), [(r, 6, 'X') for r in range(4)])
        self.assertEqual(check_winner(b), 'X')

    def test_vertical_win_o_col3_rows1_4(self):
        b = place(empty_board(), [(r, 3, 'O') for r in range(1, 5)])
        self.assertEqual(check_winner(b), 'O')

    def test_vertical_win_o_col6_rows2_5(self):
        b = place(empty_board(), [(r, 6, 'O') for r in range(2, 6)])
        self.assertEqual(check_winner(b), 'O')

    def test_vertical_win_bottom_four_rows(self):
        b = place(empty_board(), [(r, 2, 'X') for r in range(2, 6)])
        self.assertEqual(check_winner(b), 'X')

    # ── Down-right diagonal wins (↘) ─────────────────────────────────────────

    def test_diagonal_downright_x_from_0_0(self):
        # (0,0),(1,1),(2,2),(3,3)
        b = place(empty_board(), [(i, i, 'X') for i in range(4)])
        self.assertEqual(check_winner(b), 'X')

    def test_diagonal_downright_x_from_2_3(self):
        # (2,3),(3,4),(4,5),(5,6) — bottom-right corner diagonal
        b = place(empty_board(), [(2+i, 3+i, 'X') for i in range(4)])
        self.assertEqual(check_winner(b), 'X')

    def test_diagonal_downright_o_from_1_1(self):
        b = place(empty_board(), [(1+i, 1+i, 'O') for i in range(4)])
        self.assertEqual(check_winner(b), 'O')

    def test_diagonal_downright_x_boundary_max(self):
        # (2,3),(3,4),(4,5),(5,6) — last valid down-right start
        b = place(empty_board(), [(2+i, 3+i, 'X') for i in range(4)])
        self.assertEqual(check_winner(b), 'X')

    # ── Up-right diagonal wins (↗) ────────────────────────────────────────────

    def test_diagonal_upright_x_from_5_0(self):
        # (5,0),(4,1),(3,2),(2,3)
        b = place(empty_board(), [(5-i, i, 'X') for i in range(4)])
        self.assertEqual(check_winner(b), 'X')

    def test_diagonal_upright_o_from_5_0(self):
        b = place(empty_board(), [(5-i, i, 'O') for i in range(4)])
        self.assertEqual(check_winner(b), 'O')

    def test_diagonal_upright_x_from_3_3(self):
        # (3,3),(2,4),(1,5),(0,6) — top-right boundary
        b = place(empty_board(), [(3-i, 3+i, 'X') for i in range(4)])
        self.assertEqual(check_winner(b), 'X')

    def test_diagonal_upright_o_from_4_0(self):
        # (4,0),(3,1),(2,2),(1,3)
        b = place(empty_board(), [(4-i, i, 'O') for i in range(4)])
        self.assertEqual(check_winner(b), 'O')

    def test_diagonal_upright_x_boundary_max(self):
        # (5,3),(4,4),(3,5),(2,6)
        b = place(empty_board(), [(5-i, 3+i, 'X') for i in range(4)])
        self.assertEqual(check_winner(b), 'X')

    # ── Draw ──────────────────────────────────────────────────────────────────

    def test_draw_full_board_no_winner(self):
        """A completely filled board with no 4-in-a-row should return 'Draw'."""
        # Column-stripe pattern: each column uses a block of 3 X then 3 O (repeated),
        # with the column pattern shifted per column to avoid any diagonal runs.
        #   Col: 0 1 2 3 4 5 6
        # Row 0: X O X O X O X
        # Row 1: X O X O X O X
        # Row 2: X O X O X O X
        # Row 3: O X O X O X O
        # Row 4: O X O X O X O
        # Row 5: O X O X O X O
        b = []
        for r in range(6):
            row = []
            for c in range(7):
                # Each column alternates blocks: cols 0,2,4,6 → X top/O bottom; cols 1,3,5 → O top/X bottom
                if c % 2 == 0:
                    row.append('X' if r < 3 else 'O')
                else:
                    row.append('O' if r < 3 else 'X')
            b.append(row)
        self.assertEqual(check_winner(b), 'Draw')

    def test_no_draw_if_empty_cell_remains(self):
        """A board with one empty cell remaining should not be a draw."""
        # Same column-stripe pattern but with one cell emptied.
        b = []
        for r in range(6):
            row = []
            for c in range(7):
                if c % 2 == 0:
                    row.append('X' if r < 3 else 'O')
                else:
                    row.append('O' if r < 3 else 'X')
            b.append(row)
        b[5][6] = ' '   # leave one empty cell
        # Board is not full, so not a draw; no winner in this pattern either
        self.assertIsNone(check_winner(b))

    # ── Winner takes priority over draw ───────────────────────────────────────

    def test_win_detected_before_draw_on_nearly_full_board(self):
        """Even with only two cells remaining, a 4-in-a-row win is reported."""
        b = []
        for r in range(6):
            row = []
            for c in range(7):
                row.append('X' if (r + c) % 2 == 0 else 'O')
            b.append(row)
        # Force a horizontal win on row 5
        b[5][0] = 'X'
        b[5][1] = 'X'
        b[5][2] = 'X'
        b[5][3] = 'X'
        self.assertEqual(check_winner(b), 'X')

    def test_five_in_a_row_still_wins(self):
        """5 consecutive pieces should also return a win (>= 4)."""
        b = place(empty_board(), [(5, c, 'O') for c in range(5)])
        self.assertEqual(check_winner(b), 'O')


if __name__ == '__main__':
    unittest.main(verbosity=2)
