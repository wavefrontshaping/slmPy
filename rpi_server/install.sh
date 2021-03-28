#!/usr/bin/bash

sudo apt-get install python3-pip -y

# install wxPython (required for slmPy)
# sudo apt-get install libgtk-3-dev -y
sudo apt install python3-wxgtk4.0 -y

sudo python3 -m pip install wxPython

# deactivate screen blanking
sudo bash -c 'echo -e "\n[SeatDefaults]\nxserver-command=X -s 0 -dpms" >> /etc/lightdm/lightdm.conf'


git clone --branch network https://github.com/wavefrontshaping/slmPy.git
cd slmPy
sudo python3 setup.py install 

# mkdir -p /home/pi/.config/lxsession/LXDE-pi/autostart

# copy the server script that listen to port 9999 
# and display the received masks on the SLM
cp rpi_server/server.py /home/pi
# create a desktop file that will launch the server script on startup
cp rpi_server/SLM.desktop /home/pi/.config/autostart

cd ..
rm -rf slmPy

#sudo bash -c 'echo "consoleblank=0" >> /boot/cmdline.txt'
