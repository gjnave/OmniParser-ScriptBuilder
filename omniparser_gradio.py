import gradio as gr
from omniparser_core import OmniParserCore
from PIL import Image
import numpy as np

def create_interface():
    parser = OmniParserCore()
    current_elements = []
    
    def process_and_display(image, current_status):
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
        
        # Append new status to existing status instead of replacing
        new_status = f"\nFound {len(elements)} elements in new image"
        return annotated_image, gr.Dropdown(choices=element_choices), current_status + new_status

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

    def generate_final_script(current_status):
        result = parser.generate_script()
        return current_status + f"\n{result}"

    def reset_sequence():
        nonlocal current_elements
        current_elements = []
        result = parser.reset_sequence()
        return (
            None,  # Clear image
            gr.Dropdown(choices=[], value=None),  # Clear dropdown
            result  # Reset status to initial message
        )

    interface = gr.Blocks(title="OmniParser Sequence Builder")
    
    with interface:
        gr.Markdown("# OmniParser Sequence Builder")
        with gr.Row():
            with gr.Column(scale=1):
                input_image = gr.Image(label="Upload Image", type="filepath")
                process_btn = gr.Button("Process Image")
                reset_btn = gr.Button("Reset Sequence", variant="secondary")
            
            with gr.Column(scale=2):
                output_image = gr.Image(
                    label="Annotated Image",
                    show_download_button=True,
                    height=800,
                    width=1200,
                    interactive=True,
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
                        choices=["left_click", "right_click"],  # Removed wheel from here
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
                        choices=["click", "text", "keys", "wheel"],  # Added wheel as its own action type
                        value="click",
                        type="value"
                    )
                    
                pause_input = gr.Number(label="Pause Duration (seconds)", value=0)
                add_btn = gr.Button("Add to Sequence")
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
            inputs=[status_text],
            outputs=[status_text]
        )

        reset_btn.click(
            reset_sequence,
            inputs=[],
            outputs=[output_image, element_dropdown, status_text]
        )
        
        # Just before interface.launch(), add:
            
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