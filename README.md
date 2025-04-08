# Autonomous Browser Automation Agent with DeepSeek LLM Integration

## Overview
This project is an autonomous browser automation agent that accepts natural language commands to perform web interactions. It leverages Mozilla Marionette to control the Firefox browser, Flask to expose a RESTful API, and TinyDB to store dynamic DOM context data. An LLM-based command parser, powered by OpenAI’s DeepSeek Chat (deepseek-chat) model and advanced prompt engineering, translates natural language instructions into precise browser actions. In addition, an OCR-based fallback mechanism using OpenCV and pytesseract enhances element detection reliability.

## Features
- **Dynamic DOM Extraction:**  
  Extracts the complete DOM context and a curated set of interactive elements from web pages for analysis and logging.
  
- **RESTful API & CLI Integration:**  
  Provides a Flask API endpoint (`/extract`) for DOM extraction and enables concurrent command-line interactions through multi-threading.
  
- **LLM-Driven Command Parsing:**  
  Utilizes OpenAI’s DeepSeek Chat model with advanced prompt engineering to convert natural language commands into actionable browser automation steps.
  
- **Robust Browser Automation:**  
  Controls browser interactions such as navigation, clicking, text input, and data extraction using Mozilla Marionette.
  
- **Error Recovery & OCR Fallback:**  
  Implements an iterative command execution engine with adaptive recovery strategies and an OCR-based fallback (via OpenCV and pytesseract) to locate elements when standard DOM selectors fail.

## Tech Stack
- **Programming Language:** Python  
- **Web Framework:** Flask  
- **Database:** TinyDB  
- **Browser Automation:** Mozilla Marionette (marionette_driver)  
- **LLM Integration:** OpenAI DeepSeek Chat (deepseek-chat)  
- **OCR & Image Processing:** OpenCV, pytesseract  
- **Other Libraries:** argparse, threading, numpy, base64, time, re

## Installation

# Clone the repo
git clone https://github.com/Abhi-2526/web-agent.git
cd web-agent

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # For Windows: venv\Scripts\activate

# Add openAI API key in .env or command_executor

# Install dependencies
pip install -r requirements.txt

# Start the firefox browser with marionette
/Applications/Firefox.app/Contents/MacOS/firefox --marionette

# Run the automation agent
python main.py

# Test the DOM extraction endpoint (in a separate terminal or after starting the server)
curl "http://localhost:5001/extract?max_elements=200"

