#!/bin/bash
set -e

# Install Python dependencies
pip install -U -r requirements.txt

# Install Node.js dependencies for the Electron app
cd electron-app
npm install

# Launch the Electron desktop application
npm start
