# -*- coding: utf-8 -*-
"""
Created on Sun Dec 06 20:14:02 2015

@author: Sebastien Popoff
"""

try:
    import wx
except ImportError:
    raise ImportError("The wxPython module is required to run this program.")
import threading
import numpy as np
import time
import socket
# from io import BytesIO






EVT_NEW_IMAGE = wx.PyEventBinder(wx.NewEventType(), 0)

class ImageEvent(wx.PyCommandEvent):
    def __init__(self, eventType=EVT_NEW_IMAGE.evtType[0], id=0):
        wx.PyCommandEvent.__init__(self, eventType, id)
        self.img = None
        self.color = False
        self.oldImageLock = None
        self.eventLock = None
        
        
class SLMframe(wx.Frame):
    """Frame used to display full screen image."""
    def __init__(self, monitor, isImageLock = True):   
        self.isImageLock = isImageLock
        # Create the frame
        self.SetMonitor(monitor)
        # Set the frame to the position and size of the target monito
        # wx.Frame.__init__(self,None,-1,'SLM window',pos = (self._x0, self._y0), size = (self._resX, self._resY)) 
        super().__init__(None,-1,'SLM window',pos = (self._x0, self._y0), size = (self._resX, self._resY)) 
        self.img = wx.Image(2,2)
        self.bmp = self.img.ConvertToBitmap()
        self.clientSize = self.GetClientSize()
        # Update the image upon receiving an event EVT_NEW_IMAGE
        self.Bind(EVT_NEW_IMAGE, self.UpdateImage)
        # Set full screen
        self.ShowFullScreen(not self.IsFullScreen(), wx.FULLSCREEN_ALL)
        self.SetFocus()

    def InitBuffer(self):
        self.clientSize = self.GetClientSize()
        self.bmp = self.img.Scale(self.clientSize[0], self.clientSize[1]).ConvertToBitmap()
        dc = wx.ClientDC(self)
        dc.DrawBitmap(self.bmp,0,0)

        
    def UpdateImage(self, event):
        self.eventLock = event.eventLock
        self.img = event.img
        self.InitBuffer()
        self.ReleaseEventLock()
        
    def ReleaseEventLock(self):
        if self.eventLock:
            if self.eventLock.locked():
                self.eventLock.release()
        
    def SetMonitor(self, monitor):
        if (monitor < 0 or monitor > wx.Display.GetCount()-1):
            raise ValueError('Invalid monitor (monitor %d).' % monitor)
        self._x0, self._y0, self._resX, self._resY = wx.Display(monitor).GetGeometry()
 
class Client():
    """Client class to interact with slmPy running on a distant server."""
    def __init__(self):
        pass

    def start(self, server_address, port = 9999):
        self.client_socket=socket.socket()
        try:
            self.client_socket.connect((server_address, port))
            print(f'Connected to {server_address} on {port}')
        except socket.error as e:
            print(f'Connection to {server_address} on port {port} failed: {e}')
            return

    def sendArray(self, arr, timeout = 10):
        if not isinstance(arr, np.ndarray):
            print('Not a valid numpy image')
            return
        if not arr.dtype == np.uint8:
            print('Numpy array should be of uint8 type')
        self.client_socket.sendall(arr.tostring())
        self.client_socket.sendall(b'\n')
        print('Waiting for reply from the server')

        t0 = time.time()
        while True:
            buffer = self.client_socket.recv(128)
            if buffer:
                print(buffer.decode())
            if buffer and buffer.decode() == 'done':
                print('Data transmitted')
                return 1
            elif time.time()-t0 > timeout:
                print('Timeout reached.')
                return -1
            
        
    def stopServer(self):
        time.sleep(0.5)
        self.client_socket.sendall(b'\r')
        
    def close(self):
        self.stopServer()
        self.client_socket.shutdown(1)
        self.client_socket.close()
        
class SLMdisplay:
    """Interface for sending images to the display frame."""
    def __init__(self ,monitor = 1, isImageLock = False):       
        self.isImageLock = isImageLock            
        self.monitor = monitor
        # Create the thread in which the window app will run
        # It needs its thread to continuously refresh the window
        self.vt =  videoThread(self)      
        self.eventLock = threading.Lock()
        if (self.isImageLock):
            self.eventLock = threading.Lock()
            
    def listen_port(self, port = 9999):
        """
        Liston to a port for data transmission.
        Update the SLM with the array transmitted.
        Use a `Client` abject to send arrays from a client. 
        """
        server_socket=socket.socket() 
        server_socket.bind(('',port))
        server_socket.listen(1)
        print(f'waiting for a connection on port {port}')
        client_connection,client_address=server_socket.accept()
        print(f'connected to {client_address[0]}')
        data=b''
        while True:
            buffer = client_connection.recv(4096)
            data+= buffer
            if not buffer or buffer == b'\r': #
                print('Closing connection')
                break
            elif buffer and buffer[-1] == 10: # 10 is \n
                pass
            else:
                continue
            # empty buffer
            data = b''
    
            resX, resY = self.vt.frame._resX, self.vt.frame._resY
            if not len(buffer) == resX*resY:
                print('Buffer size does not match image size')
                client_connection.sendall(b'done')
                continue
              
            print('Received image')
            image=np.fromstring(data[:-1], dtype=np.uint8).reshape([resY,resX])
            print('Updating SLM')
            slm.updateArray(image)
            client_connection.sendall(b'done')

        client_connection.close()
        server_socket.close()
        
    def getSize(self):
        return self.vt.frame._resX, self.vt.frame._resY

    def updateArray(self, array, sleep = 0.2):
        """
        Update the SLM monitor with the supplied array.
        Note that the array is not the same size as the SLM resolution,
        the image will be deformed to fit the screen.
        array: numpy array to display, should be the same size as the resolution of the SLM.
        sleep: pause in seconds after displaying an image.
        """
        # create a wx.Image from the array
        h,w = array.shape[0], array.shape[1]

        if len(array.shape) == 2:
            bw_array = array.copy()
            bw_array.shape = h, w, 1
            color_array = np.concatenate((bw_array,bw_array,bw_array), axis=2)
            data = color_array.tostring()
        else :      
            data = array.tostring()   
        img = wx.ImageFromBuffer(width=w, height=h, dataBuffer=data)
        # Create the event
        event = ImageEvent()
        event.img = img
        event.eventLock = self.eventLock
        
        # Wait for the lock to be released (if isImageLock = True)
        # to be sure that the previous image has been displayed
        # before displaying the next one - it avoids skipping images
        if (self.isImageLock):
            event.eventLock.acquire()
        # Wait (can bug when closing/opening the SLM too quickly otherwise)
        time.sleep(sleep)
        # Trigger the event (update image)
        self.vt.frame.AddPendingEvent(event)
        
    def close(self):
        self.vt.frame.Close()

class videoThread(threading.Thread):
    """Run the MainLoop as a thread. Access the frame with self.frame."""
    def __init__(self, parent,autoStart=True):
        threading.Thread.__init__(self)
        self.parent = parent
        # Set as deamon so that it does not prevent the main program from exiting
        self.setDaemon(1)
        self.start_orig = self.start
        self.start = self.start_local
        self.frame = None #to be defined in self.run
        self.lock = threading.Lock()
        self.lock.acquire() #lock until variables are set
        if autoStart:
            self.start() #automatically start thread on init
    def run(self):
        app = wx.App()
        frame = SLMframe(monitor = self.parent.monitor, isImageLock = self.parent.isImageLock)
        frame.Show(True)
        self.frame = frame
        self.lock.release()
        # Start GUI main loop
        app.MainLoop()

    def start_local(self):
        self.start_orig()
        # Use lock to wait for the functions to get defined
        self.lock.acquire()
