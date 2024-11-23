import pyautogui
    import time
    from ctypes import windll
    import win32con
    import win32api
    import keyboard

    def execute_sequence():
        # Initialize
        pyautogui.FAILSAFE = True
        print("Starting sequence...")
        time.sleep(3)  # Initial delay to switch windows
    
    # Action: Scroll up (20 clicks)
    print("Executing: Scroll up (20 clicks)")
    pyautogui.scroll(2000)  # Scroll up

        print("Sequence completed!")

    if __name__ == "__main__":
        print("Press Ctrl+C to stop the sequence")
        try:
            execute_sequence()
        except KeyboardInterrupt:
            print("\nSequence stopped by user")
    