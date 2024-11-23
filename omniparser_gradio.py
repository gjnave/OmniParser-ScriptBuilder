import gradio as gr
from omniparser_core import OmniParserCore
from PIL import Image
import numpy as np
import os
import json

def create_interface():
    parser = OmniParserCore()
    current_elements = []
    
    def load_elements_from_json(image_path):
        """Load elements data from corresponding JSON file"""
        try:
            # Get base name of the image (excluding _labeled.png)
            base_name = os.path.basename(image_path)
            if '_labeled.png' in base_name:
                base_name = base_name.replace('_labeled.png', '')
            
            # Look for matching JSON file in parsed directory
            json_files = [f for f in os.listdir(parser.parsed_dir) if f.startswith(base_name) and f.endswith('_elements.json')]
            
            if json_files:
                # Use the most recent JSON file if multiple matches exist
                json_file = sorted(json_files)[-1]
                json_path = os.path.join(parser.parsed_dir, json_file)
                
                with open(json_path, 'r') as f:
                    data = json.load(f)
                    return data.get('elements', [])
            
            return []
            
        except Exception as e:
            print(f"Error loading JSON data: {str(e)}")
            return []
            
    def reset_sequence():
        nonlocal current_elements
        current_elements = []
        result = parser.reset_sequence()
        return (
            None,  # Clear image
            gr.Dropdown(choices=[], value=None),  # Clear dropdown
            result  # Reset status to initial message
        )

    def process_and_display(image, current_status):
        """Handle new image processing"""
        nonlocal current_elements
        if image is None:
            return None, gr.Dropdown(choices=[], value=None), "Please upload an image"
        
        annotated_image, elements = parser.process_image(image)
        current_elements = elements
        
        element_choices = []
        for e in elements:
            coords = e['coordinates']
            bbox = e.get('bbox', [])
            if bbox:
                element_choices.append(f"{e['name']} at ({coords[0]}, {coords[1]}) [bbox: {bbox}]")
            else:
                element_choices.append(f"{e['name']} at ({coords[0]}, {coords[1]})")
        
        new_status = f"\nFound {len(elements)} elements in new image"
        if elements:
            new_status += "\nImage and elements data saved in 'parsed' directory"
        return annotated_image, gr.Dropdown(choices=element_choices), current_status + new_status

    def load_existing_annotated(image, current_status):
            """Handle loading of existing annotated image"""
            nonlocal current_elements
            if image is None:
                return None, gr.Dropdown(choices=[], value=None), current_status + "\nNo image selected"
            
            try:
                # We get the original filepath from the gradio upload
                original_path = image
                
                # Load elements from corresponding JSON using the original path
                elements = load_elements_from_json(original_path)
                current_elements = elements
                
                # Create dropdown choices
                element_choices = []
                for e in elements:
                    coords = e['coordinates']
                    bbox = e.get('bbox', [])
                    if bbox:
                        element_choices.append(f"{e['name']} at ({coords[0]}, {coords[1]}) [bbox: {bbox}]")
                    else:
                        element_choices.append(f"{e['name']} at ({coords[0]}, {coords[1]})")
                
                # Convert image to numpy array for display
                image_array = np.array(Image.open(original_path))
                
                new_status = f"\nLoaded {len(elements)} elements from existing annotated image"
                return image_array, gr.Dropdown(choices=element_choices), current_status + new_status
                
            except Exception as e:
                print(f"Error in load_existing_annotated: {str(e)}")
                import traceback
                traceback.print_exc()
                return None, gr.Dropdown(choices=[]), current_status + f"\nError loading image: {str(e)}"

    def add_sequence_action(element_choice, click_type, text_input, key_command, wheel_direction, wheel_clicks, pause, action_type, current_status):
        try:
            action_value = None
            
            if action_type == "click":
                action_type = "right_click" if click_type == "right_click" else "click"
                selected_element = None
                for element in current_elements:
                    element_display = f"{element['name']} at ({element['coordinates'][0]}, {element['coordinates'][1]})"
                    if element_display in element_choice:
                        selected_element = element
                        break
                
                if selected_element:
                    action_value = selected_element
            elif action_type == "wheel":
                action_value = {
                    "direction": wheel_direction,
                    "clicks": int(wheel_clicks) if wheel_clicks else 1
                }
            elif action_type == "text":
                action_value = text_input
            elif action_type == "keys":
                action_value = key_command
            else:
                return current_status + "\nPlease select an action to add to the sequence"
            
            result = parser.add_action_extended(
                action_type=action_type,
                action_value=action_value,
                pause=float(pause) if pause else 0,
                elements=current_elements
            )
            return current_status + f"\n{result}"
            
        except Exception as e:
            import traceback
            error_msg = f"\nError adding action: {str(e)}"
            print(error_msg + "\n" + traceback.format_exc())
            return current_status + error_msg

    def generate_final_script(current_status, loop_enabled):  # Remove the default value since gradio will provide it
        result = parser.generate_script(loop_enabled=loop_enabled)
        return current_status + f"\n{result}"

    interface = gr.Blocks()

    with interface:
        gr.Markdown("# OmniParser Sequence Builder")  # Main title
        gr.Markdown('<p style="font-size: 14px; text-align: center;">Sponsored by: <a href="https://niggendo.org" target="_blank">riiahworld</a></p>')  # Smaller text and URL

        with gr.Row():
            with gr.Column(scale=1):
                with gr.Tab("Process New"):
                    input_image = gr.Image(label="Upload New Image", type="filepath")
                    process_btn = gr.Button("Process Image")
                with gr.Tab("Load Existing"):
                    load_image = gr.Image(label="Load Annotated Image", type="filepath")
                    load_btn = gr.Button("Load Image")
                reset_btn = gr.Button("Reset Sequence", variant="secondary")
            
            with gr.Column(scale=2):
                output_image = gr.Image(
                    label="Annotated Image",
                    show_download_button=True,
                    height=800,
                    width=1200,
                    type="numpy"
                )
                
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Action Selection")
                with gr.Group():
                    element_dropdown = gr.Dropdown(
                        label="Select Element", 
                        choices=[],
                        interactive=True
                    )
                    click_type = gr.Dropdown(
                        label="Click Type",
                        choices=["left_click", "right_click"],
                        value="left_click",
                        interactive=True
                    )
                    
                    # Wheel-specific controls
                    with gr.Group() as wheel_controls:
                        wheel_direction = gr.Radio(
                            label="Wheel Direction",
                            choices=["up", "down", "left", "right"],
                            value="down",
                            interactive=True
                        )
                        wheel_clicks = gr.Number(
                            label="Number of Clicks",
                            value=1,
                            minimum=1,
                            step=1,
                            interactive=True
                        )
                    
                    text_input = gr.Textbox(
                        label="Text Input",
                        placeholder="Enter text to type",
                        interactive=True
                    )
                    key_command = gr.Textbox(
                        label="Keyboard Command",
                        placeholder="e.g., ctrl+c, alt+tab",
                        interactive=True
                    )
                    
                    action_type = gr.Radio(
                        label="Select Action",
                        choices=["click", "text", "keys", "wheel"],
                        value="click",
                        type="value"
                    )
                    
                pause_input = gr.Number(label="Pause Duration (seconds)", value=0)
                add_btn = gr.Button("Add to Sequence")
                loop_checkbox = gr.Checkbox(label="Generate Looping Script", value=False)  # Add this line
                generate_btn = gr.Button("Generate Script")
                status_text = gr.Textbox(label="Status", lines=10)
        
        # Event handlers
        def update_controls(action_type):
            return {
                click_type: gr.Dropdown(visible=action_type == "click"),
                element_dropdown: gr.Dropdown(visible=action_type == "click"),
                wheel_controls: gr.Group(visible=action_type == "wheel"),
                text_input: gr.Textbox(visible=action_type == "text"),
                key_command: gr.Textbox(visible=action_type == "keys")
            }
        
        action_type.change(
            update_controls,
            inputs=[action_type],
            outputs=[click_type, element_dropdown, wheel_controls, text_input, key_command]
        )
        
        process_btn.click(
            process_and_display,
            inputs=[input_image, status_text],
            outputs=[output_image, element_dropdown, status_text]
        )
        
        load_btn.click(
            load_existing_annotated,
            inputs=[load_image, status_text],
            outputs=[output_image, element_dropdown, status_text]
        )
        
        add_btn.click(
            add_sequence_action,
            inputs=[
                element_dropdown, click_type, text_input, key_command,
                wheel_direction, wheel_clicks, pause_input, action_type, status_text
            ],
            outputs=[status_text]
        )
        
        generate_btn.click(
            generate_final_script,
            inputs=[status_text, loop_checkbox],  # Add loop_checkbox here
            outputs=[status_text]
        )

        reset_btn.click(
            reset_sequence,
            inputs=[],
            outputs=[output_image, element_dropdown, status_text]
        )
            
        interface.load(
            fn=update_controls,
            inputs=[action_type],
            outputs=[click_type, element_dropdown, wheel_controls, text_input, key_command]
        )
    
    return interface

def main():
    interface = create_interface()
    interface.launch(share=False)

if __name__ == "__main__":
    main()
