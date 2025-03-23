# Portable Screen Capture Tool

A lightweight, portable screen capture tool for Windows that works in virtual environments. This tool allows you to:

- Select a specific region of your screen by drawing a rectangle
- Automatically copy the captured region to Windows clipboard
- See the dimensions of your selection in real-time

## Installation in a Virtual Environment

1. Create a virtual environment:
   ```
   python -m venv venv
   ```

2. Activate the virtual environment:
   ```
   # On Windows
   venv\Scripts\activate
   
   # On Unix/MacOS
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the application:
   ```
   python KuduGrab.py
   ```

## Creating a Standalone Executable

For maximum portability, you can create a standalone executable:

1. Ensure you have PyInstaller installed in your virtual environment:
   ```
   pip install pyinstaller
   ```

2. Create the executable:
   ```
   pyinstaller --onefile --windowed KuduGrab.py
   ```

3. Find the executable in the `dist` folder

## How to Use

1. Launch the application
2. Click "Start Capture"
3. Click and drag to select the area you want to capture
4. Release the mouse button to complete the capture and copy to clipboard
5. Press ESC to cancel a capture in progress

## Features

- Portable design works in virtual environments
- No system registry modifications
- Shows real-time dimensions of selection
- Visual feedback during capture
- Copies directly to clipboard
- ESC key to cancel capture
- Compatible with high DPI displays

## Requirements

- Python 3.7+
- PyQt5
- Pillow (PIL)