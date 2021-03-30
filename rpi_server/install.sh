#!/usr/bin/bash
# connect via ssn and execute this lines
# git clone --branch network https://github.com/wavefrontshaping/slmPy.git
# cd slmPy && bash rpi_server/install.sh

sudo apt-get install python3-pip -y

# install wxPython (required for slmPy)
# sudo apt-get install libgtk-3-dev -y
#sudo apt install python3-wxgtk4.0 -y

sudo python3 -m pip install wxPython

# deactivate screen blanking
sudo bash -c 'echo -e "\n[SeatDefaults]\nxserver-command=X -s 0 -dpms" >> /etc/lightdm/lightdm.conf'

# the repo
sudo python3 setup.py install 

# copy the server script that listens to port 9999 
# and display the received masks on the SLM
cp rpi_server/server.py /home/pi/
# create a desktop file that will launch the server script on startup
mkdir -p /home/pi/.config/autostart
cp rpi_server/SLM.desktop /home/pi/.config/autostart/

cd ..
rm -rf slmPy

export DISPLAY=:0
xrandr --output HDMI-1 --mode "800x600"
sudo reboot

#sudo bash -c 'echo "consoleblank=0" >> /boot/cmdline.txt'
