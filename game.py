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
        
    def fire(self, x, y):
        if x < 0 or x >= self.board_size or y < 0 or y >= self.board_size:
            return {'hit': False, 'message': 'Invalid coordinates'}
            
        if self.opponent_board[y][x] is not None:
            return {'hit': False, 'message': 'Already fired at this position'}
            
        # In a real game, we would check the opponent's board
        # For now, just mark as miss
        self.opponent_board[y][x] = 'miss'
        return {'hit': False, 'message': 'Miss!'} 