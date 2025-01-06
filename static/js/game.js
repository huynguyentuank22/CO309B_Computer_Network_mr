class UltimateTicTacToeGame {
    constructor() {
        this.currentBoard = null;  // Which sub-board to play in (null means any)
        this.isReady = false;
        this.opponentReady = false;
        this.gameStarted = false;
        this.myTurn = false;
        this.symbol = null;  // 'X' or 'O'
        
        this.setupBoard();
        this.setupReadyButton();
        this.startConnectionCheck();
    }

    setupBoard() {
        const board = document.getElementById('gameBoard');
        board.innerHTML = '';
        
        // Create 3x3 grid of sub-boards
        for (let i = 0; i < 3; i++) {
            for (let j = 0; j < 3; j++) {
                const subBoard = document.createElement('div');
                subBoard.className = 'sub-board';
                subBoard.dataset.row = i;
                subBoard.dataset.col = j;
                
                // Create 3x3 grid of cells for each sub-board
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

    setupReadyButton() {
        const readyBtn = document.getElementById('ready-btn');
        readyBtn.addEventListener('click', async () => {
            try {
                const response = await fetch('/player_ready', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ ready: true })
                });
                
                const result = await response.json();
                if (result.success) {
                    this.isReady = true;
                    readyBtn.disabled = true;
                    
                    if (result.both_ready) {
                        this.startCountdown();
                    } else {
                        document.getElementById('status').textContent = 'Waiting for opponent...';
                    }
                }
            } catch (error) {
                console.error('Error marking ready:', error);
            }
        });
    }

    async handleMove(event) {
        if (!this.gameStarted || !this.myTurn) return;
        
        const cell = event.target;
        const mainRow = parseInt(cell.dataset.mainRow);
        const mainCol = parseInt(cell.dataset.mainCol);
        const subRow = parseInt(cell.dataset.subRow);
        const subCol = parseInt(cell.dataset.subCol);
        
        // Check if move is valid for current sub-board
        if (this.currentBoard && 
            (mainRow !== this.currentBoard[0] || mainCol !== this.currentBoard[1])) {
            return;
        }
        
        // Make move
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
                this.handleGameOver(result.winner);
            } else {
                this.currentBoard = result.next_board;
                this.highlightPlayableBoard();
            }
        }
    }

    highlightPlayableBoard() {
        // Remove previous highlights
        document.querySelectorAll('.cell').forEach(cell => {
            cell.classList.remove('playable');
        });
        
        // Highlight new playable cells
        if (this.currentBoard) {
            const [row, col] = this.currentBoard;
            document.querySelectorAll(
                `.cell[data-main-row="${row}"][data-main-col="${col}"]`
            ).forEach(cell => {
                if (!cell.textContent) {  // Only highlight empty cells
                    cell.classList.add('playable');
                }
            });
        } else {
            // If can play anywhere, highlight all empty cells
            document.querySelectorAll('.cell').forEach(cell => {
                if (!cell.textContent) {
                    cell.classList.add('playable');
                }
            });
        }
    }

    startCountdown() {
        const countdownDiv = document.getElementById('countdown');
        countdownDiv.style.display = 'block';
        let count = 3;
        
        const interval = setInterval(() => {
            if (count > 0) {
                countdownDiv.textContent = count;
                count--;
            } else {
                clearInterval(interval);
                countdownDiv.style.display = 'none';
                this.startGame();
            }
        }, 1000);
    }

    async startGame() {
        const response = await fetch('/start_game', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        if (result.success) {
            this.gameStarted = true;
            this.myTurn = result.first_player;
            this.symbol = this.myTurn ? 'X' : 'O';
            this.updateStatus();
            this.highlightPlayableBoard();
        }
    }

    updateStatus() {
        const status = document.getElementById('status');
        if (!this.gameStarted) {
            status.textContent = 'Waiting for game to start...';
        } else {
            status.textContent = this.myTurn ? 'Your turn!' : "Opponent's turn";
        }
    }

    handleGameOver(winner) {
        const status = document.getElementById('status');
        status.textContent = winner === this.symbol ? 'You won!' : 'You lost!';
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
                    alert(data.status || 'Connection lost');
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
        if (status.type === 'PLAYER_READY') {
            this.opponentReady = true;
            if (this.isReady && this.opponentReady) {
                this.startCountdown();
            }
        } else if (status.type === 'GAME_START') {
            this.gameStarted = true;
            this.myTurn = status.first_player;
            this.symbol = this.myTurn ? 'X' : 'O';
            this.updateStatus();
            this.highlightPlayableBoard();
        } else if (status.type === 'MOVE') {
            // Handle opponent's move
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
                
                // Update current board based on opponent's move
                this.currentBoard = this.board[status.sub_row][status.sub_col][0][0] === '' ?
                    [status.sub_row, status.sub_col] : null;
                this.highlightPlayableBoard();
            }
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.game = new UltimateTicTacToeGame();
}); 