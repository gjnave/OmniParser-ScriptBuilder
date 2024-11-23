import os
import subprocess
import sys
from pathlib import Path

def list_python_files():
    """List all Python files in the scripts folder and return as a dictionary."""
    try:
        scripts_dir = Path('scripts')
        if not scripts_dir.exists():
            print("Error: 'scripts' folder not found!")
            sys.exit(1)
            
        python_files = list(scripts_dir.glob('*.py'))
        if not python_files:
            print("No Python files found in 'scripts' folder!")
            sys.exit(1)
            
        file_dict = {}
        for idx, file in enumerate(python_files, 1):
            file_dict[idx] = file
            print(f"{idx}. {file.name}")
        return file_dict
    except Exception as e:
        print(f"Error listing files: {e}")
        sys.exit(1)

def rename_file(file_path):
    """Rename the selected file."""
    try:
        new_name = input("Enter new filename (without .py extension): ").strip()
        # Automatically add .py extension
        new_name = new_name if new_name.endswith('.py') else f"{new_name}.py"
            
        new_path = file_path.parent / new_name
        if new_path.exists():
            print("Error: A file with that name already exists!")
            return
            
        file_path.rename(new_path)
        print(f"File renamed to: {new_name}")
    except Exception as e:
        print(f"Error renaming file: {e}")

def run_file(file_path):
    """Run the selected Python script."""
    try:
        print(f"\nRunning {file_path.name}...")
        print("-" * 40)
        subprocess.run([sys.executable, str(file_path)], check=True)
        print("-" * 40)
    except subprocess.CalledProcessError as e:
        print(f"Error running script: {e}")

def delete_file(file_path):
    """Delete the selected file after confirmation."""
    try:
        confirm = input(f"Are you sure you want to delete {file_path.name}? (yes/no): ").lower()
        if confirm == 'yes':
            file_path.unlink()
            print(f"File deleted: {file_path.name}")
        else:
            print("Deletion cancelled.")
    except Exception as e:
        print(f"Error deleting file: {e}")

def edit_file(file_path):
    """Open the selected file in Notepad."""
    try:
        print(f"Opening {file_path.name} in Notepad...")
        subprocess.Popen(['notepad.exe', str(file_path)])
    except Exception as e:
        print(f"Error opening file in Notepad: {e}")

def main():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\nPython Script Manager")
        print("=" * 20)
        print("\nChoose an action:")
        print("a) Run file")    # Swapped with rename
        print("b) Rename file") # Swapped with run
        print("c) Edit file")
        print("d) Delete file")
        print("q) Quit")
        
        choice = input("\nEnter your choice: ").lower()
        
        if choice == 'q':
            print("Goodbye!")
            break
            
        if choice not in ['a', 'b', 'c', 'd']:
            print("Invalid choice!")
            input("Press Enter to continue...")
            continue
            
        print("\nAvailable Python files:")
        files = list_python_files()
        
        try:
            file_choice = int(input("\nEnter file number: "))
            if file_choice not in files:
                print("Invalid file number!")
                input("Press Enter to continue...")
                continue
                
            selected_file = files[file_choice]
            
            if choice == 'a':
                run_file(selected_file)     # Swapped with rename
            elif choice == 'b':
                rename_file(selected_file)  # Swapped with run
            elif choice == 'c':
                edit_file(selected_file)
            elif choice == 'd':
                delete_file(selected_file)
                
        except ValueError:
            print("Please enter a valid number!")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()