@echo off
REM Install Python dependencies
pip install -U -r requirements.txt
REM Install Node.js dependencies and launch Electron app
cd electron-app
npm install
npm start
