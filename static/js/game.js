class UltimateTicTacToeGame {
    constructor() {
        this.currentBoard = null;  // Which sub-board to play in (null means any)
        this.gameStarted = true;  // Game starts immediately
        this.myTurn = false;
        this.symbol = null;  // 'X' or 'O'
        
        this.setupBoard();
        this.startConnectionCheck();
        this.initializeGame();
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

    setupBoard() {
        const board = document.getElementById('gameBoard');
        board.innerHTML = '';
        
        for (let i = 0; i < 3; i++) {
            for (let j = 0; j < 3; j++) {
                const subBoard = document.createElement('div');
                subBoard.className = 'sub-board';
                subBoard.dataset.row = i;
                subBoard.dataset.col = j;
                
                for (let m = 0; m < 3; m++) {
                    for (let n = 0; n < 3; n++) {
                        const cell = document.createElement('div');
                        cell.className = 'cell';
                        cell.dataset.mainRow = i;
                        cell.dataset.mainCol = j;
                        cell.dataset.subRow = m;
                        cell.dataset.subCol = n;
                        cell.addEventListener('click', (e) => this.handleMove(e));
                        subBoard.appendChild(cell);
                    }
                }
                
                board.appendChild(subBoard);
            }
        }
    }

    async handleMove(event) {
        if (!this.myTurn || !this.gameStarted) return;
        
        const cell = event.target;
        if (cell.textContent) return; // Cell already taken
        
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
            
            // Handle sub-board result
            if (result.sub_board_result) {
                this.handleSubBoardResult(
                    mainRow,
                    mainCol,
                    result.sub_board_result
                );
            }
            
            // Handle game over
            if (result.game_over) {
                if (result.is_draw) {
                    this.handleGameOver('draw');
                } else {
                    this.handleGameOver(result.winner);
                }
                return;
            }
            
            this.currentBoard = [subRow, subCol];
            this.highlightPlayableBoard();
        }
    }

    updateStatus() {
        const status = document.getElementById('status');
        if (this.myTurn) {
            status.textContent = `Your turn! (${this.symbol})`;
        } else {
            status.textContent = `Opponent's turn (${this.symbol === 'X' ? 'O' : 'X'})`;
        }
    }

    handleGameOver(result) {
        const status = document.getElementById('status');
        if (result === 'draw') {
            status.textContent = "Game Over - It's a draw!";
        } else {
            status.textContent = result === this.symbol ? 'You won!' : 'You lost!';
        }
        
        // Disable all cells
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

    handleGameStatus(status) {
        if (status.type === 'MOVE') {
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
                
                // Check if sub-board is won
                if (status.sub_board_result) {
                    this.handleSubBoardResult(
                        status.main_row,
                        status.main_col,
                        status.sub_board_result
                    );
                }
                
                this.currentBoard = [status.sub_row, status.sub_col];
                this.highlightPlayableBoard();
            }
        } else if (status.type === 'GAME_START') {
            this.gameStarted = true;
            this.myTurn = status.first_player;
            this.symbol = this.myTurn ? 'X' : 'O';
            this.updateStatus();
            this.highlightPlayableBoard();
        }
    }

    handleSubBoardResult(mainRow, mainCol, result) {
        const subBoard = document.querySelector(
            `.sub-board[data-row="${mainRow}"][data-col="${mainCol}"]`
        );
        
        if (subBoard) {
            // Clear all cells in the sub-board
            subBoard.innerHTML = '';
            subBoard.classList.add('won');
            
            if (result === 'draw') {
                subBoard.classList.add('draw');
                subBoard.textContent = '-';
            } else {
                subBoard.classList.add(`won-${result.toLowerCase()}`);
                subBoard.textContent = result;  // 'X' or 'O'
            }
        }
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