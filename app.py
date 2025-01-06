from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from game import UltimateTicTacToe
from peer import PeerNetwork
import threading
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Required for session

game_instances = {}
peer_instances = {}

@app.route('/')
def index():
    # Clear any existing session
    session.clear()
    return render_template('index.html')

@app.route('/create_game', methods=['POST'])
def create_game():
    username = request.form.get('username')
    if not username:
        return jsonify({'success': False, 'error': 'Username is required'})
    
    # Store username in session
    session['username'] = username
    
    # Create peer network instance
    peer = PeerNetwork(username)
    peer.initialize_udp_socket()
    peer.initialize_tcp_socket()
    
    # Start UDP listener thread
    udp_listener_thread = threading.Thread(target=peer.listen_for_udp, daemon=True)
    udp_listener_thread.start()
    
    # Create game instance
    game = UltimateTicTacToe(username)
    
    # Store instances
    game_instances[username] = game
    peer_instances[username] = peer
    
    return jsonify({'success': True})

@app.route('/game')
def game():
    if 'username' not in session:
        return redirect(url_for('index'))
    return render_template('game.html')

@app.route('/place_ship', methods=['POST'])
def place_ship():
    data = request.json
    username = session.get('username')
    game = game_instances.get(username)
    
    if not game:
        return jsonify({'error': 'Game not found'}), 404
    
    success = game.place_ship(
        data['ship'],
        data['x'],
        data['y'],
        data['orientation']
    )
    
    return jsonify({'success': success})

@app.route('/fire', methods=['POST'])
def fire():
    data = request.json
    username = session.get('username')
    game = game_instances.get(username)
    
    if not game:
        return jsonify({'error': 'Game not found'}), 404
    
    result = game.fire(data['x'], data['y'])
    # Send the move to peer
    peer = peer_instances.get(username)
    if peer and peer.is_connected:
        peer.send_message({
            'type': 'FIRE',
            'x': data['x'],
            'y': data['y']
        })
    
    return jsonify(result)

@app.route('/lobby')
def lobby():
    # Check if user is logged in
    if 'username' not in session:
        return redirect(url_for('index'))
    return render_template('lobby.html')

@app.route('/broadcast_request', methods=['POST'])
def broadcast_request():
    username = session.get('username')
    peer = peer_instances.get(username)
    if peer:
        success = peer.broadcast_connect_request()
        if success:
            return jsonify({'success': True})
        return jsonify({
            'success': False, 
            'error': 'Failed to initialize connection'
        }), 500
    return jsonify({'success': False, 'error': 'Peer not found'}), 404

@app.route('/cancel_search', methods=['POST'])
def cancel_search():
    username = session.get('username')
    peer = peer_instances.get(username)
    if peer:
        peer.stop_broadcasting()
    return jsonify({'success': True})

@app.route('/get_requests')
def get_requests():
    username = session.get('username')
    peer = peer_instances.get(username)
    if not peer:
        return jsonify([])
    return jsonify(peer.get_pending_requests())

@app.route('/handle_request', methods=['POST'])
def handle_request():
    username = session.get('username')
    peer = peer_instances.get(username)
    data = request.json
    
    if peer and data.get('accept'):
        success = peer.accept_connection(data['username'])
        if success:
            # Get opponent's game instance
            opponent_username = data['username']
            opponent_game = game_instances.get(opponent_username)
            my_game = game_instances.get(username)
            
            if opponent_game and my_game:
                # Set up both games
                is_first = random.choice([True, False])
                my_game.start_game(is_first)
                
                # Notify opponent through peer connection
                peer.send_message({
                    'type': 'GAME_START',
                    'first_player': not is_first,  # Opposite for opponent
                    'opponent': username  # Send accepting player's username
                })
            
            return jsonify({'success': True})
    elif peer:
        peer.reject_connection(data['username'])
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/check_connection', methods=['GET'])
def check_connection():
    username = session.get('username')
    peer = peer_instances.get(username)
    
    if not peer:
        return jsonify({'connected': False, 'status': 'No peer connection'})
    
    if peer.is_connected:
        # If connected and has game status, return it
        game_status = peer.get_game_status()
        return jsonify({
            'connected': True,
            'game_status': game_status,
            'opponent': peer.opponent_username
        })
    
    return jsonify({'connected': False, 'status': 'Waiting for connection'})

@app.route('/disconnect', methods=['POST'])
def disconnect():
    username = session.get('username')
    peer = peer_instances.get(username)
    if peer:
        # Send disconnect message to opponent before closing
        if peer.is_connected:
            try:
                peer.send_message({
                    'type': 'DISCONNECT',
                    'message': 'Opponent left the game'
                })
            except:
                pass
        peer.handle_disconnect("You left the game")
    return jsonify({'success': True})

@app.route('/player_ready', methods=['POST'])
def player_ready():
    username = session.get('username')
    game = game_instances.get(username)
    peer = peer_instances.get(username)
    
    print(f"\n=== Player Ready Request ===")
    print(f"Username: {username}")
    
    if not game or not peer:
        return jsonify({'success': False}), 404
    
    if not game.is_placement_complete():
        return jsonify({'success': False, 'message': 'Not all ships placed'}), 400
    
    print(f"Player {username} is ready")
    game.ready = True
    peer.ready = True  # Set our ready status in peer
    
    # Notify opponent
    if peer.is_connected:
        print(f"Notifying opponent {peer.opponent_username} that {username} is ready")
        peer.send_message({
            'type': 'PLAYER_READY',
            'username': username
        })
    
    # Check if both players are ready
    both_ready = peer.ready and peer.opponent_ready
    print(f"Both players ready: {both_ready}")
    if both_ready:
        peer.game_status = {
                        'type': 'GAME_START',
                        'both_ready': True
                    }
    
    return jsonify({
        'success': True,
        'both_ready': both_ready
    })

@app.route('/receive_attack', methods=['POST'])
def receive_attack():
    data = request.json
    username = session.get('username')
    game = game_instances.get(username)
    
    if not game:
        return jsonify({'error': 'Game not found'}), 404
    
    result = game.receive_attack(data['x'], data['y'])
    return jsonify(result)

@app.route('/start_game', methods=['POST'])
def start_game():
    username = session.get('username')
    game = game_instances.get(username)
    peer = peer_instances.get(username)
    
    if not game or not peer:
        return jsonify({'success': False}), 404
        
    # Randomly choose who goes first
    is_first = random.choice([True, False])
    game.start_game(is_first)
    
    # Notify opponent
    if peer.is_connected:
        peer.send_message({
            'type': 'GAME_START',
            'first_player': not is_first  # Opposite for opponent
        })
    
    return jsonify({
        'success': True,
        'first_player': is_first
    })

@app.route('/make_move', methods=['POST'])
def make_move():
    data = request.json
    username = session.get('username')
    game = game_instances.get(username)
    peer = peer_instances.get(username)
    
    if not game:
        return jsonify({'valid': False, 'message': 'Game not found'}), 404
    
    result = game.make_move(
        data['main_row'],
        data['main_col'],
        data['sub_row'],
        data['sub_col']
    )
    
    # Send move to opponent if valid
    if result['valid'] and peer and peer.is_connected:
        peer.send_message({
            'type': 'MOVE',
            'main_row': data['main_row'],
            'main_col': data['main_col'],
            'sub_row': data['sub_row'],
            'sub_col': data['sub_col']
        })
    
    return jsonify(result)

@app.route('/get_username')
def get_username():
    username = session.get('username')
    if not username:
        return jsonify({'username': None}), 401
    return jsonify({'username': username})

@app.route('/logout')
def logout():
    username = session.get('username')
    if username:
        # Clean up instances
        if username in game_instances:
            del game_instances[username]
        if username in peer_instances:
            peer = peer_instances[username]
            if peer:
                peer.disconnect()
            del peer_instances[username]
    session.clear()
    return redirect(url_for('index'))

@app.route('/receive_move', methods=['POST'])
def receive_move():
    data = request.json
    username = session.get('username')
    game = game_instances.get(username)
    
    if not game:
        return jsonify({'success': False, 'message': 'Game not found'}), 404
    
    # Update the game state with opponent's move
    game.receive_move(
        data['main_row'],
        data['main_col'],
        data['sub_row'],
        data['sub_col']
    )
    
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True) 