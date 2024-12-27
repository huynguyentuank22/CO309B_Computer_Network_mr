class BattleshipGame:
    def __init__(self, username):
        self.username = username
        self.board_size = 10
        self.my_board = [[None for _ in range(self.board_size)] for _ in range(self.board_size)]
        self.opponent_board = [[None for _ in range(self.board_size)] for _ in range(self.board_size)]
        self.ships = {
            'carrier': 5,
            'battleship': 4,
            'cruiser': 3,
            'submarine': 3,
            'destroyer': 2
        }
        self.placed_ships = []
        self.ready = False
        self.opponent_ready = False
        self.my_turn = False
        self.game_started = False
        self.remaining_ships = sum(length for length in self.ships.values())
        
    def place_ship(self, ship, x, y, orientation):
        if ship not in self.ships or ship in self.placed_ships:
            return False
            
        length = self.ships[ship]
        if orientation == 'horizontal':
            if x + length > self.board_size:
                return False
            # Check if space is free
            for i in range(length):
                if self.my_board[y][x + i] is not None:
                    return False
            # Place ship
            for i in range(length):
                self.my_board[y][x + i] = ship
        else:  # vertical
            if y + length > self.board_size:
                return False
            # Check if space is free
            for i in range(length):
                if self.my_board[y + i][x] is not None:
                    return False
            # Place ship
            for i in range(length):
                self.my_board[y + i][x] = ship
                
        self.placed_ships.append(ship)
        return True
        
    def is_placement_complete(self):
        """Check if all ships have been placed."""
        return len(self.placed_ships) == len(self.ships)

    def receive_attack(self, x, y):
        """Process an attack from the opponent."""
        if x < 0 or x >= self.board_size or y < 0 or y >= self.board_size:
            return {'hit': False, 'message': 'Invalid coordinates'}

        cell = self.my_board[y][x]
        if cell:  # Hit
            self.remaining_ships -= 1
            self.my_board[y][x] = 'hit'
            return {
                'hit': True,
                'message': f'Hit {cell}!',
                'ship': cell,
                'game_over': self.remaining_ships == 0
            }
        else:  # Miss
            self.my_board[y][x] = 'miss'
            return {'hit': False, 'message': 'Miss!'}

    def fire(self, x, y):
        if x < 0 or x >= self.board_size or y < 0 or y >= self.board_size:
            return {'hit': False, 'message': 'Invalid coordinates'}
            
        if self.opponent_board[y][x] is not None:
            return {'hit': False, 'message': 'Already fired at this position'}
            
        # The actual result will come from the opponent
        return {'valid': True, 'x': x, 'y': y} 

    def set_ready(self):
        """Mark player as ready."""
        self.ready = True
        return self.ready and self.opponent_ready  # Return True if both players are ready

    def set_opponent_ready(self):
        """Mark opponent as ready."""
        self.opponent_ready = True
        return self.ready and self.opponent_ready  # Return True if both players are ready 