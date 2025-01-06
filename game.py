class UltimateTicTacToe:
    def __init__(self, username):
        self.username = username
        self.board = self.create_empty_board()
        self.current_board = None  # Which sub-board to play in (None means any)
        self.ready = False
        self.opponent_ready = False
        self.my_turn = False
        self.game_started = False
        self.winner = None
        self.symbol = None  # 'X' or 'O'

    def create_empty_board(self):
        # Create 3x3 grid of 3x3 boards
        return [[[['' for _ in range(3)] for _ in range(3)] for _ in range(3)] for _ in range(3)]

    def make_move(self, main_row, main_col, sub_row, sub_col):
        """Attempt to make a move at the specified position."""
        if not self.game_started or not self.my_turn:
            return {'valid': False, 'message': 'Not your turn'}

        if self.current_board is not None:
            if (main_row, main_col) != self.current_board:
                return {'valid': False, 'message': 'Wrong sub-board'}

        if self.board[main_row][main_col][sub_row][sub_col]:
            return {'valid': False, 'message': 'Cell already taken'}

        # Make the move
        self.board[main_row][main_col][sub_row][sub_col] = self.symbol
        
        # Check if sub-board is won
        if self.check_win(self.board[main_row][main_col]):
            # Mark the main board position as won
            self.board[main_row][main_col] = [[self.symbol for _ in range(3)] for _ in range(3)]
            
            # Check if game is won
            if self.check_game_win():
                return {
                    'valid': True,
                    'game_over': True,
                    'winner': self.symbol
                }

        # Set next board based on move position
        if self.board[sub_row][sub_col][0][0] == '':  # If target board is not full/won
            self.current_board = (sub_row, sub_col)
        else:
            self.current_board = None  # Can play anywhere

        self.my_turn = False
        return {'valid': True, 'next_board': self.current_board}

    def check_win(self, board):
        """Check if a board is won."""
        # Check rows
        for row in board:
            if row[0] and row[0] == row[1] == row[2]:
                return True

        # Check columns
        for col in range(3):
            if board[0][col] and board[0][col] == board[1][col] == board[2][col]:
                return True

        # Check diagonals
        if board[0][0] and board[0][0] == board[1][1] == board[2][2]:
            return True
        if board[0][2] and board[0][2] == board[1][1] == board[2][0]:
            return True

        return False

    def check_game_win(self):
        """Check if the entire game is won."""
        # Convert won boards to simple 3x3 grid
        main_board = [[self.get_board_winner(self.board[i][j]) 
                      for j in range(3)] for i in range(3)]
        return self.check_win(main_board)

    def get_board_winner(self, board):
        """Get the winner of a sub-board."""
        # If board is won, all cells will be the same
        return board[0][0] if board[0][0] == board[1][1] == board[2][2] else ''

    def set_ready(self):
        """Mark player as ready."""
        self.ready = True
        return self.ready and self.opponent_ready

    def set_opponent_ready(self):
        """Mark opponent as ready."""
        self.opponent_ready = True
        return self.ready and self.opponent_ready

    def start_game(self, is_first):
        """Start the game."""
        self.game_started = True
        self.my_turn = is_first
        self.symbol = 'X' if is_first else 'O' 