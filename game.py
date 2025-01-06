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
        self.sub_board_winners = [[None for _ in range(3)] for _ in range(3)]

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
        
        # Check for sub-board win
        sub_board_result = self.check_sub_board(main_row, main_col)
        if sub_board_result:
            # Store the sub-board result
            self.sub_board_winners[main_row][main_col] = sub_board_result
            
        # Check for main board win using sub-board winners
        game_result = self.check_win(self.sub_board_winners)
        
        # Switch player
        # self.symbol = 'O' if self.symbol == 'X' else 'X'
        
        # Set next valid board
        if self.sub_board_winners[sub_row][sub_col]:
            self.current_board = None  # Can play anywhere if target board is won
        else:
            self.current_board = (sub_row, sub_col)
        
        # Print board for debugging
        print("\nBoard state after move (make move):")
        self.print_board()
        
        return {
            'valid': True,
            'sub_board_result': sub_board_result,
            'game_over': game_result is not None,
            'winner': game_result if game_result and game_result != 'draw' else None,
            'is_draw': game_result == 'draw'
        }

    def check_win(self, board):
        """Check if there's a win in the given board."""
        # Check rows
        for row in board:
            if row[0] and row[0] == row[1] == row[2]:
                return row[0]
        
        # Check columns
        for col in range(3):
            if board[0][col] and board[0][col] == board[1][col] == board[2][col]:
                return board[0][col]
        
        # Check diagonals
        if board[0][0] and board[0][0] == board[1][1] == board[2][2]:
            return board[0][0]
        if board[0][2] and board[0][2] == board[1][1] == board[2][0]:
            return board[1][1]
        
        # Check for draw (all cells filled)
        if all(cell for row in board for cell in row):
            return 'draw'
        
        return None

    def check_sub_board(self, main_row, main_col):
        """Check if a sub-board is won."""
        return self.check_win(self.board[main_row][main_col])

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

    def receive_move(self, main_row, main_col, sub_row, sub_col):
        """Handle opponent's move."""
        opponent_symbol = 'O' if self.symbol == 'X' else 'X'
        self.board[main_row][main_col][sub_row][sub_col] = opponent_symbol
        
        # Check for sub-board win
        sub_board_result = self.check_sub_board(main_row, main_col)
        if sub_board_result:
            # Store the sub-board result
            self.sub_board_winners[main_row][main_col] = sub_board_result
            
        # Check for main board win using sub-board winners
        game_result = self.check_win(self.sub_board_winners)
        
        # Update current board for next move
        if self.sub_board_winners[sub_row][sub_col]:  # If target board is won
            self.current_board = None  # Can play anywhere
        else:
            self.current_board = (sub_row, sub_col)
        
        self.my_turn = True  # It's our turn after opponent's move

    
        return {
            'sub_board_result': sub_board_result,
            'game_over': game_result is not None,
            'winner': game_result if game_result and game_result != 'draw' else None,
            'is_draw': game_result == 'draw'
        }

    # can comment
    def print_board(self):
        """Print the current state of the ultimate tic-tac-toe board."""
        # Helper function to get cell content or space if empty
        def get_cell(main_row, main_col, sub_row, sub_col):
            return self.board[main_row][main_col][sub_row][sub_col] or ' '

        # Print each row of sub-boards
        for main_row in range(3):
            # Print each row within the sub-boards
            for sub_row in range(3):
                # Print the three sub-boards in this row
                for main_col in range(3):
                    print('|', end=' ')
                    for sub_col in range(3):
                        cell = get_cell(main_row, main_col, sub_row, sub_col)
                        print(f'{cell}', end=' ')
                    print('|', end=' ')
                print()  # New line after each sub-board row
            print('-' * 35)  # Separator between main rows

        # Print current board status
        print(f"\nCurrent board: {self.current_board if self.current_board else 'Any'}")