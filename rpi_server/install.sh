#!/usr/bin/bash
# connect via ssn and execute this lines
# git clone --branch network https://github.com/wavefrontshaping/slmPy.git
# cd slmPy && bash rpi_server/install.sh

RESOLUTION="800x600"

echo "Installing Python pip if not present"
sudo apt-get install python3-pip -y

# install wxPython (required for slmPy)
# sudo apt-get install libgtk-3-dev -y
echo "Installing wxPython dependencies"
sudo apt install python3-wxgtk4.0 -y

echo "Installing wxPython"
sudo python3 -m pip install wxPython


echo "Installing SlmPy"
sudo python3 setup.py install 

echo "Copying server script that listens to port 9999 and display the received masks on the SLM" 
cp rpi_server/server.py /home/pi/

echo "Creating a desktop file that will launch the server script on startup"
mkdir -p /home/pi/.config/autostart
cp rpi_server/SLM.desktop /home/pi/.config/autostart/

cd ..
rm -rf slmPy

echo "Deactivate screen blanking/sleep"
sudo bash -c 'echo -e "\n[SeatDefaults]\nxserver-command=X -s 0 -dpms" >> /etc/lightdm/lightdm.conf'

echo "Changing resolution to "$RESOLUTION
export DISPLAY=:0
xrandr --output HDMI-1 --mode $RESOLUTION
sudo reboot