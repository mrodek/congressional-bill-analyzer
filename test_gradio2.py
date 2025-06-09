import gradio as gr
import logging
import datetime
import traceback

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gradio_app.log'),
        logging.StreamHandler()  # Also log to console
    ]
)

logger = logging.getLogger(__name__)

def log_startup():
    """Log application startup information"""
    logger.info("="*50)
    logger.info("GRADIO APPLICATION STARTING")
    logger.info(f"Timestamp: {datetime.datetime.now()}")
    logger.info(f"Gradio version: {gr.__version__}")
    logger.info("="*50)

def echo_handler(input_text):
    """
    Simple event handler that echoes the input text
    Includes comprehensive logging of the interaction
    """
    try:
        logger.info(f"EVENT HANDLER CALLED")
        logger.info(f"Input received: '{input_text}'")
        logger.info(f"Input type: {type(input_text)}")
        logger.info(f"Input length: {len(input_text) if input_text else 0}")
        
        # Simple echo logic
        if input_text is None or input_text.strip() == "":
            output_text = "Please enter some text to echo."
            logger.info("Empty input detected - returning prompt message")
        else:
            output_text = f"Echo: {input_text}"
            logger.info(f"Echoing input text successfully")
        
        logger.info(f"Output generated: '{output_text}'")
        logger.info("Event handler completed successfully")
        
        return output_text
        
    except Exception as e:
        error_msg = f"Error in echo_handler: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Return a more user-friendly error message
        return f"An error occurred: {str(e)}"

def create_interface():
    """Create and configure the Gradio interface"""
    try:
        logger.info("CREATING GRADIO INTERFACE")
        
        # Create interface components
        logger.info("Creating input textbox component")
        input_textbox = gr.Textbox(
            label="Input Text",
            placeholder="Enter text here to echo...",
            lines=2
        )
        
        logger.info("Creating output textbox component")
        output_textbox = gr.Textbox(
            label="Echo Output",
            lines=2,
            interactive=False
        )
        
        logger.info("Creating submit button component")
        submit_button = gr.Button("Submit", variant="primary")
        
        # Create the interface using Blocks for better control
        logger.info("Creating Gradio interface with Blocks")
        with gr.Blocks(title="Simple Echo Interface") as interface:
            logger.info("Setting up UI components")
            
            # Add description
            gr.Markdown("Enter text and click Submit to see it echoed back.")
            
            # Input section
            input_textbox.render()
            submit_button.render()
            
            # Output section
            output_textbox.render()
            
            # Set up event handler
            logger.info("Setting up event handler")
            try:
                logger.info("Registering click event for submit button")
                submit_button.click(
                    fn=echo_handler,
                    inputs=input_textbox,  # Remove list brackets
                    outputs=output_textbox  # Remove list brackets
                )
                logger.info("Successfully registered click event")
            except Exception as e:
                logger.error(f"Error registering click event: {str(e)}")
                logger.error(traceback.format_exc())
            
            # Add clear button
            clear_button = gr.Button("Clear")
            try:
                logger.info("Registering click event for clear button")
                clear_button.click(
                    fn=lambda: ("", ""),  # Return empty strings for both input and output
                    inputs=None,
                    outputs=[input_textbox, output_textbox]
                )
                logger.info("Successfully registered clear button event")
            except Exception as e:
                logger.error(f"Error registering clear button event: {str(e)}")
                logger.error(traceback.format_exc())
        
        logger.info("Gradio interface created successfully")
        return interface
        
    except Exception as e:
        logger.error(f"Error creating interface: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

def setup_event_handlers(interface):
    """Set up additional event handlers and logging"""
    try:
        logger.info("SETTING UP EVENT HANDLERS")
        
        # Log when the interface is about to launch
        logger.info("Event handlers configured successfully")
        
    except Exception as e:
        logger.error(f"Error setting up event handlers: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")

def main():
    """Main function to run the application"""
    try:
        # Initialize logging
        log_startup()
        
        # Create interface
        interface = create_interface()
        
        # Set up event handlers
        setup_event_handlers(interface)
        
        # Launch the interface
        logger.info("LAUNCHING GRADIO INTERFACE")
        logger.info("Interface will be available at: http://localhost:7860")
        logger.info("Press Ctrl+C to stop the server")
        
        interface.launch(
            server_name="0.0.0.0",  # Makes it accessible from other devices
            server_port=7860,
            share=False,  # Set to True if you want a public link
            debug=True,   # Enable debug mode for more detailed logging
            show_error=True
        )
        
    except KeyboardInterrupt:
        logger.info("Application stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        logger.info("APPLICATION SHUTTING DOWN")
        logger.info("="*50)

if __name__ == "__main__":
    main()