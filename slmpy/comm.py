import socket

class comm_handler():
    def __init__(self):
        pass
    
class tcp_handler(comm_handler):
    def __init__(self):
        comm_handler.__init__(self)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #server_address = socket.gethostbyname(socket.gethostname())
        self.client_connection = None
        self.client_address = None
        
    def receive(self, buffersize):
        if self.client_connection:
            return self.client_connection.recv(buffersize)
    
    def send(self, data):
        if self.client_connection:
            self.client_connection.sendall(data)
    
class tcp_server(tcp_handler):
    def __init__(self, port = 9999):
        tcp_handler.__init__(self)
        self.socket.bind(('',port))
        self.socket.listen(1)
        
        self.port = port

        
    def run(self):
        print("TCP server is running.")
        print(f'Waiting for a connection on port {self.port}')
        client_connection, client_address = self.socket.accept()
        self.client_connection = client_connection
        self.client_address = client_address
        print(f'Connected to {client_address[0]}')    
        

        
        
class tcp_client(tcp_handler):
    def __init__(self):
        tcp_handler.__init__(self)
    
    
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)