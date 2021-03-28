# -*- coding: utf-8 -*-
"""
Created on Sun Dec 06 20:14:02 2015

@author: Sebastien M. Popoff

"""

try:
    import wx
except ImportError:
    raise ImportError("The wxPython module is required to run this program.")
import threading
import numpy as np
import time
import socket
import struct


EVT_NEW_IMAGE = wx.PyEventBinder(wx.NewEventType(), 0)

class ImageEvent(wx.PyCommandEvent):
    def __init__(self, eventType=EVT_NEW_IMAGE.evtType[0], id=0):
        wx.PyCommandEvent.__init__(self, eventType, id)
        self.img = None
        self.color = False
        self.oldImageLock = None
        self.eventLock = None


class SLMframe(wx.Frame):
    
    def __init__(self, monitor, isImageLock = True):
        self.isImageLock = isImageLock
        self.SetMonitor(monitor)
        super().__init__(None,
                         -1,
                         'SLM window',
                         pos = (self._x0, self._y0), 
                         size = (self._resX, self._resY),
                         style = wx.DEFAULT_FRAME_STYLE
                        ) 
        
        self.Window = SLMwindow(self, 
                                isImageLock = isImageLock,
                                res = (self._resX, self._resY)
                               )
        self.Show()
        
        self.Bind(EVT_NEW_IMAGE, self.OnNewImage)
        self.ShowFullScreen(not self.IsFullScreen(), wx.FULLSCREEN_ALL)
        self.SetFocus()
        
    def SetMonitor(self, monitor):
        if (monitor < 0 or monitor > wx.Display.GetCount()-1):
            raise ValueError('Invalid monitor (monitor %d).' % monitor)
        self._x0, self._y0, self._resX, self._resY = wx.Display(monitor).GetGeometry()
        
    def OnNewImage(self, event):
        self.Window.UpdateImage(event)
        
    
    def Quit(self):
        wx.CallAfter(self.Destroy)
        
        
class SLMwindow(wx.Window):
    
    def __init__(self,  *args, **kwargs):#isImageLock, res,  **kwargs): 
        self.isImageLock = kwargs.pop('isImageLock')
        self.res = kwargs.pop('res')
        kwargs['style'] = kwargs.setdefault('style', wx.NO_FULL_REPAINT_ON_RESIZE) | wx.NO_FULL_REPAINT_ON_RESIZE
        super().__init__(*args, **kwargs)
        
        self.img = wx.Image(*self.res)
        self._Buffer = wx.Bitmap(*self.res)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(EVT_NEW_IMAGE, self.UpdateImage)
        self.Bind(wx.EVT_PAINT,self.OnPaint)
        
        self.OnSize(None)
        
    def OnPaint(self, event):
        self._Buffer = self.img.ConvertToBitmap()
        dc = wx.BufferedPaintDC(self, self._Buffer)
#         dc = wx.PaintDC(self)
#         dc.DrawBitmap(self._Buffer,0,0)
 
    def OnSize(self,event):
        # The Buffer init is done here, to make sure the buffer is always
        # the same size as the Window
        Size = self.GetClientSize()

        # Make new offscreen bitmap: this bitmap will always have the
        # current drawing in it, so it can be used to save the image to
        # a file, or whatever.
        self._Buffer = wx.Bitmap(*self.res)
        
    def UpdateImage(self, event):
        self.eventLock = event.eventLock
        self.img = event.img
        self.Refresh()
        
        self.ReleaseEventLock()
        
    def ReleaseEventLock(self):
        if self.eventLock:
            if self.eventLock.locked():
                self.eventLock.release()

    
class Client():
    """Client class to interact with slmPy running on a distant server."""
    def __init__(self):
        pass

    def start(self, server_address, port = 9999):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((server_address, port))
            print(f'Connected to {server_address} on {port}')
        except socket.error as e:
            print(f'Connection to {server_address} on port {port} failed: {e}')
            return

    def send_numpy_array(self, np_array):
        """
        :param np_array: Numpy array to send to the listening socket
        :type np_array: ndarray
        :return: None
        :rtype: None
        """
        data = np_array.tostring()

        # Send message length first
        # using "i" cause "L" for unsigned long does not have the same
        # size on different systems (4 on raspberry pi!)
        message_size = struct.pack("i", len(data)) 

        # Then send data
        self.client_socket.sendall(message_size + data)
        
    def sendArray(self, arr, timeout = 10):
        if not isinstance(arr, np.ndarray):
            print('Not a valid numpy image')
            return
        if not arr.dtype == np.uint8:
            print('Numpy array should be of uint8 type')

        self.send_numpy_array(arr)
        print('Waiting for reply from the server')

        t0 = time.time()
        while True:
            buffer = self.client_socket.recv(128)
            if buffer and buffer.decode() == 'done':
                print('Data transmitted')
                return 1
            elif buffer and buffer.decode() == 'err':
                print('Error. Data not transmitted')
                print('Wrong image size?')
                return -1
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
            
    def listen_port(self, port = 9999, check_image_size = False):
        """
        Liston to a port for data transmission.
        Update the SLM with the array transmitted.
        Use a `Client` abject to send arrays from a client. 
        
        Parameters
        ----------
        port : int
            The port to listen to and receive the data from.
        check_image_size : bool
            If `check_image_size` is True, an image that does not fit
            the resolution of the SLM will not be displayed and an 
            error will be returned to the client.

        """
        server_socket=socket.socket() 
        server_socket.bind(('',port))
        server_socket.listen(1)
        print(f'waiting for a connection on port {port}')
        client_connection,client_address=server_socket.accept()
        print(f'connected to {client_address[0]}')      
        
        payload_size = struct.calcsize("i") 
        print(f'Payload size = {payload_size}') 
        while True:
            data=b''
            while len(data) < payload_size:
                data += client_connection.recv(4096)

            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("i", packed_msg_size)[0]
            # Retrieve all data based on message size
            while len(data) < msg_size:
                data += client_connection.recv(4096)

            frame_data = data[:msg_size]
            data = data[msg_size:]

            # Extract frame
            print('Received image')
            #image = pickle.loads(frame_data, encoding='latin1')
            image = np.frombuffer(frame_data, dtype = np.uint8)

            resX, resY = self.vt.frame._resX, self.vt.frame._resY
            if check_image_size and not len(image) == resY*resX:
                print('Buffer size does not match image size')
                print(f'Expected {resX*resY}, received: {len(image)}')
                client_connection.sendall(b'err')
                continue
            
            image = image.reshape([resY,resX])
            print('Updating SLM')
            self.updateArray(image, sleep = 0.)
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
         self.vt.frame.Quit()

class videoThread(threading.Thread):
    """Run the MainLoop as a thread. 
    WxPython is not designed for that, it will give a warning on exit, but it will work, 
    see: https://wiki.wxpython.org/MainLoopAsThread
    Access the frame with self.frame."""
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
