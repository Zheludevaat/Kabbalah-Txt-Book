#!/bin/bash
set -e

# Install Python dependencies with upgrades
pip install -U -r requirements.txt

# Install Node.js dependencies for the Electron app
cd electron-app
npm install
cd ..
