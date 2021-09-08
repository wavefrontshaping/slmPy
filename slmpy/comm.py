import socket
import struct
import time

DEFAULT_PORT = 9999
DEFAULT_TIMEOUT = 2
PACKET_SIZE = 4096
PAYLOAD_SIZE = struct.calcsize("i") 

class comm_handler():
    def __init__(self, **kwargs):
        self.port = kwargs.pop('port', DEFAULT_PORT)
        
    def send(self, data):
        pass
    
    def receive(self):
        pass
        
    def send_data(self, data):
        # Send message length first
        # using "i" type because "L" for unsigned long does not have the same
        # size on different systems (4 on raspberry pi!)
        message_size = struct.pack("i", len(data)) 
        self.send(message_size + data)
    
class udp_handler(comm_handler):
    def __init__(self, **kwargs):
        comm_handler.__init__(self, **kwargs)
        self.socket_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) 
        self.socket_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) 
        
    def receive(self, buffersize):
        return self.socket_in.recv(buffersize)

    def send(self, data):
        self.socket_out.sendall(data)
        
#     def send_data(self, message_size, data):
#         self.socket.sendall(message_size + data)
    
class udp_server(udp_handler):
    def __init__(self, **kwargs):
        udp_handler.__init__(self, **kwargs)
        
        self.socket_in.bind(('', self.port))      
        self.socket_out.connect((self.server_address, self.port+1))
        
        print("TCP server is running.")
        print(f'Writing on port {self.port+1}.')
        print(f'Listening to port {self.port}.')
        print(f'Waiting for a connection.')
        
        
class udp_client(udp_handler):
    def __init__(self, **kwargs):
        udp_handler.__init__(self, **kwargs) 
        self.server_address = kwargs.pop('server_address')

        self.socket_in.bind(('', self.port))
        self.socket_out.connect((self.server_address, self.port))
        
        print("TCP client is running.")
        print(f'Writing on port {self.port}.')
        print(f'Listening to port {self.port+1}.')
        print(f'Waiting for a connection.')
        
    
class tcp_handler(comm_handler):
    def __init__(self, **kwargs):
        comm_handler.__init__(self, **kwargs)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #server_address = socket.gethostbyname(socket.gethostname())
        self.client_connection = None
        self.client_address = None
        
    def receive(self, buffersize):
        if self.client_connection:
            return self.client_connection.recv(buffersize)
        else:
            return self.socket.recv(buffersize)
    
    def send(self, data):
        if self.client_connection:
            self.client_connection.sendall(data)
    
class tcp_server(tcp_handler):
    def __init__(self, **kwargs):
        tcp_handler.__init__(self, **kwargs)
        self.socket.bind(('',self.port))
        self.socket.listen(1)
#         self.port = port

        
    def run(self):
        print("TCP server is running.")
        print(f'Waiting for a connection on port {self.port}')
        client_connection, client_address = self.socket.accept()
        self.client_connection = client_connection
        self.client_address = client_address
        print(f'Connected to {client_address[0]}')    
        

    def get_data(self, buffer_size, timeout = DEFAULT_TIMEOUT):
        data=b''
                
        while len(data) < PAYLOAD_SIZE:
            data += self.receive(PACKET_SIZE)
#                     print(f'data length = {len(data)}')

        t0 = time.time()
        packed_msg_size = data[:PAYLOAD_SIZE]
        data = data[PAYLOAD_SIZE:]
        msg_size = struct.unpack("i", packed_msg_size)[0]
        # Retrieve all data based on message size
        print(f'Waiting for data of size {msg_size}')
        while len(data) < msg_size:      
            data += self.receive(buffer_size)
            if time.time()-t0 > timeout:
                print('Timeout!')
                print(f'{time.time()-t0:.3f}')
                self.send(b'err')
                continue

        frame_data = data[:msg_size]
        data = data[msg_size:]
        
        return frame_data, data
        
        
class tcp_client(tcp_handler):
    def __init__(self, **kwargs):
        tcp_handler.__init__(self, **kwargs)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.server_address = kwargs.pop('server_address')
#         self.port = port
        self._connect()        
        
    def _connect(self):
        try:
            self.socket.connect((self.server_address, self.port))
            print(f'Connected to {self.server_address} on {self.port}')
        except socket.error as e:
            print(f'Connection to {self.server_address} on port {self.port} failed: {e}')
        
        
#     def send_data(self, message_size, data):
#         self.socket.sendall(message_size + data)



