class BattleshipGame {
    constructor() {
        this.boardSize = 10;
        this.currentShip = null;
        this.orientation = 'horizontal';
        this.isPlacingShip = false;
        this.isReady = false;
        this.opponentReady = false;
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
        
        // Add event listeners to cells
        this.myBoard.querySelectorAll('.cell').forEach(cell => {
            const x = parseInt(cell.dataset.x);
            const y = parseInt(cell.dataset.y);
            cell.addEventListener('click', () => this.handleMyBoardClick(x, y));
        });
        
        this.opponentBoard.querySelectorAll('.cell').forEach(cell => {
            const x = parseInt(cell.dataset.x);
            const y = parseInt(cell.dataset.y);
            cell.addEventListener('click', () => this.handleOpponentBoardClick(x, y));
        });
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
                console.log('All ships placed, showing ready button');
                const readyBtn = document.getElementById('ready-btn');
                if (readyBtn) {
                    readyBtn.style.display = 'block';
                    console.log('Ready button is now visible');
                } else {
                    console.error('Ready button not found when trying to show it');
                }
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
        if (!readyBtn) {
            console.error('Ready button not found!');
            return;
        }
        console.log('Setting up ready button:', readyBtn);
        readyBtn.style.display = 'none';  // Initially hidden
        readyBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            console.log('Ready button clicked!');
            alert('Ready button clicked!');
            try {
                await this.handleReady();
            } catch (error) {
                console.error('Error handling ready:', error);
                alert('Error: ' + error.message);
            }
        });
    }

    async handleReady() {
        console.log('handleReady called');
        if (!this.isPlacementComplete()) {
            alert('Please place all your ships first!');
            return;
        }

        console.log('Current status - Ready:', this.isReady, 'Opponent Ready:', this.opponentReady);

        try {
            const response = await fetch('/player_ready', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ ready: true })
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const result = await response.json();
            console.log('Player ready result:', result);

            if (result.success) {
                console.log('Successfully marked as ready');
                this.isReady = true;
                document.getElementById('ready-btn').disabled = true;
                document.getElementById('rotate').disabled = true;
                document.querySelectorAll('.ships button').forEach(btn => btn.disabled = true);
                
                // Check if opponent was already ready
                if (this.opponentReady) {
                    console.log('Opponent was already ready, starting game');
                    document.getElementById('phase-text').textContent = 'Both players ready! Starting game...';
                    setTimeout(() => this.startCountdown(), 1000);  // Small delay before countdown
                } else {
                    console.log('Waiting for opponent to be ready');
                    document.getElementById('phase-text').textContent = 'Waiting for opponent...';
                }
            } else {
                alert(`Failed to ready up: ${result.message || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Error in handleReady:', error);
            // More specific error message
            if (error.message.includes('status 0')) {
                alert('Connection error. Please check your internet connection.');
            } else {
                alert('Failed to ready up. Please try again.');
            }
        }
    }

    isPlacementComplete() {
        const placedShips = document.querySelectorAll('.ships button[disabled]');
        const count = placedShips.length;
        alert(`Checking ship placement: ${count}/5 ships placed`);
        return count === 5;  // All 5 ships should be placed
    }

    startCountdown() {
        if (this.countdownStarted) {
            console.log('Countdown already started');
            return;
        }
        this.countdownStarted = true;
        console.log('Starting countdown');
        const countdownDiv = document.getElementById('countdown');
        countdownDiv.style.display = 'block';
        let count = 3;

        const countInterval = setInterval(() => {
            console.log('Countdown:', count);
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
        console.log('Starting game');
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

    startConnectionCheck() {
        setInterval(() => {
            fetch('/check_connection')
                .then(response => response.json())
                .then(data => {
                    if (!data.connected) {
                        // Show disconnect message if provided
                        const message = data.status || 'Connection lost';
                        alert(message);
                        // Navigate back to lobby
                        window.location.href = '/lobby';
                    } else if (data.game_status) {
                        // Handle game status updates
                        this.handleGameStatus(data.game_status);
                    }
                })
                .catch(error => console.error('Connection check error:', error));
        }, 2000);
    }

    handleGameStatus(status) {
        console.log('Received game status:', status);
        if (status.type === 'PLAYER_READY') {
            // Opponent is ready
            if (!this.isReady) {
                console.log('Opponent is ready, waiting for us');
                document.getElementById('phase-text').textContent = 'Opponent is ready! Place your ships and click Done.';
                this.opponentReady = true;
                console.log('Updated opponent ready status:', this.opponentReady);
            } else {
                console.log('We are ready and received opponent ready');
                document.getElementById('phase-text').textContent = 'Both players ready! Starting game...';
                console.log('Both players ready, starting countdown');
                this.startCountdown();
            }
        }
    }

    setupExitHandler() {
        // Handle page unload/exit
        window.addEventListener('beforeunload', async (e) => {
            // Cancel the event
            e.preventDefault();
            
            // Send disconnect message to server
            try {
                await fetch('/disconnect', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
            } catch (error) {
                console.error('Error sending disconnect:', error);
            }
            
            // Chrome requires returnValue to be set
            e.returnValue = '';
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.game = new BattleshipGame();
    console.log('Game initialized:', window.game);
}); 