#!/usr/bin/env python3

import gi
import random
import copy
from enum import Enum
from typing import Optional, List, Tuple, Dict

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gdk, GLib, GObject, Pango

class PieceType(Enum):
    PAWN = 'p'
    KNIGHT = 'n'
    BISHOP = 'b'
    ROOK = 'r'
    QUEEN = 'q'
    KING = 'k'

class ChessWidget(Gtk.Box):
    """
    A GTK4 chess widget with intermediate AI for entertainment during installation.
    """
    
    __gsignals__ = {
        'game-over': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'user-move-made': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }
    
    # Unicode chess pieces - using filled/solid versions
    PIECES = {
        'wp': '♟', 'wn': '♞', 'wb': '♝', 'wr': '♜', 'wq': '♛', 'wk': '♚',
        'bp': '♟', 'bn': '♞', 'bb': '♝', 'br': '♜', 'bq': '♛', 'bk': '♚'
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(10)
        
        # Game state
        self.board = self._init_board()
        self.current_player = 'w'  # 'w' for white, 'b' for black
        self.selected_square = None
        self.valid_moves = []
        self.move_history = []
        self.ai_thinking = False
        self.game_over = False
        self.ai_difficulty = 3  # Search depth for minimax
        self.player_color = 'w'  # Human plays white
        self.ai_color = 'b'  # AI plays black
        self.last_move = None  # Track last move for highlighting
        
        # Castling rights
        self.castling_rights = {
            'w': {'king_side': True, 'queen_side': True},
            'b': {'king_side': True, 'queen_side': True}
        }
        
        # En passant target square
        self.en_passant_target = None
        
        self._build_ui()
        
    def _init_board(self):
        """Initialize the chess board with starting positions."""
        board = [[None for _ in range(8)] for _ in range(8)]
        
        # Place pieces
        piece_order = ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r']
        
        # Black pieces
        for i, piece in enumerate(piece_order):
            board[0][i] = ('b', piece)
            board[1][i] = ('b', 'p')
        
        # White pieces
        for i, piece in enumerate(piece_order):
            board[7][i] = ('w', piece)
            board[6][i] = ('w', 'p')
        
        return board
    
    def _build_ui(self):
        """Build the chess interface."""
        
        # Title and status
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.set_halign(Gtk.Align.CENTER)
        self.append(header_box)
        
        title = Gtk.Label()
        title.set_markup('<b>Chess While You Wait</b>')
        header_box.append(title)
        
        self.status_label = Gtk.Label(label="Your turn (White)")
        self.status_label.add_css_class('dim-label')
        header_box.append(self.status_label)
        
        # Chess board frame
        board_frame = Gtk.Frame()
        board_frame.set_halign(Gtk.Align.CENTER)
        board_frame.set_valign(Gtk.Align.CENTER)
        board_frame.set_size_request(200, 200)
        self.append(board_frame)
        
        # Board grid
        self.board_grid = Gtk.Grid()
        self.board_grid.set_column_homogeneous(True)
        self.board_grid.set_row_homogeneous(True)
        board_frame.set_child(self.board_grid)
        
        # Create board squares
        self.squares = []
        for row in range(8):
            row_squares = []
            for col in range(8):
                # Create button for each square
                button = Gtk.Button()
                button.set_size_request(50, 50)
                
                # Set square color
                if (row + col) % 2 == 0:
                    button.add_css_class('chess-white-square')
                else:
                    button.add_css_class('chess-black-square')
                
                # Connect click handler
                button.connect('clicked', self._on_square_clicked, row, col)
                
                # Add to grid
                self.board_grid.attach(button, col, row, 1, 1)
                row_squares.append(button)
            
            self.squares.append(row_squares)
        
        # Control buttons
        control_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        control_box.set_halign(Gtk.Align.CENTER)
        self.append(control_box)
        
        new_game_btn = Gtk.Button(label="New Game")
        new_game_btn.connect('clicked', self._on_new_game)
        control_box.append(new_game_btn)
        
        # Difficulty selector
        difficulty_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        control_box.append(difficulty_box)
        
        diff_label = Gtk.Label(label="AI Level:")
        difficulty_box.append(diff_label)
        
        self.difficulty_combo = Gtk.ComboBoxText()
        self.difficulty_combo.append_text("Easy")
        self.difficulty_combo.append_text("Medium")
        self.difficulty_combo.append_text("Hard")
        self.difficulty_combo.set_active(1)  # Default to Medium
        self.difficulty_combo.connect('changed', self._on_difficulty_changed)
        difficulty_box.append(self.difficulty_combo)
        
        # Add custom CSS for chess squares with Adwaita-Dark compatible colors
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            .chess-white-square {
                background-color: #5e5c64;
                border: 1px solid #3d3846;
                min-height: 25px;
                min-width: 25px;
            }
            .chess-white-square:hover:not(.chess-selected):not(.chess-in-check) {
                background-color: #6e6b73;
            }
            .chess-black-square {
                background-color: #3d3846;
                border: 1px solid #241f31;
                min-height: 25px;
                min-width: 25px;
            }
            .chess-black-square:hover:not(.chess-selected):not(.chess-in-check) {
                background-color: #4d4a53;
            }
            .chess-selected {
                background-color: #3584e4 !important;
                box-shadow: inset 0 0 0 3px #1c71d8;
            }
            .chess-valid-move {
                background-color: #2ec27e !important;
                opacity: 0.7;
            }
            .chess-valid-move:hover {
                opacity: 1.0;
            }
            .chess-valid-capture {
                background-color: #e66100 !important;
                opacity: 0.8;
            }
            .chess-valid-capture:hover {
                opacity: 1.0;
            }
            .chess-in-check {
                background-color: #c01c28 !important;
                box-shadow: inset 0 0 0 3px #a51d2d;
                animation: pulse-check 1s infinite;
            }
            @keyframes pulse-check {
                0% { box-shadow: inset 0 0 0 3px #a51d2d; }
                50% { box-shadow: inset 0 0 0 5px #e01b24; }
                100% { box-shadow: inset 0 0 0 3px #a51d2d; }
            }
            .chess-last-move {
                box-shadow: inset 0 0 0 2px #f6d32d;
            }
            .chess-piece {
                font-size: 20px;
                font-weight: normal;
                text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8),
                            -1px -1px 2px rgba(0, 0, 0, 0.8),
                            1px -1px 2px rgba(0, 0, 0, 0.8),
                            -1px 1px 2px rgba(0, 0, 0, 0.8);
            }
            .chess-piece-white {
                color: #ffffff;
                filter: drop-shadow(0 0 1px #000000);
            }
            .chess-piece-black {
                color: #2e2e2e;
                filter: drop-shadow(0 0 1px #ffffff);
            }
        """)
        
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        # Update board display
        self._update_board_display()
    
    def _is_valid_position(self, row, col):
        """Check if position is within board bounds."""
        return 0 <= row < 8 and 0 <= col < 8
    
    def _update_board_display(self):
        """Update the visual representation of the board."""
        # Check if either king is in check
        white_in_check = self._is_in_check('w')
        black_in_check = self._is_in_check('b')
        
        # Find king positions if in check
        white_king_pos = None
        black_king_pos = None
        if white_in_check or black_in_check:
            for r in range(8):
                for c in range(8):
                    if self.board[r][c]:
                        color, piece = self.board[r][c]
                        if piece == 'k':
                            if color == 'w':
                                white_king_pos = (r, c)
                            else:
                                black_king_pos = (r, c)
        
        for row in range(8):
            for col in range(8):
                button = self.squares[row][col]
                
                # Clear all previous state classes
                button.remove_css_class('chess-selected')
                button.remove_css_class('chess-valid-move')
                button.remove_css_class('chess-valid-capture')
                button.remove_css_class('chess-in-check')
                button.remove_css_class('chess-last-move')
                button.remove_css_class('chess-piece-white')
                button.remove_css_class('chess-piece-black')
                
                # Highlight last move
                if self.last_move:
                    if (row, col) in [self.last_move['from'], self.last_move['to']]:
                        button.add_css_class('chess-last-move')
                
                # Highlight king in check
                if white_in_check and (row, col) == white_king_pos:
                    button.add_css_class('chess-in-check')
                elif black_in_check and (row, col) == black_king_pos:
                    button.add_css_class('chess-in-check')
                
                # Add selection highlight (persistent)
                if self.selected_square == (row, col):
                    button.add_css_class('chess-selected')
                
                # Add valid move highlights
                if (row, col) in self.valid_moves:
                    # Check if this is a capture move
                    if self.board[row][col] and self.board[row][col][0] != self.current_player:
                        button.add_css_class('chess-valid-capture')
                    else:
                        # Check for en passant capture
                        if self.selected_square and self.board[self.selected_square[0]][self.selected_square[1]]:
                            piece = self.board[self.selected_square[0]][self.selected_square[1]]
                            if piece[1] == 'p' and self.en_passant_target == (row, col):
                                button.add_css_class('chess-valid-capture')
                            else:
                                button.add_css_class('chess-valid-move')
                        else:
                            button.add_css_class('chess-valid-move')
                
                # Set piece label with color styling
                if self.board[row][col]:
                    color, piece = self.board[row][col]
                    piece_symbol = self.PIECES.get(color + piece, '')
                    button.set_label(piece_symbol)
                    button.add_css_class('chess-piece')
                    if color == 'w':
                        button.add_css_class('chess-piece-white')
                    else:
                        button.add_css_class('chess-piece-black')
                else:
                    button.set_label('')
    
    def _on_square_clicked(self, button, row, col):
        """Handle square click events."""
        if self.game_over or self.ai_thinking or self.current_player != self.player_color:
            return
        
        if self.selected_square is None:
            # Select a piece
            if self.board[row][col] and self.board[row][col][0] == self.player_color:
                self.selected_square = (row, col)
                self.valid_moves = self._get_valid_moves(row, col)
                self._update_board_display()
        else:
            # Try to move the selected piece
            if (row, col) in self.valid_moves:
                success = self._make_move(self.selected_square[0], self.selected_square[1], row, col)
                if success:
                    self.emit('user-move-made')  # Add this line
                self.selected_square = None
                self.valid_moves = []
                self._update_board_display()
                
                # Check for game over
                if self._is_checkmate(self.ai_color):
                    self._end_game("White wins by checkmate!")
                elif self._is_stalemate(self.ai_color):
                    self._end_game("Stalemate - Draw!")
                else:
                    # Trigger AI move after a short delay
                    self.ai_thinking = True
                    self.status_label.set_text("AI thinking...")
                    GLib.timeout_add(500, self._make_ai_move)
            else:
                # Click on another piece of same color - select it instead
                if self.board[row][col] and self.board[row][col][0] == self.player_color:
                    self.selected_square = (row, col)
                    self.valid_moves = self._get_valid_moves(row, col)
                else:
                    # Deselect
                    self.selected_square = None
                    self.valid_moves = []
                
                self._update_board_display()
    
    def _make_move(self, from_row, from_col, to_row, to_col):
        """Execute a move on the board."""
        # Validate positions
        if not (self._is_valid_position(from_row, from_col) and self._is_valid_position(to_row, to_col)):
            print(f"Invalid move coordinates: ({from_row},{from_col}) -> ({to_row},{to_col})")
            return False
        
        piece = self.board[from_row][from_col]
        if not piece:
            print(f"Warning: No piece at {from_row},{from_col}")
            return False
        
        captured = self.board[to_row][to_col]
        
        # Store move in history and track as last move
        move_record = {
            'from': (from_row, from_col),
            'to': (to_row, to_col),
            'piece': piece,
            'captured': captured
        }
        self.move_history.append(move_record)
        self.last_move = move_record
        
        # Handle special moves
        if piece and piece[1] == 'k':
            # Update castling rights
            color = piece[0]
            self.castling_rights[color]['king_side'] = False
            self.castling_rights[color]['queen_side'] = False
            
            # Check for castling move
            if abs(to_col - from_col) == 2:
                # Castle - ensure rook positions are valid
                if to_col > from_col and self._is_valid_position(to_row, 7):
                    # King side
                    if self._is_valid_position(to_row, to_col - 1):
                        self.board[to_row][to_col - 1] = self.board[to_row][7]
                        self.board[to_row][7] = None
                else:
                    # Queen side
                    if self._is_valid_position(to_row, 0) and self._is_valid_position(to_row, to_col + 1):
                        self.board[to_row][to_col + 1] = self.board[to_row][0]
                        self.board[to_row][0] = None
        
        # Update castling rights if rook moves
        if piece and piece[1] == 'r':
            color = piece[0]
            if from_col == 0:
                self.castling_rights[color]['queen_side'] = False
            elif from_col == 7:
                self.castling_rights[color]['king_side'] = False
        
        # Handle en passant
        if piece and piece[1] == 'p' and to_col != from_col and captured is None:
            # This is an en passant capture - validate the capture position
            if piece[0] == 'w' and self._is_valid_position(to_row + 1, to_col):
                self.board[to_row + 1][to_col] = None
            elif piece[0] == 'b' and self._is_valid_position(to_row - 1, to_col):
                self.board[to_row - 1][to_col] = None
        
        # Update en passant target
        if piece and piece[1] == 'p' and abs(to_row - from_row) == 2:
            self.en_passant_target = (from_row + (to_row - from_row) // 2, from_col)
        else:
            self.en_passant_target = None
        
        # Make the move
        self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = None
        
        # Handle pawn promotion
        if piece and piece[1] == 'p':
            if (piece[0] == 'w' and to_row == 0) or (piece[0] == 'b' and to_row == 7):
                self.board[to_row][to_col] = (piece[0], 'q')  # Auto-promote to queen
        
        # Switch player
        self.current_player = 'b' if self.current_player == 'w' else 'w'
        
        # Update status only if game isn't over
        if not self.game_over:
            if self.current_player == self.player_color:
                self.status_label.set_text("Your turn (White)")
            else:
                self.status_label.set_text("AI thinking...")
        
        return True
    
    def _get_valid_moves(self, row, col):
        """Get all valid moves for a piece at the given position."""
        if not self.board[row][col]:
            return []
        
        color, piece = self.board[row][col]
        moves = []
        
        # Get all possible moves for the piece
        possible_moves = self._get_piece_moves(self.board, row, col, color, piece, check_castling=True)
        
        # Filter out moves that would leave king in check
        for move_row, move_col in possible_moves:
            if self._is_valid_position(move_row, move_col) and self._is_valid_move(row, col, move_row, move_col):
                moves.append((move_row, move_col))
        
        return moves
    
    def _get_piece_moves(self, board, row, col, color, piece, check_castling=True):
        """Get all possible moves for a specific piece type."""
        moves = []
        
        if piece == 'p':
            direction = -1 if color == 'w' else 1
            
            # Forward move
            if self._is_valid_position(row + direction, col):
                if board[row + direction][col] is None:
                    moves.append((row + direction, col))
                    
                    # Double move from starting position
                    start_row = 6 if color == 'w' else 1
                    if row == start_row and self._is_valid_position(row + 2 * direction, col) and board[row + 2 * direction][col] is None:
                        moves.append((row + 2 * direction, col))
            
            # Captures
            for dc in [-1, 1]:
                if self._is_valid_position(col + dc, 0) and self._is_valid_position(row + direction, 0):
                    target = board[row + direction][col + dc]
                    if target and target[0] != color:
                        moves.append((row + direction, col + dc))
                    
                    # En passant
                    if self.en_passant_target == (row + direction, col + dc):
                        moves.append((row + direction, col + dc))
        
        elif piece == 'n':
            # Knight moves
            knight_moves = [
                (-2, -1), (-2, 1), (-1, -2), (-1, 2),
                (1, -2), (1, 2), (2, -1), (2, 1)
            ]
            for dr, dc in knight_moves:
                new_row, new_col = row + dr, col + dc
                if self._is_valid_position(new_row, new_col):
                    target = board[new_row][new_col]
                    if not target or target[0] != color:
                        moves.append((new_row, new_col))
        
        elif piece in ['b', 'r', 'q']:
            # Bishop, rook, and queen moves
            directions = []
            if piece in ['r', 'q']:
                directions.extend([(0, 1), (0, -1), (1, 0), (-1, 0)])
            if piece in ['b', 'q']:
                directions.extend([(1, 1), (1, -1), (-1, 1), (-1, -1)])
            
            for dr, dc in directions:
                for i in range(1, 8):
                    new_row, new_col = row + dr * i, col + dc * i
                    if self._is_valid_position(new_row, new_col):
                        target = board[new_row][new_col]
                        if not target:
                            moves.append((new_row, new_col))
                        elif target[0] != color:
                            moves.append((new_row, new_col))
                            break
                        else:
                            break
                    else:
                        break
        
        elif piece == 'k':
            # King moves
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0:
                        continue
                    new_row, new_col = row + dr, col + dc
                    if self._is_valid_position(new_row, new_col):
                        target = board[new_row][new_col]
                        if not target or target[0] != color:
                            moves.append((new_row, new_col))
            
            # Castling (only check if flag is set to avoid recursion)
            if check_castling and not self._is_board_in_check(board, color):
                # King side
                if self.castling_rights[color]['king_side']:
                    if all(board[row][c] is None for c in range(col + 1, 7)):
                        if self._is_valid_position(row, 7) and board[row][7] and board[row][7][1] == 'r':
                            # Check if squares king passes through are not under attack
                            if not self._is_square_attacked(board, row, col + 1, color):
                                moves.append((row, col + 2))
                
                # Queen side
                if self.castling_rights[color]['queen_side']:
                    if all(board[row][c] is None for c in range(1, col)):
                        if self._is_valid_position(row, 0) and board[row][0] and board[row][0][1] == 'r':
                            # Check if squares king passes through are not under attack
                            if not self._is_square_attacked(board, row, col - 1, color):
                                moves.append((row, col - 2))
        
        return moves
    
    def _is_square_attacked(self, board, row, col, by_color):
        """Check if a square is attacked by the opposite color."""
        enemy_color = 'b' if by_color == 'w' else 'w'
        
        for r in range(8):
            for c in range(8):
                if board[r][c] and board[r][c][0] == enemy_color:
                    _, piece = board[r][c]
                    # Get moves without checking castling to avoid recursion
                    piece_moves = self._get_piece_moves(board, r, c, enemy_color, piece, check_castling=False)
                    if (row, col) in piece_moves:
                        return True
        return False
    
    def _is_valid_move(self, from_row, from_col, to_row, to_col):
        """Check if a move would leave the king in check."""
        # Make temporary move
        temp_board = copy.deepcopy(self.board)
        temp_board[to_row][to_col] = temp_board[from_row][from_col]
        temp_board[from_row][from_col] = None
        
        # Check if king would be in check
        color = self.board[from_row][from_col][0]
        return not self._is_board_in_check(temp_board, color)
    
    def _is_in_check(self, color):
        """Check if the given color's king is in check."""
        return self._is_board_in_check(self.board, color)
    
    def _is_board_in_check(self, board, color):
        """Check if a king is in check on the given board."""
        # Find king
        king_pos = None
        for r in range(8):
            for c in range(8):
                if board[r][c] and board[r][c] == (color, 'k'):
                    king_pos = (r, c)
                    break
        
        if not king_pos:
            return False
        
        # Check if any enemy piece can attack the king
        return self._is_square_attacked(board, king_pos[0], king_pos[1], color)
    
    def _is_checkmate(self, color):
        """Check if the given color is in checkmate."""
        if not self._is_in_check(color):
            return False
        
        # Try all possible moves
        for r in range(8):
            for c in range(8):
                if self.board[r][c] and self.board[r][c][0] == color:
                    moves = self._get_valid_moves(r, c)
                    if moves:
                        return False
        
        return True
    
    def _is_stalemate(self, color):
        """Check if the game is in stalemate."""
        if self._is_in_check(color):
            return False
        
        # Check if any legal moves exist
        for r in range(8):
            for c in range(8):
                if self.board[r][c] and self.board[r][c][0] == color:
                    moves = self._get_valid_moves(r, c)
                    if moves:
                        return False
        
        return True
    
    def _make_ai_move(self):
        """Make an AI move using minimax algorithm."""
        try:
            # Only proceed if it's actually the AI's turn
            if self.current_player != self.ai_color or self.game_over:
                self.ai_thinking = False
                return False
            
            best_move = self._minimax_root(self.ai_difficulty, self.ai_color)
            
            if best_move:
                from_pos, to_pos = best_move
                # Validate move before executing
                if (self._is_valid_position(from_pos[0], from_pos[1]) and 
                    self._is_valid_position(to_pos[0], to_pos[1]) and
                    self.board[from_pos[0]][from_pos[1]] is not None):
                    
                    success = self._make_move(from_pos[0], from_pos[1], to_pos[0], to_pos[1])
                    if success:
                        self._update_board_display()
                        
                        # Check for game over
                        if self._is_checkmate(self.player_color):
                            self._end_game("Black (AI) wins by checkmate!")
                        elif self._is_stalemate(self.player_color):
                            self._end_game("Stalemate - Draw!")
                    else:
                        print(f"Failed to execute AI move: {from_pos} -> {to_pos}")
                        self.current_player = self.player_color
                        self.status_label.set_text("Your turn (White)")
                else:
                    print(f"Invalid AI move generated: {from_pos} -> {to_pos}")
                    self.current_player = self.player_color  
                    self.status_label.set_text("Your turn (White)")
            else:
                # No valid moves - game over
                if self._is_in_check(self.ai_color):
                    self._end_game("White wins by checkmate!")
                else:
                    self._end_game("Stalemate - Draw!")
        except Exception as e:
            print(f"AI move error: {e}")
            import traceback
            traceback.print_exc()
            # Reset to player's turn on error
            self.current_player = self.player_color
            self.status_label.set_text("Your turn (White) - AI error occurred")
        finally:
            # Always clear the AI thinking flag
            self.ai_thinking = False
        
        return False  # Don't repeat the timeout
    
    def _minimax_root(self, depth, color):
        """Root function for minimax algorithm."""
        best_move = None
        best_value = -float('inf') if color == 'b' else float('inf')
        
        # Get all possible moves
        moves = []
        for r in range(8):
            for c in range(8):
                if self.board[r][c] and self.board[r][c][0] == color:
                    valid_moves = self._get_valid_moves(r, c)
                    for move in valid_moves:
                        moves.append(((r, c), move))
        
        if not moves:
            return None
        
        # Shuffle moves for variety
        random.shuffle(moves)
        
        # Limit number of moves to evaluate for performance (especially on higher difficulties)
        max_moves_to_evaluate = min(len(moves), 20) if depth > 3 else len(moves)
        moves = moves[:max_moves_to_evaluate]
        
        for from_pos, to_pos in moves:
            try:
                # Make temporary move
                temp_board = copy.deepcopy(self.board)
                
                # Validate positions before making move
                if (not self._is_valid_position(from_pos[0], from_pos[1]) or 
                    not self._is_valid_position(to_pos[0], to_pos[1])):
                    continue
                
                # Apply move to temp board
                temp_board[to_pos[0]][to_pos[1]] = temp_board[from_pos[0]][from_pos[1]]
                temp_board[from_pos[0]][from_pos[1]] = None
                
                # Evaluate position
                value = self._minimax(temp_board, depth - 1, -float('inf'), float('inf'), color == 'w')
                
                if color == 'b':  # AI is maximizing
                    if value > best_value:
                        best_value = value
                        best_move = (from_pos, to_pos)
                else:  # AI is minimizing (if playing white)
                    if value < best_value:
                        best_value = value
                        best_move = (from_pos, to_pos)
            except Exception as e:
                print(f"Error evaluating move {from_pos} -> {to_pos}: {e}")
                continue
        
        return best_move
    
    def _minimax(self, board, depth, alpha, beta, maximizing):
        """Minimax algorithm with alpha-beta pruning."""
        if depth == 0:
            return self._evaluate_board(board)
        
        try:
            if maximizing:
                max_eval = -float('inf')
                move_found = False
                for r in range(8):
                    for c in range(8):
                        if board[r][c] and board[r][c][0] == 'b':
                            moves = self._get_valid_moves_for_board(board, r, c)
                            for move in moves:
                                if not self._is_valid_position(move[0], move[1]):
                                    continue
                                    
                                move_found = True
                                temp_board = copy.deepcopy(board)
                                temp_board[move[0]][move[1]] = temp_board[r][c]
                                temp_board[r][c] = None
                                
                                eval_score = self._minimax(temp_board, depth - 1, alpha, beta, False)
                                max_eval = max(max_eval, eval_score)
                                alpha = max(alpha, eval_score)
                                
                                if beta <= alpha:
                                    return max_eval
                
                # If no moves found, return current evaluation
                if not move_found:
                    max_eval = self._evaluate_board(board)
                
                return max_eval
            else:
                min_eval = float('inf')
                move_found = False
                for r in range(8):
                    for c in range(8):
                        if board[r][c] and board[r][c][0] == 'w':
                            moves = self._get_valid_moves_for_board(board, r, c)
                            for move in moves:
                                if not self._is_valid_position(move[0], move[1]):
                                    continue
                                    
                                move_found = True
                                temp_board = copy.deepcopy(board)
                                temp_board[move[0]][move[1]] = temp_board[r][c]
                                temp_board[r][c] = None
                                
                                eval_score = self._minimax(temp_board, depth - 1, alpha, beta, True)
                                min_eval = min(min_eval, eval_score)
                                beta = min(beta, eval_score)
                                
                                if beta <= alpha:
                                    return min_eval
                
                # If no moves found, return current evaluation
                if not move_found:
                    min_eval = self._evaluate_board(board)
                
                return min_eval
        except Exception as e:
            print(f"Minimax error at depth {depth}: {e}")
            return self._evaluate_board(board)
    
    def _get_valid_moves_for_board(self, board, row, col):
        """Get valid moves for a piece on a specific board state."""
        if not board[row][col]:
            return []
        
        color, piece = board[row][col]
        moves = []
        
        # Get all possible moves for the piece
        possible_moves = self._get_piece_moves(board, row, col, color, piece, check_castling=False)
        
        # Filter out moves that would leave king in check
        for move_row, move_col in possible_moves:
            if (self._is_valid_position(move_row, move_col) and 
                self._is_valid_move_for_board(board, row, col, move_row, move_col)):
                moves.append((move_row, move_col))
        
        return moves
    
    def _is_valid_move_for_board(self, board, from_row, from_col, to_row, to_col):
        """Check if a move would leave the king in check on a specific board."""
        # Make temporary move
        temp_board = copy.deepcopy(board)
        temp_board[to_row][to_col] = temp_board[from_row][from_col]
        temp_board[from_row][from_col] = None
        
        # Check if king would be in check
        color = board[from_row][from_col][0]
        return not self._is_board_in_check(temp_board, color)
    
    def _evaluate_board(self, board):
        """Evaluate the board position."""
        piece_values = {
            'p': 10, 'n': 30, 'b': 30, 'r': 50, 'q': 90, 'k': 900
        }
        
        # Position bonus tables (simplified)
        pawn_table = [
            [0,  0,  0,  0,  0,  0,  0,  0],
            [5, 10, 10,-20,-20, 10, 10,  5],
            [5, -5,-10,  0,  0,-10, -5,  5],
            [0,  0,  0, 20, 20,  0,  0,  0],
            [5,  5, 10, 25, 25, 10,  5,  5],
            [10, 10, 20, 30, 30, 20, 10, 10],
            [50, 50, 50, 50, 50, 50, 50, 50],
            [0,  0,  0,  0,  0,  0,  0,  0]
        ]
        
        knight_table = [
            [-50,-40,-30,-30,-30,-30,-40,-50],
            [-40,-20,  0,  5,  5,  0,-20,-40],
            [-30,  5, 10, 15, 15, 10,  5,-30],
            [-30,  0, 15, 20, 20, 15,  0,-30],
            [-30,  5, 15, 20, 20, 15,  5,-30],
            [-30,  0, 10, 15, 15, 10,  0,-30],
            [-40,-20,  0,  0,  0,  0,-20,-40],
            [-50,-40,-30,-30,-30,-30,-40,-50]
        ]
        
        score = 0
        for r in range(8):
            for c in range(8):
                if board[r][c]:
                    color, piece = board[r][c]
                    value = piece_values.get(piece, 0)
                    
                    # Add position bonus
                    if piece == 'p':
                        if color == 'w':
                            value += pawn_table[7-r][c]
                        else:
                            value += pawn_table[r][c]
                    elif piece == 'n':
                        if color == 'w':
                            value += knight_table[7-r][c]
                        else:
                            value += knight_table[r][c]
                    
                    if color == 'b':
                        score += value
                    else:
                        score -= value
        
        return score
    
    def _end_game(self, message):
        """End the game and show result."""
        self.game_over = True
        self.ai_thinking = False
        self.status_label.set_text(message)
        self.emit('game-over', message)
    
    def _on_new_game(self, button):
        """Start a new game."""
        self.board = self._init_board()
        self.current_player = 'w'
        self.selected_square = None
        self.valid_moves = []
        self.move_history = []
        self.last_move = None
        self.ai_thinking = False
        self.game_over = False
        self.castling_rights = {
            'w': {'king_side': True, 'queen_side': True},
            'b': {'king_side': True, 'queen_side': True}
        }
        self.en_passant_target = None
        self.status_label.set_text("Your turn (White)")
        self._update_board_display()
    
    def _on_difficulty_changed(self, combo):
        """Handle difficulty change."""
        difficulty_map = {0: 2, 1: 3, 2: 4}  # Easy, Medium, Hard
        self.ai_difficulty = difficulty_map.get(combo.get_active(), 3)
        print(f"AI difficulty changed to: {self.ai_difficulty}")
    
    def _on_chess_game_over(self, widget, message):
        """Optional callback for game over event."""
        print(f"Chess game ended: {message}")