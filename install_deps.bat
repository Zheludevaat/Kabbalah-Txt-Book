@echo off
REM Install Python dependencies with upgrades
pip install -U -r requirements.txt
REM Install Node.js dependencies for the Electron app
cd electron-app
npm install
cd ..
