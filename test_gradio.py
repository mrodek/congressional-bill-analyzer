import gradio as gr
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_gradio.log')
    ]
)
logger = logging.getLogger('TestGradio')

def handle_input(input_text):
    """Simple function to echo the input text"""
    logger.info(f"Received input: {input_text}")
    try:
        return f"You entered: {input_text}"
    except Exception as e:
        logger.error(f"Error in handle_input: {str(e)}")
        logger.error(traceback.format_exc())
        return f"Error: {str(e)}"

def create_interface():
    """Create a simple Gradio interface with one input and one output"""
    logger.info("Creating test Gradio interface...")
    try:
        with gr.Blocks(title="Gradio Test App") as app:
            logger.info("Setting up UI components...")
            
            # Input section
            input_text = gr.Textbox(
                label="Enter text",
                placeholder="Type something here..."
            )
            submit_btn = gr.Button("Submit", variant="primary")
            
            # Output section
            output_text = gr.Textbox(
                label="Output"
            )
            
            logger.info("Setting up event handlers...")
            submit_btn.click(
                fn=handle_input,
                inputs=[input_text],
                outputs=[output_text]
            )
            
            logger.info("Interface created successfully")
            return app
    except Exception as e:
        logger.error(f"Error creating interface: {str(e)}")
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    try:
        app = create_interface()
        logger.info("Starting server...")
        app.launch()
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        logger.error(traceback.format_exc())
