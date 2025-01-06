class UltimateTicTacToeGame {
    constructor() {
        this.currentBoard = null;
        this.gameStarted = false;  // Start as false
        this.myTurn = false;
        this.symbol = null;
        
        this.setupBoard();
        this.startConnectionCheck();
        this.initializeGame();  // Keep this to initialize the game
    }

    async initializeGame() {
        try {
            const response = await fetch('/start_game', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            if (result.success) {
                this.myTurn = result.first_player;
                this.symbol = this.myTurn ? 'X' : 'O';
                this.updateStatus();
                this.highlightPlayableBoard();
            }
        } catch (error) {
            console.error('Error starting game:', error);
        }
    }

    handleGameStatus(status) {
        if (status.type === 'GAME_START') {
            console.log('Received game start:', status);
            this.gameStarted = true;
            this.myTurn = status.first_player;
            this.symbol = this.myTurn ? 'X' : 'O';
            this.updateStatus();
            this.highlightPlayableBoard();
        } else if (status.type === 'MOVE') {
            const cell = document.querySelector(
                `.cell[data-main-row="${status.main_row}"]` +
                `[data-main-col="${status.main_col}"]` +
                `[data-sub-row="${status.sub_row}"]` +
                `[data-sub-col="${status.sub_col}"]`
            );
            
            if (cell) {
                cell.textContent = this.symbol === 'X' ? 'O' : 'X';
                this.myTurn = true;
                this.updateStatus();
                this.currentBoard = [status.sub_row, status.sub_col];
                this.highlightPlayableBoard();
            }
        }
    }

    async handleMove(event) {
        if (!this.myTurn || !this.gameStarted) {
            console.log('Not your turn or game not started');
            return;
        }
        
        const cell = event.target;
        if (cell.textContent) {
            console.log('Cell already taken');
            return;
        }
        
        const mainRow = parseInt(cell.dataset.mainRow);
        const mainCol = parseInt(cell.dataset.mainCol);
        const subRow = parseInt(cell.dataset.subRow);
        const subCol = parseInt(cell.dataset.subCol);
        
        if (this.currentBoard && 
            (mainRow !== this.currentBoard[0] || mainCol !== this.currentBoard[1])) {
            return;
        }
        
        const response = await fetch('/make_move', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                main_row: mainRow,
                main_col: mainCol,
                sub_row: subRow,
                sub_col: subCol
            })
        });
        
        const result = await response.json();
        if (result.valid) {
            cell.textContent = this.symbol;
            this.myTurn = false;
            this.updateStatus();
            
            if (result.game_over) {
                this.handleGameOver(this.symbol);
            } else {
                this.currentBoard = [subRow, subCol];
                this.highlightPlayableBoard();
            }
        }
    }

    updateStatus() {
        const status = document.getElementById('status');
        if (!this.gameStarted) {
            status.textContent = 'Waiting for game to start...';
        } else if (this.myTurn) {
            status.textContent = 'Your turn!';
        } else {
            status.textContent = "Opponent's turn";
        }
    }

    handleGameOver(winner) {
        const status = document.getElementById('status');
        status.textContent = winner === this.symbol ? 'You won!' : 'You lost!';
        document.querySelectorAll('.cell').forEach(cell => {
            cell.style.pointerEvents = 'none';
        });
    }

    startConnectionCheck() {
        setInterval(async () => {
            try {
                const response = await fetch('/check_connection');
                const data = await response.json();
                
                if (!data.connected) {
                    alert('Opponent disconnected');
                    window.location.href = '/lobby';
                } else if (data.game_status) {
                    this.handleGameStatus(data.game_status);
                }
            } catch (error) {
                console.error('Connection check error:', error);
            }
        }, 2000);
    }

    highlightPlayableBoard() {
        // Remove previous highlights
        document.querySelectorAll('.cell').forEach(cell => {
            cell.classList.remove('playable');
        });

        // Add highlights to playable cells
        if (this.currentBoard) {
            const [row, col] = this.currentBoard;
            document.querySelectorAll(
                `.cell[data-main-row="${row}"][data-main-col="${col}"]`
            ).forEach(cell => {
                if (!cell.textContent) {
                    cell.classList.add('playable');
                }
            });
        } else {
            document.querySelectorAll('.cell').forEach(cell => {
                if (!cell.textContent) {
                    cell.classList.add('playable');
                }
            });
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.game = new UltimateTicTacToeGame();
}); 