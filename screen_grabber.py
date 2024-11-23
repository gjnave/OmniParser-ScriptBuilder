import os
import time
from datetime import datetime
from pathlib import Path
import keyboard
import pyautogui
from PIL import Image

def get_next_session_number():
    base_dir = Path("images")
    if not base_dir.exists():
        return 1
    
    existing_sessions = [int(d.name) for d in base_dir.iterdir() if d.is_dir() and d.name.isdigit()]
    return 1 if not existing_sessions else max(existing_sessions) + 1

def ensure_session_directory():
    # Create base images directory if it doesn't exist
    base_dir = Path("images")
    base_dir.mkdir(exist_ok=True)
    
    # Get next session number and create directory
    next_session = get_next_session_number()
    session_dir = base_dir / str(next_session)
    session_dir.mkdir(exist_ok=True)
    return session_dir

def take_screenshot(session_dir=None):
    # Create session directory if this is the first screenshot
    if session_dir is None:
        session_dir = ensure_session_directory()
        print(f"Created new session directory: {session_dir}")
    
    # Generate timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    filepath = session_dir / filename
    
    # Take screenshot
    screenshot = pyautogui.screenshot()
    screenshot.save(filepath)
    print(f"Screenshot saved: {filepath}")
    
    return session_dir

def main():
    print("Screenshot application running...")
    print("Press Ctrl+Shift+PrintScreen to take a screenshot")
    print("Press Ctrl+C to exit")
    
    # Initialize session_dir as None - it will be created on first screenshot
    session_dir = None
    
    def on_trigger():
        nonlocal session_dir
        session_dir = take_screenshot(session_dir)
    
    # Register hotkey (Ctrl + Shift + PrintScreen)
    keyboard.add_hotkey('ctrl+shift+print_screen', on_trigger)
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting application...")

if __name__ == "__main__":
    main()