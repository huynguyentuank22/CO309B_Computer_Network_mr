import socket
import threading
import time
import pickle


class PeerNetwork:
    def __init__(self, username):
        self.username = username
        self.local_ip = self.get_local_ip()
        self.UDP_PORT = 5005
        self.udp_socket = None
        self.tcp_socket = None
        self.tcp_port = None
        self.peer_connection = None
        self.is_connected = False
        self.pending_requests = []
        self.is_broadcasting = False
        self.broadcast_thread = None

    def get_local_ip(self):
        """Get local IP address."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.254.254.254', 1))
            local_ip = s.getsockname()[0]
        except Exception:
            local_ip = '127.0.0.1'
        finally:
            s.close()
        return local_ip

    def initialize_udp_socket(self):
        """Initialize UDP socket for broadcasting and listening."""
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.bind((self.local_ip, self.UDP_PORT))
        print(f"Listening for connection requests on UDP port {self.UDP_PORT}...")

    def initialize_tcp_socket(self):
        """Initialize TCP socket for direct communication."""
        try:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_socket.bind((self.local_ip, 0))
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
        """Start broadcasting connection requests."""
        if not self.tcp_socket:
            if not self.initialize_tcp_socket():
                return False

        print(f"Broadcasting connection request from {self.username}...")
        self.is_broadcasting = True
        
        def broadcast_loop():
            while self.is_broadcasting and not self.is_connected:
                try:
                    request_msg = pickle.dumps({
                        'type': 'CONNECT_REQUEST',
                        'username': self.username,
                        'local_ip': self.local_ip,
                        'tcp_port': self.tcp_port
                    })
                    self.udp_socket.sendto(request_msg, ('<broadcast>', self.UDP_PORT))
                    time.sleep(2)  # Broadcast every 2 seconds
                except Exception as e:
                    print(f"Broadcasting error: {e}")
                    self.is_broadcasting = False
                    break

        self.broadcast_thread = threading.Thread(target=broadcast_loop, daemon=True)
        self.broadcast_thread.start()
        return True

    def stop_broadcasting(self):
        """Stop broadcasting connection requests."""
        self.is_broadcasting = False
        if self.broadcast_thread:
            self.broadcast_thread.join(timeout=1)

    def listen_for_udp(self):
        """Listen for incoming UDP messages."""
        while True:
            try:
                data, addr = self.udp_socket.recvfrom(1024)
                message = pickle.loads(data)

                if message['type'] == 'CONNECT_REQUEST' and addr[0] != self.local_ip:
                    # Store the request with timestamp
                    request = {
                        'username': message['username'],
                        'ip': addr[0],
                        'tcp_port': message['tcp_port'],
                        'timestamp': time.time()
                    }
                    # Update or add new request
                    self.update_pending_requests(request)

            except Exception as e:
                print(f"UDP listener error: {e}")
                continue

    def update_pending_requests(self, new_request):
        """Update pending requests list, removing old requests."""
        current_time = time.time()
        
        # Remove requests older than 30 seconds
        self.pending_requests = [
            r for r in self.pending_requests 
            if current_time - r['timestamp'] < 30
        ]
        
        # Remove existing request from same user if exists
        self.pending_requests = [
            r for r in self.pending_requests 
            if r['username'] != new_request['username']
        ]
        
        # Add new request
        self.pending_requests.append(new_request)

    def get_pending_requests(self):
        """Get list of pending connection requests."""
        current_time = time.time()
        # Clean up old requests before returning
        self.pending_requests = [
            r for r in self.pending_requests 
            if current_time - r['timestamp'] < 30
        ]
        return self.pending_requests

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
                    peer_socket.connect((request['ip'], request['tcp_port']))
                    self.peer_connection = peer_socket
                    self.is_connected = True
                    print(f"Connected to peer {username} at {request['ip']}:{request['tcp_port']}")

                    # Start message handling thread
                    threading.Thread(target=self.handle_peer_messages,
                                  daemon=True).start()
                    
                    # Clean up requests
                    self.pending_requests = []
                    return True
                except Exception as e:
                    print(f"Connection error: {e}")
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
                    break
                message = pickle.loads(data)
                if message.get('type') == 'GAME_ACTION':
                    # Handle game-specific messages
                    print(f"Received game action: {message}")
                else:
                    print(f"Received message: {message}")
            except Exception as e:
                print(f"Message handling error: {e}")
                break
        
        self.is_connected = False
        print("Peer connection lost")

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


def main():
    username = input("Enter your username: ")
    peer = PeerNetwork(username)
    peer.start()


if __name__ == '__main__':
    main()
