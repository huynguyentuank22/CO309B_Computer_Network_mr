class BattleshipGame {
    constructor() {
        this.boardSize = 10;
        this.currentShip = null;
        this.orientation = 'horizontal';
        this.isPlacingShip = false;
        this.setupBoards();
        this.setupControls();
        this.setupPreview();
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
        }
    }

    async handleOpponentBoardClick(x, y) {
        const response = await fetch('/fire', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ x, y })
        });
        
        const result = await response.json();
        const cell = this.opponentBoard.querySelector(`[data-x="${x}"][data-y="${y}"]`);
        cell.classList.add(result.hit ? 'hit' : 'miss');
        
        document.getElementById('game-status').textContent = result.message;
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
}

document.addEventListener('DOMContentLoaded', () => {
    new BattleshipGame();
}); 