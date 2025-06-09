import streamlit as st
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import asdict
import plotly.graph_objects as go

# Add src directory to Python path to allow direct imports
SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Now import your project modules
from congress_api import CongressAPI
from text_processor import TextProcessor
from ai_analyzer import AIAnalyzer
from qa_system import QASystem

# Load environment variables from .env file
# Assuming .env is in the parent directory of src (project root)
dotenv_path = SRC_DIR.parent / '.env'
load_dotenv(dotenv_path=dotenv_path)

# Configure basic logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=log_level,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout) # Streamlit apps often log to stdout/stderr
logger = logging.getLogger('StreamlitApp')

# Helper functions for Plotly Gauges
def create_ideology_gauge(score):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Ideology Score", 'font': {'size': 20}},
        gauge = {
            'axis': {'range': [-10, 10], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "darkblue"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [-10, -5], 'color': 'rgba(255, 0, 0, 0.7)'},       # Strong Liberal (Red)
                {'range': [-5, -1], 'color': 'rgba(255, 165, 0, 0.7)'},    # Moderate Liberal (Orange)
                {'range': [-1, 1], 'color': 'rgba(255, 255, 0, 0.7)'},      # Moderate (Yellow)
                {'range': [1, 5], 'color': 'rgba(173, 216, 230, 0.7)'},    # Moderate Conservative (Light Blue)
                {'range': [5, 10], 'color': 'rgba(0, 0, 255, 0.7)'}        # Strong Conservative (Blue)
            ],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': score
            }
        }
    ))
    fig.update_layout(height=250, margin=dict(l=10, r=10, t=50, b=10))
    return fig

def create_confidence_gauge(confidence_score):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = confidence_score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Confidence Score", 'font': {'size': 20}},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkgreen"},
            'bar': {'color': "darkgreen"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 50], 'color': 'rgba(255, 0, 0, 0.6)'},
                {'range': [50, 80], 'color': 'rgba(255, 255, 0, 0.6)'},
                {'range': [80, 100], 'color': 'rgba(0, 128, 0, 0.6)'}
            ],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': confidence_score
            }
        }
    ))
    fig.update_layout(height=250, margin=dict(l=10, r=10, t=50, b=10))
    return fig


# Initialize API clients and processors
# Ensure API keys are loaded correctly by the respective modules
OPENAI_API_KEY = os.getenv("OPENAIAPIKEY")
CONGRESS_API_KEY = os.getenv("CONGRESS_GOV_API_KEY")

if not OPENAI_API_KEY:
    st.error("OpenAI API key (OPENAIAPIKEY) not found in environment variables. Please check your .env file.")
    st.stop()
if not CONGRESS_API_KEY: # CongressAPI reads this from env directly
    st.error("Congress.gov API key (CONGRESS_GOV_API_KEY) not found in environment variables. Please check your .env file.")
    st.stop()

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./data/chromadb") # Default if not in .env
if not os.path.exists(CHROMA_DB_PATH):
    logger.warning(f"ChromaDB path {CHROMA_DB_PATH} does not exist. It will be created by ChromaDB if it's a new database.")

# Initialize components (modules handle their own API key loading from env)
try:
    congress_api_client = CongressAPI()
    text_processor = TextProcessor()
    ai_analyzer = AIAnalyzer(api_key=OPENAI_API_KEY)
    qa_system = QASystem(api_key=OPENAI_API_KEY, db_path=CHROMA_DB_PATH)
    logger.info("Core components initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing core components: {e}", exc_info=True)
    st.error(f"Fatal error initializing application components: {e}. Check logs.")
    st.stop()

# --- Helper Function for Bill Analysis ---
def perform_bill_analysis(url_to_analyze: str):
    try:
        logger.info(f"Starting analysis for URL: {url_to_analyze}")
        bill_metadata_obj = congress_api_client.get_bill_metadata(url_to_analyze) # Renamed to avoid confusion
        
        if not bill_metadata_obj or not bill_metadata_obj.url:
            logger.error("Failed to retrieve bill metadata or bill URL.")
            return {"error": "Failed to retrieve bill metadata. Check URL or API."}

        # Convert BillMetadata object to dictionary for consistent use where dicts are expected
        bill_metadata_dict = asdict(bill_metadata_obj)

        bill_id = f"{bill_metadata_obj.congress}-{bill_metadata_obj.bill_type}-{bill_metadata_obj.number}"
        logger.info(f"Bill ID: {bill_id}")

        full_text = congress_api_client.get_bill_text(bill_metadata_obj.url) # Pass the direct URL
        if not full_text: # Check if text is empty
            logger.error("Failed to retrieve bill text (text is empty).")
            return {"error": "Failed to retrieve bill text (text is empty)."}
        
        processed_bill_data = text_processor.process_bill(full_text)

        # AIAnalyzer expects a dictionary for bill_metadata
        executive_summary = ai_analyzer.generate_executive_summary(full_text, bill_metadata_dict)
        ideology_score_obj = ai_analyzer.score_political_ideology(full_text, bill_metadata_dict)
        ideology_analysis_dict = asdict(ideology_score_obj) # Convert IdeologyAnalysis object to dict
        
        # Reconstruct the summary_analysis dictionary to match expected structure
        summary_analysis = {
            "summary": executive_summary,
            "ideology_analysis": ideology_analysis_dict
        }
        if not summary_analysis:
            logger.error("Failed to generate summary and ideology.")
            return {"error": "AI analysis for summary/ideology failed."}

        word_count = len(full_text.split())
        if word_count < 5000:
            size_category = "Short"
        elif word_count < 20000:
            size_category = "Medium"
        else:
            size_category = "Long"

        analysis_output = {
            "bill_id": bill_id,
            "summary": summary_analysis.get("summary", "N/A"),
            "ideology_score": summary_analysis.get("ideology_analysis", {}).get("score", 0.0),
            "ideology_confidence": summary_analysis.get("ideology_analysis", {}).get("confidence", 0.0),
            "word_count": word_count,
            "size_category": size_category,
            "bill_metadata": bill_metadata_dict, # Store the dictionary version
            "full_text": full_text, 
            "processed_sections": processed_bill_data.get('sections', []),
            "chunks": processed_bill_data.get('chunks', [])
        }
        logger.info(f"Analysis successful for {bill_id}.")
        return analysis_output

    except Exception as e:
        logger.error(f"Error during bill analysis for {url_to_analyze}: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {str(e)}"}

# --- Streamlit App UI --- 
st.set_page_config(page_title="Congressional Bill Analyzer - Streamlit", layout="wide")
st.title("📊 Congressional Bill Analyzer (Streamlit Edition)")
st.markdown("--- ")

# Initialize session state variables if they don't exist
if 'bill_url' not in st.session_state:
    st.session_state.bill_url = "https://www.congress.gov/bill/118th-congress/house-bill/589"
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None # To store dict of summary, score, etc.
if 'processed_sections' not in st.session_state:
    st.session_state.processed_sections = []
if 'section_analysis_json' not in st.session_state:
    st.session_state.section_analysis_json = None
if 'qa_history' not in st.session_state:
    st.session_state.qa_history = [] # List of tuples (question, answer)
if 'current_bill_id_for_qa' not in st.session_state:
    st.session_state.current_bill_id_for_qa = None
if 'fetched_bills' not in st.session_state:
    st.session_state.fetched_bills = []
if 'list_bills_congress' not in st.session_state:
    st.session_state.list_bills_congress = 118 # Default to current or recent congress
if 'list_bills_type' not in st.session_state:
    st.session_state.list_bills_type = "hr"
if 'list_bills_limit' not in st.session_state:
    st.session_state.list_bills_limit = 10
if 'list_bills_sort' not in st.session_state:
    st.session_state.list_bills_sort = "date+desc"

# --- Main App Sections --- 

# Section 1: Bill Analysis Input
st.header("🔎 Bill Analysis")
bill_url_input = st.text_input(
    "Enter Congress.gov Bill URL:", 
    value=st.session_state.bill_url, 
    key="bill_url_input_key"
)

if st.button("Analyze Bill", key="analyze_bill_btn"):
    if bill_url_input:
        st.session_state.bill_url = bill_url_input
        # Clear previous results before new analysis
        st.session_state.analysis_results = None
        st.session_state.processed_sections = []
        st.session_state.section_analysis_json = None
        st.session_state.qa_history = []
        st.session_state.current_bill_id_for_qa = None

        with st.spinner("Analyzing bill... Please wait."):
            logger.info(f"Analyze button clicked for URL: {st.session_state.bill_url}")
            analysis_data = perform_bill_analysis(st.session_state.bill_url)

            if analysis_data and "error" not in analysis_data:
                st.session_state.analysis_results = {
                    "summary": analysis_data.get("summary"),
                    "ideology_score": analysis_data.get("ideology_score"),
                    "ideology_confidence": analysis_data.get("ideology_confidence"),
                    "word_count": analysis_data.get("word_count"),
                    "size_category": analysis_data.get("size_category")
                }
                st.session_state.processed_sections = analysis_data.get("processed_sections", [])
                st.session_state.current_bill_id_for_qa = analysis_data.get("bill_id")
                
                # Setup Q&A context for the newly analyzed bill
                retrieved_bill_id = analysis_data.get("bill_id")
                retrieved_chunks = analysis_data.get("chunks")
                retrieved_metadata = analysis_data.get("bill_metadata")

                if retrieved_bill_id and retrieved_chunks is not None and retrieved_metadata: # Check chunks is not None as empty list is valid
                    try:
                        qa_system.store_bill_chunks(
                            bill_id=retrieved_bill_id,
                            chunks=retrieved_chunks,
                            metadata=retrieved_metadata
                        )
                        logger.info(f"Q&A context setup successful for bill ID: {retrieved_bill_id}")
                        st.success("Bill analysis complete and Q&A system ready!")
                    except Exception as e_qa:
                        logger.error(f"Error setting up Q&A context for {retrieved_bill_id}: {e_qa}", exc_info=True)
                        st.error(f"Analysis complete, but Q&A setup failed: {e_qa}. Check logs for details.")
                else:
                    logger.warning(f"Q&A context not fully set up for bill ID: {retrieved_bill_id} due to missing data. Bill ID: {bool(retrieved_bill_id)}, Chunks: {retrieved_chunks is not None}, Metadata: {bool(retrieved_metadata)}")
                    st.success("Bill analysis complete! (Q&A context not fully set up due to missing data - check logs)")

            elif analysis_data and "error" in analysis_data:
                st.error(f"Analysis failed: {analysis_data['error']}")
                logger.error(f"Analysis failed for {st.session_state.bill_url}: {analysis_data['error']}")
            else:
                st.error("Analysis failed: An unknown error occurred during analysis.")
                logger.error(f"Analysis failed for {st.session_state.bill_url} with no specific error message from perform_bill_analysis.")
    else:
        st.warning("Please enter a bill URL.")

# Display Analysis Results (if available)
if st.session_state.analysis_results:
    st.subheader("📋 Analysis Results")
    res = st.session_state.analysis_results
    # Example display - to be populated by actual analysis
    st.markdown(f"**Executive Summary:**\n{res.get('summary', 'Not available.')}")
    
    col1, col2 = st.columns(2) # Using 2 columns for gauges
    with col1:
        ideology_score_val = res.get('ideology_score', 0.0)
        st.plotly_chart(create_ideology_gauge(ideology_score_val), use_container_width=True)
    with col2:
        confidence_score_val = res.get('ideology_confidence', 0.0)
        st.plotly_chart(create_confidence_gauge(confidence_score_val), use_container_width=True)

    col3, col4 = st.columns(2) # Separate row for word count and size
    col3.metric("Word Count", res.get('word_count', 'N/A'))
    col4.text_input("Bill Size Category", value=res.get('size_category', 'N/A'), disabled=True)
    
    if st.session_state.processed_sections: # Only show if sections were processed
        if st.button("Generate Section-by-Section Analysis", key="generate_sections_btn"):
            if not st.session_state.processed_sections:
                st.warning("No processed sections available. Please analyze a bill first.")
            else:
                with st.spinner("Generating section analysis... Please wait."):
                    try:
                        logger.info(f"Generating section-by-section analysis for {len(st.session_state.processed_sections)} sections.")
                        section_analysis_result = ai_analyzer.generate_section_breakdown(st.session_state.processed_sections)
                        if section_analysis_result:
                            st.session_state.section_analysis_json = section_analysis_result
                            logger.info("Section-by-section analysis generated successfully.")
                            st.success("Section-by-section analysis complete!")
                        else:
                            st.session_state.section_analysis_json = None # Clear previous if any
                            logger.warning("Section-by-section analysis returned no result.")
                            st.warning("Could not generate section-by-section analysis. The AI might not have found sections to analyze or an issue occurred.")
                    except Exception as e_sections:
                        st.session_state.section_analysis_json = None # Clear previous if any
                        logger.error(f"Error generating section-by-section analysis: {e_sections}", exc_info=True)
                        st.error(f"Failed to generate section-by-section analysis: {e_sections}")
    
    if st.session_state.section_analysis_json:
        st.subheader("📄 Section-by-Section Analysis")
        st.json(st.session_state.section_analysis_json)

st.markdown("--- ")

# Section 2: Q&A about the Bill
st.header("❓ Ask Questions About The Bill")
if st.session_state.current_bill_id_for_qa:
    # Display Q&A history
    for i, (q, a) in enumerate(st.session_state.qa_history):
        with st.chat_message("user", avatar="❓"):
            st.markdown(q)
        with st.chat_message("assistant", avatar="💡"):
            st.markdown(a)

    question_input = st.chat_input("Ask your question about the analyzed bill...")
    if question_input:
        # Add user question to history and display it immediately
        st.session_state.qa_history.append((question_input, None)) # Placeholder for answer
        # Display the new question immediately by re-rendering the chat messages
        # Need to redraw the chat messages before the spinner and API call
        # This is a bit of a workaround for Streamlit's execution model with chat_input

        # Display the latest question from user
        with st.chat_message("user", avatar="❓"):
            st.markdown(question_input)
        
        # Now get the answer
        with st.spinner("Thinking..."):
            try:
                logger.info(f"Querying Q&A system for bill '{st.session_state.current_bill_id_for_qa}' with question: {question_input}")
                answer = qa_system.query_bill(question=question_input, bill_id=st.session_state.current_bill_id_for_qa)
                if answer:
                    # Update the last entry in qa_history with the actual answer
                    st.session_state.qa_history[-1] = (question_input, answer)
                    logger.info(f"Received answer: {answer[:100]}...")
                else:
                    st.session_state.qa_history[-1] = (question_input, "Sorry, I couldn't find an answer to that.")
                    logger.warning("Q&A system returned no answer.")
            except Exception as e_qa_query:
                logger.error(f"Error querying Q&A system: {e_qa_query}", exc_info=True)
                answer_error = f"Sorry, an error occurred while trying to get an answer: {str(e_qa_query)}"
                st.session_state.qa_history[-1] = (question_input, answer_error)
        
        st.rerun() # Rerun to display the assistant's response
else:
    st.info("Please analyze a bill first to enable Q&A.")

st.markdown("--- ")

# Section 3: List Bills from API (New Feature)
st.header("📜 List Bills from Congress.gov")
col1, col2 = st.columns(2)
with col1:
    congress_num = st.number_input("Congress Number (e.g., 118):", min_value=93, max_value=200, value=st.session_state.list_bills_congress, key="list_bills_congress_input")
    bill_type_options = ["hr", "s", "hres", "sres", "hjres", "sjres", "hconres", "sconres"]
    bill_type_selected = st.selectbox("Bill Type:", options=bill_type_options, index=bill_type_options.index(st.session_state.list_bills_type), key="list_bills_type_input")
with col2:
    limit_num = st.number_input("Number of bills to fetch (Limit):", min_value=1, max_value=250, value=st.session_state.list_bills_limit, key="list_bills_limit_input") # Max limit for API is 250
    sort_options = {
        "Latest Action (Newest First)": "date+desc",
        "Latest Action (Oldest First)": "date+asc",
        "Bill Number (Descending)": "number+desc",
        "Bill Number (Ascending)": "number+asc"
    }
    sort_display = st.selectbox("Sort by:", options=list(sort_options.keys()), index=list(sort_options.values()).index(st.session_state.list_bills_sort), key="list_bills_sort_input")
    sort_selected = sort_options[sort_display]

if st.button("Fetch Bills", key="fetch_bills_btn"):
    # Update session state from inputs before fetching
    st.session_state.list_bills_congress = congress_num
    st.session_state.list_bills_type = bill_type_selected
    st.session_state.list_bills_limit = limit_num
    st.session_state.list_bills_sort = sort_selected

    with st.spinner(f"Fetching {limit_num} '{bill_type_selected}' bills from {congress_num}th Congress..."):
        try:
            logger.info(f"Fetching bills: Congress={congress_num}, Type={bill_type_selected}, Limit={limit_num}, Sort={sort_selected}")
            bills_data = congress_api_client.get_bill_list(
                congress=congress_num,
                bill_type=bill_type_selected,
                limit=limit_num,
                sort=sort_selected
            )
            if bills_data:
                st.session_state.fetched_bills = bills_data
                logger.info(f"Successfully fetched {len(bills_data)} bills.")
                st.success(f"Successfully fetched {len(bills_data)} bills.")
            else:
                st.session_state.fetched_bills = []
                logger.info("No bills found for the given criteria.")
                st.info("No bills found for the given criteria.")
        except Exception as e_fetch:
            st.session_state.fetched_bills = []
            logger.error(f"Error fetching bill list: {e_fetch}", exc_info=True)
            st.error(f"Failed to fetch bills: {e_fetch}")

if st.session_state.fetched_bills:
    st.subheader(f"Displaying {len(st.session_state.fetched_bills)} Fetched Bills")
    for i, bill in enumerate(st.session_state.fetched_bills):
        bill_title = bill.get('title', 'N/A')
        bill_number_display = bill.get('number', 'N/A')
        bill_congress_display = bill.get('congress', 'N/A')
        bill_type_display = bill.get('type', 'N/A')
        bill_id_display = f"{bill_congress_display}-{bill_type_display}-{bill_number_display}"
        
        latest_action = bill.get('latestAction', {})
        latest_action_date = latest_action.get('actionDate', 'N/A')
        latest_action_text = latest_action.get('text', 'N/A')
        update_date = bill.get('updateDate', 'N/A')
        origin_chamber = bill.get('originChamber', 'N/A')

        with st.expander(f"{i+1}. {bill_title} ({bill_id_display})"):
            st.markdown(f"**Bill ID:** {bill_id_display}")
            st.markdown(f"**Title:** {bill_title}")
            st.markdown(f"**Origin Chamber:** {origin_chamber}")
            st.markdown(f"**Latest Action Date:** {latest_action_date}")
            st.markdown(f"**Latest Action:** {latest_action_text}")
            st.markdown(f"**Last Update from API:** {update_date}")
            # Provide a link to the bill on Congress.gov if possible (requires constructing the URL)
            if bill_congress_display and bill_type_display and bill_number_display:
                bill_url_congress_gov = f"https://www.congress.gov/bill/{bill_congress_display}th-congress/{bill_type_display.lower()}-bill/{bill_number_display}"
                st.markdown(f"[View on Congress.gov]({bill_url_congress_gov})")

st.sidebar.info("Streamlit UI for Congressional Bill Analysis.")

logger.info("Streamlit app setup complete. Waiting for user interaction.")
