from flask import Flask, render_template, request, jsonify, session, redirect
from game import BattleshipGame
from peer import PeerNetwork
import threading

app = Flask(__name__)
app.secret_key = 'battleship_secret_key'  # Required for session

game_instances = {}
peer_instances = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_game', methods=['POST'])
def create_game():
    username = request.form.get('username')
    if not username:
        return jsonify({'error': 'Username is required'}), 400
    
    # Create peer network instance
    peer = PeerNetwork(username)
    # Initialize UDP socket
    if not peer.initialize_udp_socket():
        return jsonify({'error': 'Failed to initialize network'}), 500
    
    # Start UDP listener thread
    udp_listener_thread = threading.Thread(target=peer.listen_for_udp, daemon=True)
    udp_listener_thread.start()
    
    # Create game instance
    game = BattleshipGame(username)
    
    # Store instances
    session['username'] = username
    game_instances[username] = game
    peer_instances[username] = peer
    
    return jsonify({'success': True, 'redirect': '/lobby'})

@app.route('/game')
def game():
    username = session.get('username')
    if not username or username not in game_instances:
        return redirect('/')
    return render_template('game.html', username=username)

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
    username = session.get('username')
    if not username:
        return redirect('/')
    return render_template('lobby.html', username=username)

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
        return jsonify({'success': success})
    elif peer:
        peer.reject_connection(data['username'])
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/check_connection')
def check_connection():
    username = session.get('username')
    peer = peer_instances.get(username)
    game = game_instances.get(username)
    
    if peer and peer.is_connected:
        game_status = None
        if game:
            # Check opponent's ready status
            opponent_game = game_instances.get(peer.opponent_username)
            if opponent_game and opponent_game.ready and not game.opponent_ready:
                game.opponent_ready = True
                game_status = {
                    'type': 'PLAYER_READY',
                    'username': peer.opponent_username
                }
            
            # If both players are ready, start the game
            if game.ready and game.opponent_ready and not game.game_started:
                game_status = {
                    'type': 'GAME_START',
                    'first_player': game.my_turn
                }
                
        return jsonify({
            'connected': True,
            'opponent': getattr(peer, 'opponent_username', None),
            'game_status': game_status
        })
    
    # Get disconnect reason if any
    status = peer.get_game_status() if peer else None
    return jsonify({
        'connected': False,
        'status': status
    })

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
    print(f"Game exists: {game is not None}")
    print(f"Peer exists: {peer is not None}")
    print(f"Peer connected: {peer.is_connected if peer else False}")
    print(f"Opponent username: {peer.opponent_username if peer else None}")
    
    if not game or not peer:
        print(f"Game or peer not found for {username}")
        return jsonify({'success': False}), 404
    
    if not game.is_placement_complete():
        print(f"Not all ships placed for {username}")
        return jsonify({'success': False, 'message': 'Not all ships placed'}), 400
    
    print(f"Player {username} is ready")
    game.ready = True
    
    # Notify opponent
    if peer.is_connected:
        print(f"Notifying opponent {peer.opponent_username} that {username} is ready")
        peer.send_message({
            'type': 'PLAYER_READY',
            'username': username
        })
    
    # Check if both players are ready
    opponent_game = game_instances.get(peer.opponent_username)
    print(f"Opponent game exists: {opponent_game is not None}")
    print(f"Opponent ready: {opponent_game.ready if opponent_game else False}")
    
    both_ready = False
    if opponent_game:
        if opponent_game.ready:
            both_ready = True
            print("Both players are ready!")
            # Start the game
            game.game_started = True
            opponent_game.game_started = True
            
            # Randomly choose who goes first
            import random
            game.my_turn = random.choice([True, False])
            opponent_game.my_turn = not game.my_turn
            print(f"First player: {username if game.my_turn else peer.opponent_username}")
            
            # Notify opponent of turn order
            peer.send_message({
                'type': 'GAME_START',
                'first_player': username if game.my_turn else peer.opponent_username
            })
    
    print(f"Returning: success=True, both_ready={both_ready}")
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

if __name__ == '__main__':
    app.run(debug=True) 