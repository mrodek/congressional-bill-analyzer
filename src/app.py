import gradio as gr
import os
import sys
import traceback
from dotenv import load_dotenv

# Handle imports whether running from project root or src directory
try:
    from congress_api import CongressAPI
    from text_processor import TextProcessor
    from ai_analyzer import AIAnalyzer
    from qa_system import QASystem
except ImportError:
    from src.congress_api import CongressAPI
    from src.text_processor import TextProcessor
    from src.ai_analyzer import AIAnalyzer
    from src.qa_system import QASystem
from typing import Tuple, List, Dict
import logging
import traceback
from typing import Callable, Any, List, Tuple, Dict, Optional
import inspect

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)

# Get the root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Remove existing handlers and add our configured ones
root_logger.handlers = []
root_logger.addHandler(logging.StreamHandler())
root_logger.addHandler(logging.FileHandler('app.log'))

# Set up specific loggers
logger = logging.getLogger('CongressionalBillAnalyzer')
bill_scraper_logger = logging.getLogger('BillScraper')
text_processor_logger = logging.getLogger('TextProcessor')
ai_analyzer_logger = logging.getLogger('AIAnalyzer')
qa_system_logger = logging.getLogger('QASystem')

# Set levels for specific loggers
bill_scraper_logger.setLevel(logging.INFO)
text_processor_logger.setLevel(logging.INFO)
ai_analyzer_logger.setLevel(logging.INFO)
qa_system_logger.setLevel(logging.INFO)

# Helper function to validate Gradio event handler return values
def validate_handler_output(handler_func: Callable) -> Callable:
    """Decorator to validate the output of Gradio event handlers
    to ensure they match the expected structure.
    """
    def wrapper(*args, **kwargs):
        print(f"DEBUG: Entering validate_handler_output for {handler_func.__name__}") # Cascade: Added debug print
        try:
            # Call the original function
            result = handler_func(*args, **kwargs)
            
            # Get function signature and return annotation
            sig = inspect.signature(handler_func)
            return_annotation = sig.return_annotation
            
            # Log the actual return value structure
            logger.debug(f"Handler {handler_func.__name__} returned: {type(result)}, value: {result}")
            print(f"DEBUG: Handler {handler_func.__name__} returned: {type(result)}, value: {{str(result)[:200]}}...") # Cascade: Added debug print, truncated result
            
            # If return annotation is specified, validate the result
            if return_annotation != inspect.Signature.empty:
                if isinstance(result, tuple):
                    print(f"DEBUG: Handler {handler_func.__name__} return value is a tuple with {len(result)} items") # Cascade: Added debug print
                    logger.debug(f"Return value is a tuple with {len(result)} items")
                else:
                    print(f"DEBUG: Handler {handler_func.__name__} return value is not a tuple, but {type(result)}") # Cascade: Added debug print
                    logger.debug(f"Return value is not a tuple, but {type(result)}")
            print(f"DEBUG: Exiting validate_handler_output for {handler_func.__name__} successfully") # Cascade: Added debug print
            return result
        except Exception as e:
            logger.error(f"Error in handler {handler_func.__name__}: {str(e)}")
            logger.error(traceback.format_exc())
            print(f"DEBUG: Error in validate_handler_output for {handler_func.__name__}: {str(e)}") # Cascade: Added debug print
            raise # Ensure exception is re-raised
    
    # Preserve the original function's signature
    wrapper.__name__ = handler_func.__name__
    wrapper.__doc__ = handler_func.__doc__
    wrapper.__annotations__ = handler_func.__annotations__
    
    return wrapper

# Load environment variables
load_dotenv()

# Initialize components
congress_api = CongressAPI()  # Use the official Congress.gov API
text_processor = TextProcessor()
ai_analyzer = AIAnalyzer(os.getenv('OPENAIAPIKEY'))
qa_system = QASystem(
    api_key=os.getenv('OPENAIAPIKEY'),
    db_path=os.getenv('CHROMA_DB_PATH', './data/chromadb')
)

logger.info("AIAnalyzer initialized with API key: " + os.getenv('OPENAIAPIKEY'))
logger.info("QASystem initialized with API key: " + os.getenv('OPENAIAPIKEY'))

# Global variables to store current bill information
current_bill_id = None
current_bill_metadata = None
current_processed_sections = []

def analyze_bill(url: str) -> Tuple[str, float, float, str, int]:
    """Main bill analysis pipeline"""
    logger.info(f"Starting bill analysis for URL:")
    try:
        logger.info(f"Starting bill analysis for URL: {url}")
        
        # 1. Get bill metadata from Congress.gov API
        logger.info("Getting bill metadata from API...")
        try:
            metadata = congress_api.get_bill_metadata(url)
            logger.info(f"Metadata retrieved: {metadata.__dict__}")
        except Exception as e:
            logger.error(f"Error getting bill metadata: {str(e)}\n{traceback.format_exc()}")
            raise Exception(f"Failed to get bill metadata: {str(e)}")
        
        # 2. Get bill text from Congress.gov API
        logger.info("Getting bill text from API...")
        try:
            bill_text = congress_api.get_bill_text(url)
            logger.info(f"Bill text retrieved: {len(bill_text)} characters")
        except Exception as e:
            logger.error(f"Error getting bill text: {str(e)}\n{traceback.format_exc()}")
            raise Exception(f"Failed to get bill text: {str(e)}")
        
        # 3. Process bill text
        logger.info("Processing bill text...")
        try:
            processed = text_processor.process_bill(bill_text)
            logger.info(f"Processed bill into {len(processed['chunks'])} chunks and {len(processed['sections'])} sections")
            global current_processed_sections
            current_processed_sections = processed.get('sections', [])
            logger.info(f"Stored {len(current_processed_sections)} processed sections globally.")
        except Exception as e:
            logger.error(f"Error processing bill text: {str(e)}\n{traceback.format_exc()}")
            raise Exception(f"Failed to process bill text: {str(e)}")
        
        # 4. Store in vector database
        logger.info("Storing bill chunks in vector database...")
        global current_bill_id, current_bill_metadata
        current_bill_id = f"{metadata.congress}-{metadata.bill_type}-{metadata.number}"
        current_bill_metadata = metadata.__dict__
        # Store bill-level metadata in QASystem
        qa_system.store_bill_metadata(current_bill_id, current_bill_metadata)
        logger.info(f"Stored bill-level metadata for {current_bill_id} in QASystem.")
        
        try:
            qa_system.store_bill_chunks(
                bill_id=current_bill_id,
                chunks=processed['chunks'],
                metadata=current_bill_metadata
            )
            logger.info("Bill chunks stored successfully")
        except Exception as e:
            logger.error(f"Error storing bill chunks: {str(e)}\n{traceback.format_exc()}")
            raise Exception(f"Failed to store bill chunks: {str(e)}")
        
        # 5. Generate executive summary
        logger.info("Generating executive summary...")
        try:
            summary = ai_analyzer.generate_executive_summary(bill_text, metadata.__dict__)
            logger.info("Executive summary generated")
        except Exception as e:
            logger.error(f"Error generating executive summary: {str(e)}\n{traceback.format_exc()}")
            raise Exception(f"Failed to generate executive summary: {str(e)}")
        
        # 7. Score political ideology
        logger.info("Scoring political ideology...")
        try:
            ideology = ai_analyzer.score_political_ideology(bill_text, metadata.__dict__)
            logger.info("Political ideology scored")
        except Exception as e:
            logger.error(f"Error scoring political ideology: {str(e)}\n{traceback.format_exc()}")
            # Don't fail the whole analysis for ideology scoring issues
            ideology_score = 0.0
            ideology_confidence = 50.0
            
            # Calculate bill size category
            word_count = len(bill_text.split())
            if word_count < 500:
                size_category = "Small"
            elif word_count < 1100:
                size_category = "Medium-Small"
            elif word_count < 5000:
                size_category = "Medium"
            elif word_count < 25000:
                size_category = "Large"
            else:
                size_category = "Extra Large"
                
            return (summary, ideology_score, ideology_confidence, size_category, word_count)
        
        # 8. Calculate bill size category based on word count
        word_count = len(bill_text.split())
        logger.info(f"Bill word count: {word_count}")
        
        if word_count < 500:
            size_category = "Small"
        elif word_count < 1100:
            size_category = "Medium-Small"
        elif word_count < 5000:
            size_category = "Medium"
        elif word_count < 25000:
            size_category = "Large"
        else:
            size_category = "Extra Large"
            
        logger.info(f"Bill size category: {size_category}")
        
        # 9. Return results
        logger.info(f"Analysis completed successfully for bill: {current_bill_id}")
        return (summary, ideology.score, ideology.confidence, size_category, word_count)
        
    except Exception as e:
        import sys
        logger.error(f"Error in bill analysis: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error args: {e.args}")
        logger.error(f"Exception info: {sys.exc_info()}")
        logger.error("Full traceback:")
        import traceback
        tb = traceback.format_exc()
        logger.error(tb)
        
        error_msg = (
            f"Error: {str(e)}\n"
            f"Error type: {type(e).__name__}\n"
            "\nPlease check app.log for more details."
        )
        # Return values that match the UI component structure in error case
        return (
            error_msg,  # summary_output (Markdown)
            [],         # sections_output (JSON)
            0,          # score_output (Number)
            0           # confidence_output (Number)
        )

def handle_question(question: str, chat_history: List[Tuple[str, str]]) -> Tuple[str, List[Tuple[str, str]]]:
    """Handle user questions about the current bill"""
    if not current_bill_id:
        response = "Please analyze a bill first before asking questions."
        chat_history.append((question, response))
        return "", chat_history
    
    try:
        logger.info(f"Handling question: {question}")
        answer = qa_system.query_bill(question, current_bill_id)
        chat_history.append((question, answer))
        return "", chat_history
    except Exception as e:
        logger.error(f"Error in question handling: {str(e)}")
        logger.error(traceback.format_exc())
        error_response = f"Sorry, I encountered an error: {str(e)}\n\nPlease check app.log for more details."
        chat_history.append((question, error_response))
        return "", chat_history

def create_interface():
    """Create Gradio interface"""
    # Log that we're entering the function
    logger.info("=== Entering create_interface() ===")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"URL input exists: {'url_input' in locals()}")
    logger.info(f"Analyze button exists: {'analyze_btn' in locals()}")
    
    logger.info("Creating Gradio interface...")
    try:
        with gr.Blocks(title="Congressional Bill Analyzer") as app:
            gr.Markdown("# Congressional Bill Analyzer")
            
            # Bill Input Section
            with gr.Row():
                url_input = gr.Textbox(
                    label="Congress.gov Bill URL",
                    placeholder="https://www.congress.gov/bill/118th-congress/house-bill/1234",
                    value="https://www.congress.gov/bill/118th-congress/senate-bill/4487"
                )
                analyze_btn = gr.Button("Analyze Bill", variant="primary")
            
            # Analysis Results Section
            with gr.Row():
                with gr.Column(scale=2):
                    summary_output = gr.Markdown(label="Executive Summary")
                    sections_output = gr.JSON(label="Section-by-Section Analysis")
                    generate_sections_btn = gr.Button("Generate Section-by-Section Analysis")
                
                with gr.Column(scale=1):
                    score_output = gr.Number(label="Political Ideology Score", precision=1)
                    confidence_output = gr.Number(label="Confidence Level", precision=1)
                    size_label = gr.Textbox(label="Bill Size Category", 
                                 info="Based on word count: Small (<500), Medium-Small (500-1,100), Medium (1,100-5,000), Large (5,000-25,000), Extra Large (25,000+)")
                    word_count_output = gr.Number(label="Word Count")
            # Interactive Q&A Section
            gr.Markdown("## Ask Questions About This Bill")
            
            with gr.Row():
                with gr.Column(scale=4):
                    question_input = gr.Textbox(
                        label="Your Question",
                        placeholder="e.g., How will this bill affect healthcare costs?",
                        lines=2
                    )
                with gr.Column(scale=1):
                    ask_btn = gr.Button("Ask Question", variant="secondary")
            
            # Q&A History
            qa_chatbot = gr.Chatbot(
                label="Questions & Answers",
                height=400,
                show_label=True
            )
            
            # Suggested Questions
            with gr.Row():
                gr.Markdown("### Suggested Questions:")
                with gr.Column():
                    suggestion_btns = [
                        gr.Button("What are the key provisions?", size="sm"),
                        gr.Button("What's the estimated cost?", size="sm"),
                        gr.Button("When does this take effect?", size="sm"),
                        gr.Button("Who does this impact most?", size="sm")
                    ]
            
            # Set up event handlers
            @validate_handler_output
            def on_analyze_click(url) -> Tuple[str, List[Dict], float, float, str, int]: # Returns 6 items for UI
                print(f"DEBUG: on_analyze_click called with URL: {url}")
                logger.info(f"Analyze button clicked with URL: {url}")
                try:
                    # analyze_bill now returns 5 items: summary, score, confidence, bill_size_info, word_count_int
                    summary, score, confidence, bill_size_info, word_count_int = analyze_bill(url)
                    logger.info(f"Successfully analyzed bill (core analysis): {url}")
                    # Return 6 items for the UI: summary, empty list for sections_output, then the rest
                    return summary, [], score, confidence, bill_size_info, word_count_int
                except Exception as e:
                    logger.error(f"Error in on_analyze_click during call to analyze_bill for URL {url}: {str(e)}")
                    logger.error(traceback.format_exc())
                    error_summary = f"# Analysis Error\nAn error occurred while analyzing the bill: {str(e)}"
                    # Return 6 items with error placeholders
                    return error_summary, [], 0.0, 0.0, "Error", 0
            
            @validate_handler_output
            def on_generate_sections_click():
                logger.info("Generate Section Analysis button clicked.")
                global current_processed_sections, current_bill_id # Ensure current_bill_id is accessible
                if not current_bill_id: # Check if a bill has been analyzed
                    logger.warning("Attempted to generate sections before analyzing a bill.")
                    return [{'error': "Please analyze a bill first before generating section analysis."}]
                if not current_processed_sections:
                    logger.warning("No processed sections available to analyze.")
                    return [{'error': "No sections were found in the bill text to analyze."}]
                try:
                    section_analysis = ai_analyzer.generate_section_breakdown(current_processed_sections)
                    logger.info("Section-by-section analysis generated successfully.")
                    return section_analysis
                except Exception as e:
                    logger.error(f"Error generating section breakdown: {str(e)}")
                    logger.error(traceback.format_exc())
                    return [{'error': f"An error occurred during section analysis: {str(e)}"}]
            
            @validate_handler_output
            def on_question_click(question, chat_history) -> Tuple[str, List[Tuple[str, str]]]:
                logger.info(f"Question button clicked with: {question}")
                if not current_bill_id:
                    logger.warning("Ask button clicked before a bill was analyzed.")
                    chat_history.append((question, "Please analyze a bill first before asking questions."))
                    return "", chat_history
                try:
                    answer = qa_system.query_bill(question, current_bill_id)
                    chat_history.append((question, answer))
                    return "", chat_history
                except Exception as e:
                    logger.error(f"Error in on_question_click: {str(e)}")
                    logger.error(traceback.format_exc())
                    error_msg = f"Sorry, I encountered an error answering your question: {str(e)}"
                    chat_history.append((question, error_msg))
                    return "", chat_history

            @validate_handler_output
            def on_suggestion_click(suggestion_text, chat_history) -> Tuple[str, List[Tuple[str, str]]]:
                logger.info(f"Suggestion button clicked with text: {suggestion_text}")
                # Populate the question input with the suggestion
                # Then, call on_question_click logic
                return on_question_click(suggestion_text, chat_history)

            # Log before setting up event handlers
            logger.info("=== Setting up event handlers ===")

            # Analyze Bill button
            try:
                analyze_btn.click(
                    fn=on_analyze_click,
                    inputs=url_input,
                    outputs=[summary_output, sections_output, score_output, confidence_output, size_label, word_count_output]
                )
                logger.info("Successfully registered analyze_btn event handler.")
            except Exception as e:
                logger.error(f"Error registering analyze_btn event: {str(e)}\n{traceback.format_exc()}")

            # Generate Section Analysis button
            try:
                generate_sections_btn.click(
                    fn=on_generate_sections_click,
                    inputs=None, # Uses global current_processed_sections
                    outputs=sections_output
                )
                logger.info("Successfully registered generate_sections_btn event handler.")
            except Exception as e:
                logger.error(f"Error registering generate_sections_btn event: {str(e)}\n{traceback.format_exc()}")

            # Ask Question button
            try:
                ask_btn.click(
                    fn=on_question_click,
                    inputs=[question_input, qa_chatbot],
                    outputs=[question_input, qa_chatbot]
                )
                logger.info("Successfully registered ask_btn event handler.")
            except Exception as e:
                logger.error(f"Error registering ask_btn event: {str(e)}\n{traceback.format_exc()}")

            # Suggestion buttons
            logger.info("Setting up suggestion button handlers.")
            for btn in suggestion_btns:
                try:
                    # When a suggestion button is clicked, its value (the question text) is passed to on_suggestion_click
                    logger.info(f"Setting up handler for suggestion button: {btn}")
                    # Use the validated handler
                    btn.click(
                        fn=on_suggestion_click,
                        inputs=[btn, qa_chatbot],  # Pass the button and chat history
                        outputs=[question_input, qa_chatbot]
                    )
                    logger.info(f"Successfully registered suggestion button event handler for {btn}")
                except Exception as e:
                    logger.error(f"Error registering suggestion button event: {str(e)}")
                    logger.error(traceback.format_exc())
            
            return app
            
    except Exception as e:
        logger.error(f"Error creating interface: {str(e)}")
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    logger.info("Starting Congressional Bill Analyzer...")
    app = create_interface()
    app.launch()
