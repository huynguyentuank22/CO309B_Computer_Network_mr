import socket
import threading
import time
import pickle
from typing import List, Dict
import logging
import requests


class PeerNetwork:
    def __init__(self, username: str):
        self.username = username
        self.local_ip = self.get_local_ip()
        self.UDP_PORT = 5005
        self.udp_socket = None
        self.tcp_socket = None
        self.tcp_port = None
        self.peer_connection = None
        self.is_connected = False
        self.pending_requests: List[Dict] = []
        self.is_broadcasting = False
        self.broadcast_thread = None
        self.request_lock = threading.Lock()
        self.opponent_username = None
        self.game_status = None  # To store game status messages
        self.ready = False  # My ready status
        self.opponent_ready = False  # Opponent's ready status

    def get_local_ip(self):
        """Get local IP address."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            print(f"Local IP: {local_ip}")
        except Exception:
            local_ip = '127.0.0.1'
            print("Failed to get local IP, using localhost")
        finally:
            s.close()
        return local_ip

    def initialize_udp_socket(self):
        """Initialize UDP socket for broadcasting and listening."""
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Bind to all interfaces for better broadcast reception
            self.udp_socket.bind(('', self.UDP_PORT))
            print(f"Listening for connection requests on UDP port {self.UDP_PORT}...")
            return True
        except Exception as e:
            print(f"UDP socket initialization failed: {e}")
            return False

    def initialize_tcp_socket(self):
        """Initialize TCP socket for direct communication."""
        try:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_socket.bind(('0.0.0.0', 0))
            self.tcp_port = self.tcp_socket.getsockname()[1]
            self.tcp_socket.listen(1)
            print(f"TCP socket initialized on port {self.tcp_port}")
            
            # Start TCP listener thread
            tcp_listener_thread = threading.Thread(target=self.listen_for_tcp, daemon=True)
            tcp_listener_thread.start()
            
            return True
        except Exception as e:
            print(f'Initialize TCP failed: {e}')
            return False

    def listen_for_tcp(self):
        """Listen for incoming TCP connections."""
        while True:
            try:
                client_socket, client_address = self.tcp_socket.accept()
                if not self.is_connected:
                    self.peer_connection = client_socket
                    self.is_connected = True
                    print(f"Accepted TCP connection from {client_address}")
                    
                    # Start message handling thread
                    threading.Thread(target=self.handle_peer_messages, 
                                   daemon=True).start()
                    
                    # Send connection confirmation
                    self.send_message({
                        'type': 'CONNECTION_ACCEPTED',
                        'username': self.username
                    })
                else:
                    # Reject connection if already connected
                    client_socket.close()
            except Exception as e:
                print(f"TCP accept error: {e}")
                break

    def start(self):
        """Start the peer network."""
        self.initialize_udp_socket()

        # Start UDP listener thread
        udp_listener_thread = threading.Thread(target=self.listen_for_udp, daemon=True)
        udp_listener_thread.start()

        while True:
            if not self.is_connected:
                choice = input(
                    "\nDo you want to:\n1. Broadcast connection request\n2. Just listen\n3. Quit\nChoice: ")

                if choice == '1':
                    self.broadcast_connect_request()
                    time.sleep(10)
                elif choice == '2':
                    print("Continuing to listen for requests...")
                    time.sleep(10)
                elif choice == '3':
                    break
            else:
                message = input("Enter message (or 'quit' to disconnect): ")
                if message.lower() == 'quit':
                    self.is_connected = False
                    if self.peer_connection:
                        self.peer_connection.close()
                else:
                    self.send_message(message)

    def broadcast_connect_request(self):
        """Start broadcasting connection requests with improved reliability."""
        if not self.tcp_socket:
            if not self.initialize_tcp_socket():
                return False

        if not self.udp_socket:
            if not self.initialize_udp_socket():
                return False

        print(f"Broadcasting connection request from {self.username}...")
        self.is_broadcasting = True
        
        def broadcast_loop():
            broadcast_count = 0
            while self.is_broadcasting and not self.is_connected:
                try:
                    request_msg = pickle.dumps({
                        'type': 'CONNECT_REQUEST',
                        'username': self.username,
                        'local_ip': self.local_ip,
                        'tcp_port': self.tcp_port,
                        'sequence': broadcast_count
                    })
                    
                    # Send to broadcast address
                    self.udp_socket.sendto(request_msg, ('<broadcast>', self.UDP_PORT))
                    
                    # Also try sending to subnet broadcast
                    subnet_broadcast = '.'.join(self.local_ip.split('.')[:-1] + ['255'])
                    self.udp_socket.sendto(request_msg, (subnet_broadcast, self.UDP_PORT))
                    
                    broadcast_count += 1
                    time.sleep(1)  # Broadcast more frequently
                except Exception as e:
                    print(f"Broadcasting error: {e}")
                    time.sleep(1)  # Prevent tight loop on error
                    continue

        self.broadcast_thread = threading.Thread(target=broadcast_loop, daemon=True)
        self.broadcast_thread.start()
        return True

    def stop_broadcasting(self):
        """Stop broadcasting connection requests."""
        self.is_broadcasting = False
        if self.broadcast_thread:
            self.broadcast_thread.join(timeout=1)

    def listen_for_udp(self):
        """Listen for incoming UDP messages with improved error handling and validation."""
        print(f"Starting UDP listener for {self.username}...")
        while True:
            try:
                data, addr = self.udp_socket.recvfrom(4096)
                print(f"Received UDP data from {addr}")
                if not data:
                    continue

                try:
                    message = pickle.loads(data)
                    print(f"Decoded message: {message}")
                except pickle.UnpicklingError:
                    print(f"Invalid message format from {addr}")
                    continue

                if not isinstance(message, dict) or 'type' not in message:
                    print(f"Malformed message from {addr}")
                    continue

                if (message['type'] == 'CONNECT_REQUEST' and 
                    addr[0] != self.local_ip and  # Ignore self-broadcasts
                    not self.is_connected):  # Only process if not already connected
                    
                    # Validate required fields
                    required_fields = ['username', 'local_ip', 'tcp_port']
                    if not all(field in message for field in required_fields):
                        print(f"Missing required fields in message from {addr}")
                        continue

                    request = {
                        'username': message['username'],
                        'ip': addr[0],  # Use actual sender IP
                        'tcp_port': message['tcp_port'],
                        'timestamp': time.time(),
                        'strength': 1  # New field to track request persistence
                    }

                    self.update_pending_requests(request)
                    print(f"\nNew connection request from {request['username']} at {request['ip']}")
                    self.display_pending_requests()

            except socket.error as e:
                print(f"UDP socket error: {e}")
                time.sleep(1)  # Prevent tight loop on error
            except Exception as e:
                print(f"Unexpected error in UDP listener: {e}")
                time.sleep(1)

    def update_pending_requests(self, new_request: Dict):
        """Update pending requests with thread safety and improved handling."""
        with self.request_lock:
            current_time = time.time()
            
            # Remove expired requests (older than 30 seconds)
            self.pending_requests = [
                r for r in self.pending_requests 
                if current_time - r['timestamp'] < 30
            ]
            
            # Check if request from this user already exists
            existing_request = next(
                (r for r in self.pending_requests 
                 if r['username'] == new_request['username']),
                None
            )
            
            if existing_request:
                # Update existing request
                existing_request['timestamp'] = current_time
                existing_request['strength'] += 1
                existing_request['ip'] = new_request['ip']
                existing_request['tcp_port'] = new_request['tcp_port']
            else:
                # Add new request
                self.pending_requests.append(new_request)

    def display_pending_requests(self):
        """Display current pending requests in a formatted way."""
        with self.request_lock:
            if not self.pending_requests:
                print("\nNo pending connection requests.")
                return

            print("\nPending connection requests:")
            print("-" * 50)
            for i, request in enumerate(self.pending_requests, 1):
                age = time.time() - request['timestamp']
                print(f"{i}. Username: {request['username']}")
                print(f"   IP: {request['ip']}:{request['tcp_port']}")
                print(f"   Age: {age:.1f} seconds")
                print(f"   Signal Strength: {'█' * request['strength']}")
                print("-" * 50)

    def get_pending_requests(self):
        """Get list of pending connection requests."""
        print(f"Getting pending requests for {self.username}")
        with self.request_lock:
            current_time = time.time()
            # Clean up old requests before returning
            self.pending_requests = [
                r for r in self.pending_requests 
                if current_time - r['timestamp'] < 30
            ]
            # Filter out self requests
            filtered_requests = [
                r for r in self.pending_requests 
                if r['username'] != self.username
            ]
            print(f"Current pending requests: {self.pending_requests}")
            # Return only necessary information for the frontend
            return [{
                'username': r['username'],
                'timestamp': r['timestamp'],
                'strength': r['strength']
            } for r in filtered_requests]

    def accept_connection(self, username):
        """Accept a connection request from a specific user."""
        for request in self.pending_requests:
            if request['username'] == username:
                try:
                    # Stop broadcasting if we're searching
                    self.stop_broadcasting()
                    
                    # Initialize TCP connection
                    if not self.tcp_socket:
                        if not self.initialize_tcp_socket():
                            return False
                    
                    # Connect to peer
                    peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    print(f"Attempting to connect to {request['ip']}:{request['tcp_port']}")
                    # Set a timeout for the connection attempt
                    peer_socket.settimeout(5)
                    peer_socket.connect((request['ip'], request['tcp_port']))
                    # Reset to blocking mode after connection
                    peer_socket.settimeout(None)
                    self.peer_connection = peer_socket
                    self.is_connected = True
                    self.opponent_username = username
                    print(f"Connected to peer {username} at {request['ip']}:{request['tcp_port']}")

                    # Start message handling thread
                    threading.Thread(target=self.handle_peer_messages,
                                  daemon=True).start()
                    
                    # Clean up requests
                    self.pending_requests = []
                    
                    # Send connection confirmation
                    self.send_message({
                        'type': 'CONNECTION_ACCEPTED',
                        'username': self.username
                    })
                    
                    return True
                except Exception as e:
                    print(f"Connection error: {e}")
                    # Clean up failed connection
                    try:
                        peer_socket.close()
                    except:
                        pass
                    return False
        return False

    def reject_connection(self, username):
        """Reject a connection request from a specific user."""
        self.pending_requests = [
            r for r in self.pending_requests 
            if r['username'] != username
        ]

    def handle_peer_messages(self):
        """Handle incoming messages from connected peer."""
        while self.is_connected:
            try:
                data = self.peer_connection.recv(1024)
                if not data:
                    self.handle_disconnect("Opponent disconnected")
                    break
                message = pickle.loads(data)
                
                if message.get('type') == 'MOVE':
                    print(f"Received move: {message}")
                    # Update game state through Flask route
                    requests.post('http://localhost:5000/receive_move', json={
                        'main_row': message['main_row'],
                        'main_col': message['main_col'],
                        'sub_row': message['sub_row'],
                        'sub_col': message['sub_col']
                    })
                elif message.get('type') == 'GAME_START':
                    print(f"Game starting, first player: {message.get('first_player')}")
                    self.game_status = {
                        'type': 'GAME_START',
                        'first_player': message.get('first_player')
                    }
                elif message.get('type') == 'DISCONNECT':
                    self.handle_disconnect(message.get('message', 'Opponent disconnected'))
                    break
                else:
                    print(f"Received unknown message type: {message}")
            except Exception as e:
                print(f"Message handling error: {e}")
                self.handle_disconnect("Connection error occurred")
                break

    def handle_disconnect(self, reason="Connection lost"):
        """Handle disconnection with cleanup."""
        self.is_connected = False
        self.game_status = reason
        if self.peer_connection:
            try:
                self.peer_connection.close()
            except:
                pass
        self.peer_connection = None
        self.opponent_username = None
        print(f"Peer connection lost: {reason}")

    def send_message(self, message):
        """Send message to connected peer."""
        if self.is_connected and self.peer_connection:
            try:
                serialized_message = pickle.dumps(message)
                self.peer_connection.send(serialized_message)
                print(f"Sent: {message}")
            except Exception as e:
                print(f"Message send error: {e}")
                self.is_connected = False

    def get_game_status(self):
        """Get current game status."""
        status = self.game_status
        self.game_status = None  # Clear after reading
        return status


def main():
    username = input("Enter your username: ")
    peer = PeerNetwork(username)
    peer.start()


if __name__ == '__main__':
    main()
