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
    peer_thread = threading.Thread(target=peer.initialize_udp_socket, daemon=True)
    peer_thread.start()
    
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
        peer.broadcast_connect_request()
    return jsonify({'success': True})

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

if __name__ == '__main__':
    app.run(debug=True) 