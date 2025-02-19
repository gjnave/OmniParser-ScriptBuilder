import json
import os
from PIL import Image, ImageDraw
import numpy as np
from typing import List, Dict, Any, Tuple, Union
import time
from datetime import datetime

class OmniParserCore:
    def load_config(self) -> Dict:
        """Load existing config or create new one if doesn't exist"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            return {"elements": {}, "sequences": []}
        except PermissionError:
            print(f"Error: No permission to read/write config file at {self.config_file}")
            return {"elements": {}, "sequences": []}

    def __init__(self):
        self.working_dir = os.getcwd()
        self.scripts_dir = os.path.join(self.working_dir, "scripts")
        self.parsed_dir = os.path.join(self.working_dir, "parsed")  # New parsed directory
        self.config_file = os.path.join(self.working_dir, "config.json")
        self.config_data = self.load_config()
        self.action_sequence = []
        
        # Create necessary directories
        for directory in [self.scripts_dir, self.parsed_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
        
        # Define key aliases - mapping common variations to standard keys
        self.key_aliases = {
            'del': 'delete',
            'esc': 'escape',
            'ins': 'insert',
            'ret': 'return',
            'enter': 'return',
            'pgup': 'pageup',
            'pgdn': 'pagedown',
            'break': 'pause',
            'space': 'spacebar',
            ' ': 'spacebar',
        }
        
        # Define allowed single keys with all common variations
        self.allowed_single_keys = {
            # Function keys
            'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
            
            # Navigation
            'up', 'down', 'left', 'right',
            'pageup', 'pgup', 'pagedown', 'pgdn',
            'home', 'end',
            
            # Control keys
            'return', 'enter',
            'escape', 'esc',
            'tab',
            'spacebar', 'space',
            'backspace',
            'delete', 'del',
            'insert', 'ins',
            'pause', 'break'
        }

        # Add scroll directions
        self.wheel_directions = {
            'up', 'down', 'left', 'right'
        }

    def save_config(self):
        """Save current config to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config_data, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {str(e)}")

    def save_parsed_data(self, image_path: str, labeled_image: np.ndarray, elements: List[Dict]) -> Tuple[str, str]:
        """
        Save the labeled image and elements data to the parsed directory.
        Returns tuple of (saved_image_path, saved_json_path)
        """
        try:
            # Get base filename without extension
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            
            # Create paths for new files
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"{base_name}_{timestamp}_labeled.png"
            json_filename = f"{base_name}_{timestamp}_elements.json"
            
            saved_image_path = os.path.join(self.parsed_dir, image_filename)
            saved_json_path = os.path.join(self.parsed_dir, json_filename)
            
            # Save labeled image
            labeled_image_pil = Image.fromarray(labeled_image)
            labeled_image_pil.save(saved_image_path)
            
            # Save elements data
            with open(saved_json_path, 'w') as f:
                json.dump({
                    'original_image': image_path,
                    'labeled_image': image_filename,
                    'timestamp': timestamp,
                    'elements': elements
                }, f, indent=2)
                
            return saved_image_path, saved_json_path
            
        except Exception as e:
            print(f"Error saving parsed data: {str(e)}")
            import traceback
            traceback.print_exc()
            return "", ""

    def reset_sequence(self):
        """Reset the current sequence and config data"""
        self.action_sequence = []
        self.config_data = {"elements": {}, "sequences": []}
        self.save_config()
        return "Sequence reset successfully"

    def validate_key_command(self, key_command: str) -> Tuple[bool, str, str]:
        """
        Validate a key command and determine if it's safe to use.
        Returns (is_valid, error_message, command_type)
        """
        if not key_command:
            return False, "Empty key command", ""

        # Normalize the key command
        key_command = key_command.lower().strip()
        
        # Check if it's a single key
        if '+' not in key_command:
            # Check for aliases first
            if key_command in self.key_aliases:
                key_command = self.key_aliases[key_command]
            
            if key_command in self.allowed_single_keys:
                return True, "", "single"
            return False, f"Single key '{key_command}' not in allowed list", ""

        # For key combinations, just validate format
        parts = key_command.split('+')
        if not all(part.strip() for part in parts):
            return False, "Invalid key combination format", ""
            
        return True, "", "combination"

    def process_image(self, image_path: str):
        """Process image and return annotated image and elements"""
        try:
            from utils import get_som_labeled_img, check_ocr_box, get_caption_model_processor, get_yolo_model
            
            # First get OCR results
            ocr_bbox_rslt, is_goal_filtered = check_ocr_box(
                image_path, 
                display_img=False, 
                output_bb_format='xyxy', 
                goal_filtering=None, 
                easyocr_args={'paragraph': False, 'text_threshold':0.9}, 
                use_paddleocr=True
            )
            text, ocr_bbox = ocr_bbox_rslt
            
            som_model = get_yolo_model(model_path="weights/icon_detect/best.pt")
            som_model.to("cuda")
            
            caption_model_processor = get_caption_model_processor(
                model_name="florence2", 
                model_name_or_path="weights/icon_caption_florence", 
                device="cuda"
            )
            
            # Calculate box overlay ratio
            img = Image.open(image_path)
            box_overlay_ratio = img.size[0] / 3200
            
            draw_bbox_config = {
                'text_scale': 0.8 * box_overlay_ratio,
                'text_thickness': max(int(2 * box_overlay_ratio), 1),
                'text_padding': max(int(3 * box_overlay_ratio), 1),
                'thickness': max(int(3 * box_overlay_ratio), 1),
            }
            
            # Process image with OCR results
            dino_labeled_img, label_coordinates, parsed_content_list = get_som_labeled_img(
                image_path,
                som_model,
                BOX_TRESHOLD=0.05,
                output_coord_in_ratio=False,
                ocr_bbox=ocr_bbox,
                draw_bbox_config=draw_bbox_config,
                caption_model_processor=caption_model_processor,
                ocr_text=text
            )
            
            # Create elements list
            elements = []
            for i, content in enumerate(parsed_content_list):
                coords = label_coordinates.get(str(i))
                if coords is not None:
                    center_x = int(coords[0] + coords[2]/2)
                    center_y = int(coords[1] + coords[3]/2)
                    elements.append({
                        "id": i,
                        "name": f"Element {i}: {content}",
                        "coordinates": (center_x, center_y),
                        "bbox": coords.tolist()
                    })

            # Convert base64 image to numpy array
            import base64, io
            labeled_image = Image.open(io.BytesIO(base64.b64decode(dino_labeled_img)))
            labeled_image_array = np.array(labeled_image)
            
            # Save the processed data
            saved_image_path, saved_json_path = self.save_parsed_data(
                image_path, 
                labeled_image_array, 
                elements
            )
            
            if saved_image_path and saved_json_path:
                print(f"Saved labeled image to: {saved_image_path}")
                print(f"Saved elements data to: {saved_json_path}")
            
            return labeled_image_array, elements
                
        except Exception as e:
            print(f"Error in process_image: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, []

    def add_action_extended(self, action_type: str, action_value: Any, pause: float, elements: List[Dict]):
        """Add action to sequence with support for multiple action types"""
        try:
            action_id = f"action_{len(self.action_sequence)}"
            
            if action_type == "wheel":
                direction = action_value.get('direction', '').lower()
                clicks = int(action_value.get('clicks', 1))
                
                if direction not in self.wheel_directions:
                    return f"Error: Invalid wheel direction '{direction}'"
                
                self.config_data["elements"][action_id] = {
                    "type": "wheel",
                    "direction": direction,
                    "clicks": clicks,
                    "name": f"Scroll {direction} ({clicks} clicks)",
                    "pause": pause
                }
            
            elif action_type == "click":
                self.config_data["elements"][action_id] = {
                    "type": "click",
                    "name": action_value["name"],
                    "coordinates": action_value["coordinates"],
                    "pause": pause
                }
            
            elif action_type == "right_click":
                self.config_data["elements"][action_id] = {
                    "type": "right_click",
                    "name": action_value["name"],
                    "coordinates": action_value["coordinates"],
                    "pause": pause
                }
            
            elif action_type == "text":
                self.config_data["elements"][action_id] = {
                    "type": "text",
                    "value": action_value,
                    "name": f"Type text: {action_value[:20]}{'...' if len(action_value) > 20 else ''}",
                    "pause": pause
                }
            
            elif action_type == "keys":
                # Validate key command before adding
                is_valid, error_msg, _ = self.validate_key_command(action_value)
                if not is_valid:
                    return f"Error: {error_msg}"

                self.config_data["elements"][action_id] = {
                    "type": "keys",
                    "value": action_value,
                    "name": f"Press keys: {action_value}",
                    "pause": pause
                }
            
            else:
                return f"Unknown action type: {action_type}"
            
            self.action_sequence.append(action_id)
            self.config_data["sequences"].append(action_id)
            self.save_config()
                
            return f"Added action: {self.config_data['elements'][action_id]['name']} with {pause}s pause"
            
        except Exception as e:
            return f"Error adding action: {str(e)}"

    def generate_script(self, loop_enabled=False):
        """Generate Python script from recorded sequence with support for all action types"""
        try:
            # Define the initial script with no indentation
            script = (
                "import pyautogui\n"
                "import time\n"
                "from ctypes import windll\n"
                "import win32con\n"
                "import win32api\n"
                "import keyboard\n"
                "\n"
                "def execute_sequence():\n"
                "    # Initialize\n"
                "    pyautogui.FAILSAFE = True\n"
                "    print(\"Starting sequence...\")\n"
                "    time.sleep(3)  # Initial delay to switch windows"
            )

            # Add loop structure if enabled
            if loop_enabled:
                script += (
                    "\n"
                    "    try:\n"
                    "        while True:\n"
                    "            print(\"\\nStarting loop iteration...\")"
                )
                # Indent the action content for loop
                action_indent = "            "
            else:
                action_indent = "    "

            for action_id in self.action_sequence:
                element = self.config_data["elements"][action_id]
                action_type = element.get("type", "click")
                
                script += f"\n{action_indent}# Action: {element['name']}\n"
                script += f"{action_indent}print(\"Executing: {element['name']}\")\n"
                
                if action_type == "wheel":
                    direction = element["direction"]
                    clicks = element["clicks"]
                    
                    if direction in ['up', 'down']:
                        amount = (clicks * 100) if direction == 'up' else -(clicks * 100)
                        script += f"{action_indent}pyautogui.scroll({amount})  # Scroll {direction}\n"
                    else:  # left or right
                        amount = -(clicks * 100) if direction == 'left' else (clicks * 100)
                        script += f"{action_indent}pyautogui.hscroll({amount})  # Scroll {direction}\n"
                
                elif action_type == "click":
                    coords = element["coordinates"]
                    script += f"{action_indent}pyautogui.moveTo({coords[0]}, {coords[1]}, duration=0.5)\n"
                    script += f"{action_indent}pyautogui.click()\n"
                
                elif action_type == "right_click":
                    coords = element["coordinates"]
                    script += f"{action_indent}pyautogui.moveTo({coords[0]}, {coords[1]}, duration=0.5)\n"
                    script += f"{action_indent}pyautogui.rightClick()\n"
                
                elif action_type == "text":
                    script += f"{action_indent}pyautogui.write(\"{element['value']}\")\n"
                
                elif action_type == "keys":
                    key_command = element['value'].lower().strip()
                    
                    if key_command in ['esc', 'escape']:
                        script += (
                            f"{action_indent}# Using both keyboard library and Windows API for reliable ESC\n"
                            f"{action_indent}keyboard.send('esc', do_press=True, do_release=True)\n"
                            f"{action_indent}time.sleep(0.1)\n"
                            f"\n"
                            f"{action_indent}# Backup method using Windows API with scan code\n"
                            f"{action_indent}scan_code = 0x01  # ESC scan code\n"
                            f"{action_indent}windll.user32.keybd_event(win32con.VK_ESCAPE, scan_code, 0, 0)  # Key down\n"
                            f"{action_indent}time.sleep(0.1)\n"
                            f"{action_indent}windll.user32.keybd_event(win32con.VK_ESCAPE, scan_code, win32con.KEYEVENTF_KEYUP, 0)  # Key up\n"
                        )
                    else:
                        is_valid, _, command_type = self.validate_key_command(key_command)
                        if not is_valid:
                            script += f"{action_indent}# Warning: Invalid key command {key_command}\n"
                        elif command_type == "single":
                            script += f"{action_indent}pyautogui.press(\"{key_command}\")\n"
                        else:  # combination
                            script += f"{action_indent}pyautogui.hotkey(*\"{key_command}\".split('+'))\n"
                
                if element["pause"] > 0:
                    script += f"{action_indent}time.sleep({element['pause']})  # Pause for {element['pause']} seconds\n"
            
            if loop_enabled:
                script += (
                    "\n            time.sleep(0.5)  # Short delay between iterations\n"
                    "    except KeyboardInterrupt:\n"
                    "        print(\"\\nLoop stopped by user\")"
                )

            script += (
                "\n"
                "\n"
                "if __name__ == \"__main__\":\n"
                "    print(\"Press Ctrl+C to stop the sequence\")\n"
                "    try:\n"
                "        execute_sequence()\n"
                "    except KeyboardInterrupt:\n"
                "        print(\"\\nSequence stopped by user\")"
            )
            
            # Generate a simpler sequence number based on timestamp
            seq_num = len(os.listdir(self.scripts_dir)) + 1
            script_filename = os.path.join(self.scripts_dir, f"sequence_{seq_num}.py")
            
            # Save script to file
            with open(script_filename, 'w') as f:
                f.write(script)
            
            return f"Script generated: {script_filename}"
            
        except Exception as e:
            raise e
