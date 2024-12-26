class BattleshipGame {
    constructor() {
        this.boardSize = 10;
        this.currentShip = null;
        this.orientation = 'horizontal';
        this.isPlacingShip = false;
        this.isReady = false;
        this.gameStarted = false;
        this.myTurn = false;
        
        this.setupBoards();
        this.setupControls();
        this.setupPreview();
        this.startConnectionCheck();
        this.setupExitHandler();
        this.setupReadyButton();
    }

    setupBoards() {
        this.myBoard = document.getElementById('my-board');
        this.opponentBoard = document.getElementById('opponent-board');
        
        for (let i = 0; i < this.boardSize; i++) {
            for (let j = 0; j < this.boardSize; j++) {
                const myCell = this.createCell(i, j, true);
                const opponentCell = this.createCell(i, j, false);
                
                this.myBoard.appendChild(myCell);
                this.opponentBoard.appendChild(opponentCell);
            }
        }
    }

    createCell(x, y, isMyBoard) {
        const cell = document.createElement('div');
        cell.className = 'cell';
        cell.dataset.x = x;
        cell.dataset.y = y;
        
        if (isMyBoard) {
            cell.addEventListener('click', () => this.handleMyBoardClick(x, y));
        } else {
            cell.addEventListener('click', () => this.handleOpponentBoardClick(x, y));
        }
        
        return cell;
    }

    setupControls() {
        const shipButtons = document.querySelectorAll('.ships button');
        shipButtons.forEach(button => {
            button.addEventListener('click', () => {
                this.currentShip = button.dataset.ship;
                this.isPlacingShip = true;
                shipButtons.forEach(b => b.classList.remove('selected'));
                button.classList.add('selected');
            });
        });

        document.getElementById('rotate').addEventListener('click', () => {
            this.orientation = this.orientation === 'horizontal' ? 'vertical' : 'horizontal';
            if (this.isPlacingShip && this.lastPreviewCell) {
                this.showShipPreview(this.lastPreviewCell);
            }
        });
    }

    setupPreview() {
        const cells = this.myBoard.querySelectorAll('.cell');
        cells.forEach(cell => {
            cell.addEventListener('mouseover', () => {
                if (this.isPlacingShip && this.currentShip) {
                    this.showShipPreview(cell);
                }
            });
            
            cell.addEventListener('mouseout', () => {
                this.clearPreview();
            });
        });
    }

    showShipPreview(cell) {
        this.clearPreview();
        this.lastPreviewCell = cell;
        
        const x = parseInt(cell.dataset.x);
        const y = parseInt(cell.dataset.y);
        const length = parseInt(document.querySelector(`[data-ship="${this.currentShip}"]`).dataset.length);
        
        const previewCells = [];
        let isValid = true;
        
        for (let i = 0; i < length; i++) {
            const cellX = this.orientation === 'horizontal' ? x + i : x;
            const cellY = this.orientation === 'horizontal' ? y : y + i;
            
            if (cellX >= this.boardSize || cellY >= this.boardSize) {
                isValid = false;
                break;
            }
            
            const previewCell = this.myBoard.querySelector(`[data-x="${cellX}"][data-y="${cellY}"]`);
            if (previewCell.classList.contains('ship')) {
                isValid = false;
                break;
            }
            
            previewCells.push(previewCell);
        }
        
        previewCells.forEach(cell => {
            cell.classList.add(isValid ? 'preview-valid' : 'preview-invalid');
        });
    }

    clearPreview() {
        const previewCells = this.myBoard.querySelectorAll('.preview-valid, .preview-invalid');
        previewCells.forEach(cell => {
            cell.classList.remove('preview-valid', 'preview-invalid');
        });
    }

    async handleMyBoardClick(x, y) {
        if (!this.currentShip) return;
        
        const response = await fetch('/place_ship', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                ship: this.currentShip,
                x: x,
                y: y,
                orientation: this.orientation
            })
        });
        
        const result = await response.json();
        if (result.success) {
            this.placeShipOnBoard(x, y);
            document.querySelector(`[data-ship="${this.currentShip}"]`).disabled = true;
            this.currentShip = null;
            
            // Check if all ships are placed
            if (this.isPlacementComplete()) {
                document.getElementById('ready-btn').style.display = 'block';
            }
        }
    }

    async handleOpponentBoardClick(x, y) {
        if (!this.gameStarted || !this.myTurn) return;

        const response = await fetch('/fire', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ x, y })
        });
        
        const result = await response.json();
        if (result.valid) {
            this.myTurn = false;
            this.updateTurnIndicator();
        }
    }

    placeShipOnBoard(x, y) {
        const length = parseInt(document.querySelector(`[data-ship="${this.currentShip}"]`).dataset.length);
        
        for (let i = 0; i < length; i++) {
            const cellX = this.orientation === 'horizontal' ? x + i : x;
            const cellY = this.orientation === 'horizontal' ? y : y + i;
            const cell = this.myBoard.querySelector(`[data-x="${cellX}"][data-y="${cellY}"]`);
            cell.classList.add('ship');
        }
    }

    setupReadyButton() {
        const readyBtn = document.getElementById('ready-btn');
        readyBtn.style.display = 'none';  // Initially hidden
        readyBtn.addEventListener('click', () => this.handleReady());
    }

    async handleReady() {
        if (!this.isPlacementComplete()) {
            alert('Please place all your ships first!');
            return;
        }

        const response = await fetch('/player_ready', {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.success) {
            this.isReady = true;
            document.getElementById('ready-btn').disabled = true;
            document.getElementById('rotate').disabled = true;
            document.querySelectorAll('.ships button').forEach(btn => btn.disabled = true);
            document.getElementById('phase-text').textContent = 'Waiting for opponent...';
            
            if (result.both_ready) {
                this.startCountdown();
            }
        }
    }

    isPlacementComplete() {
        const placedShips = document.querySelectorAll('.ships button[disabled]');
        return placedShips.length === 5;  // All 5 ships should be placed
    }

    startCountdown() {
        const countdownDiv = document.getElementById('countdown');
        countdownDiv.style.display = 'block';
        let count = 3;

        const countInterval = setInterval(() => {
            if (count > 0) {
                countdownDiv.textContent = count;
                count--;
            } else {
                clearInterval(countInterval);
                countdownDiv.style.display = 'none';
                this.startGame();
            }
        }, 1000);
    }

    startGame() {
        this.gameStarted = true;
        document.getElementById('ship-placement').style.display = 'none';
        document.getElementById('phase-text').textContent = 'Battle Phase';
        this.updateTurnIndicator();
    }

    updateTurnIndicator() {
        const indicator = document.getElementById('turn-indicator');
        indicator.textContent = this.myTurn ? 'Your Turn' : "Opponent's Turn";
        indicator.className = this.myTurn ? 'my-turn' : 'opponent-turn';
        
        // Enable/disable opponent board clicks based on turn
        const cells = this.opponentBoard.getElementsByClassName('cell');
        for (let cell of cells) {
            cell.style.cursor = this.myTurn ? 'pointer' : 'not-allowed';
        }
    }

    handleAttackResult(x, y, result) {
        const cell = this.opponentBoard.querySelector(`[data-x="${x}"][data-y="${y}"]`);
        cell.classList.add(result.hit ? 'hit' : 'miss');
        
        document.getElementById('game-status').textContent = result.message;
        
        if (result.game_over) {
            this.handleGameOver(true);  // We won
        }
    }

    handleIncomingAttack(x, y) {
        if (!this.gameStarted) return;

        fetch('/receive_attack', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ x, y })
        })
        .then(response => response.json())
        .then(result => {
            const cell = this.myBoard.querySelector(`[data-x="${x}"][data-y="${y}"]`);
            cell.classList.add(result.hit ? 'hit' : 'miss');
            
            if (result.game_over) {
                this.handleGameOver(false);  // We lost
            } else {
                this.myTurn = true;
                this.updateTurnIndicator();
            }
        });
    }

    handleGameOver(won) {
        const message = won ? 'Congratulations! You won!' : 'Game Over! You lost!';
        alert(message);
        window.location.href = '/lobby';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new BattleshipGame();
}); 