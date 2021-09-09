import socket
import struct
import time
from funcy import chunks
from math import ceil

DEFAULT_PORT = 9999
DEFAULT_TIMEOUT = 2
PACKET_SIZE = 4096
INT_TYPE = "Q"
# INT8 = 'I'
PAYLOAD_SIZE = struct.calcsize(INT_TYPE) # size of the buffer to communicate integers (for the message size)
HANDSHAKE_BUFFER_SIZE = 9 # size of the message to check connection from client for UDP
RESPONSE_BUFFER_SIZE = 4 # size of messages (errors, confirmation)
DEFAULT_BUFFER_SIZE = 4096

class comm_handler():
    def __init__(self, **kwargs):
        self.port = kwargs.pop('port', DEFAULT_PORT)
        self.buffer_size = None
        
    def send(self, data):
        pass
    
    def receive(self):
        pass
    
    def send_data(self, data):
        pass
    
    def get_data(self, timeout = DEFAULT_TIMEOUT):
        pass
        
    def get_message_size(self, data):
        # Send message length first
        # using "i" type because "L" for unsigned long does not have the same
        # size on different systems (4 on raspberry pi)
        return struct.pack(INT_TYPE, len(data)) 
        
    def communicate_buffer_size(self):
        self.send(struct.pack(INT_TYPE, self.buffer_size))
        
    def get_buffer_size(self):
        packed_buffer_size = self.receive(PAYLOAD_SIZE)
        self.buffer_size = struct.unpack(INT_TYPE, packed_buffer_size)[0]
        print(f'Buffer size = {self.buffer_size}')


       
    
class udp_handler(comm_handler):
    def __init__(self, **kwargs):
        comm_handler.__init__(self, **kwargs)
        self.socket_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) 
        self.socket_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) 
        print('Setting up sockets')
        
    def receive(self, buffersize):
        return self.socket_in.recv(buffersize)

    def send(self, data):
        self.socket_out.sendall(data)
        
    def send_data(self, data):
        print('sending data...')
        message_size = self.get_message_size(data)
        print(f'message_size = {len(data)} = {struct.unpack(INT_TYPE, message_size)[0]}')
        print(message_size)
        self.send(message_size)
        
        for chunk in chunks(self.buffer_size, data):
            self.send(chunk)    
        
    def get_data(self, timeout = DEFAULT_TIMEOUT):
      
        t0 = time.time()
        packed_msg_size = self.receive(PAYLOAD_SIZE)
        msg_size = struct.unpack(INT_TYPE, packed_msg_size)[0]
        print(f'-message size = {msg_size}')
        print(packed_msg_size)

        # number of chunks to divide the data into
        n_chunks = ceil(msg_size/self.buffer_size)

        data=b''
        for i_chunk in range(n_chunks):
            data += self.receive(self.buffer_size)
            if time.time()-t0 > timeout:
                print('Timeout!')
                self.send(b'err!')
                break

            print(f'{i_chunk+1}/{n_chunks}')
            print(' >>', len(data))

        print('Data received')
        return data[:msg_size]

    
class udp_server(udp_handler):
    def __init__(self, **kwargs):
        udp_handler.__init__(self, **kwargs)
        
        self.port_in = self.port
        self.port_out = self.port+1 
        
        self.socket_in.bind(('', self.port_in))      
        #self.socket_out.connect((self.server_address, self.port_out))
        
        print(f'Writing on port {self.port_out}.')
        print(f'Listening to port {self.port_in}.')
        print(f'Waiting for a connection.')
        
        
    def run(self):
        print("UDP server is running.")
        print(f'Waiting for a connection on port {self.port}')
        
        # as there is not connection in UDP, we wait for the 
        # client to send a message
        while True:
            #msg = self.socket_in.recv(HANDSHAKE_BUFFER_SIZE)
            msg, client_address = self.socket_in.recvfrom(HANDSHAKE_BUFFER_SIZE)
            if msg.decode() == 'handshake':
                break
        
        self.get_buffer_size()
        self.client_address = client_address[0]
        self.socket_out.connect((self.client_address, self.port_out))
        print(f'Connected to {client_address[0]} on port {self.port_out}.')    
        
class udp_client(udp_handler):
    def __init__(self, **kwargs):
        udp_handler.__init__(self, **kwargs) 
        self.buffer_size = kwargs.pop('buffer_size', DEFAULT_BUFFER_SIZE)
        self.server_address = kwargs.pop('server_address')

        self.port_in = self.port+1
        self.port_out = self.port
        
        self.socket_in.bind(('', self.port_in))
        self.socket_out.connect((self.server_address, self.port_out))
        
        print("UDP client is running.")
        print(f'Writing on port {self.port_out}.')
        print(f'Listening to port {self.port_in}.')
        handshake_message = bytes('handshake', "utf-8")
        self.send(handshake_message)
        self.communicate_buffer_size()
        
    
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
        else:
            self.socket.sendall(data)
            
    def get_data(self, timeout = DEFAULT_TIMEOUT):
        data=b''
                
        while len(data) < PAYLOAD_SIZE:
            data += self.receive(PACKET_SIZE)
        t0 = time.time()
        packed_msg_size = data[:PAYLOAD_SIZE]
        data = data[PAYLOAD_SIZE:]
        msg_size = struct.unpack(INT_TYPE, packed_msg_size)[0]
        # Retrieve all data based on message size
        print(f'Waiting for data of size {msg_size}')
        while len(data) < msg_size:      
            data += self.receive(self.buffer_size)
            if time.time()-t0 > timeout:
                print('Timeout!')
                print(f'{time.time()-t0:.3f}')
                self.send(b'err!')
                break
        frame_data = data[:msg_size]        
        return frame_data
    
    def send_data(self, data):
        message_size = self.get_message_size(data)
        self.send(message_size + data)
    
class tcp_server(tcp_handler):
    def __init__(self, **kwargs):
        tcp_handler.__init__(self, **kwargs)
        self.socket.bind(('',self.port))
        self.socket.listen(1)

    def run(self):
        print("TCP server is running.")
        print(f'Waiting for a connection on port {self.port}')
        client_connection, client_address = self.socket.accept()
        self.client_connection = client_connection
        self.client_address = client_address
        self.get_buffer_size()
        print(f'Connected to {client_address[0]}')    
              
class tcp_client(tcp_handler):
    def __init__(self, **kwargs):
        tcp_handler.__init__(self, **kwargs)
        self.buffer_size = kwargs.pop('buffer_size', DEFAULT_BUFFER_SIZE)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.server_address = kwargs.pop('server_address')
        self._connect()
        self.communicate_buffer_size()
        
    def _connect(self):
        try:
            self.socket.connect((self.server_address, self.port))
            print(f'Connected to {self.server_address} on {self.port}')
        except socket.error as e:
            print(f'Connection to {self.server_address} on port {self.port} failed: {e}')
        

