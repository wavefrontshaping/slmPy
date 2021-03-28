from slmpy import SLMdisplay
import time

PORT = 9999 

## initialize SLM
slm = SLMdisplay(monitor = 0, isImageLock = True)
resX, resY = slm.getSize()
print(f'Resolution: {resX}x{resY}')
slm.listen_port(port = PORT)

slm.close()
