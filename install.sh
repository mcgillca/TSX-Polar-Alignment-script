#!/bin/bash

function installUI() 
{
	sudo mkdir -p /usr/local/bin/
	sudo cp -f PAUI.py /usr/local/bin/
	sudo chmod oug+x /usr/local/bin/PAUI.py
	sudo mkdir -p /usr/share/pixmaps/
	sudo cp -f PAIcon.png /usr/share/pixmaps
	cp -f PA.desktop ~/Desktop
	sudo desktop-file-install ~/Desktop/PA.desktop
	sudo update-desktop-database
}

installUI
UIOk=$?
if [ "$UIOk" = "0" ]; then
	echo "Polar Alignment UI tools installed"
else
	echo "Polar Alignment UI tools installation failed"
fi




