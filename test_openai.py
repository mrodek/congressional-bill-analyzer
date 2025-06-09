import os
from dotenv import load_dotenv
import openai
import logging
import traceback
import re
from pathlib import Path
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_openai.log')
    ]
)
logger = logging.getLogger('OpenAITest')

# Get the absolute path to the .env file
env_path = Path(os.path.abspath('.env'))
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Looking for .env file at: {env_path}")
logger.info(f".env file exists: {env_path.exists()}")
logger.info(f".env file absolute path: {os.path.abspath('.env')}"),
logger.info(f".env file exists at absolute path: {os.path.exists(os.path.abspath('.env'))}")

# Load environment variables from the specific .env file
load_dotenv(dotenv_path=env_path)
logger.info(f"Loaded environment variables: {dict(os.environ)}")

# Verify the API key is loaded correctly
api_key = os.getenv('OPENAIAPIKEY')
if not api_key:
    logger.error("OPENAI_API_KEY not found in environment variables")
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# Log the API key (redacted)
logger.info(f"API key loaded: {api_key[:4]}...{api_key[-4:]} (length: {len(api_key)})")

# Validate API key format
api_key = os.getenv('OPENAIAPIKEY')
print(f"API key from env: {api_key}")
logger.info(f"API key from env: {api_key}")
if not api_key:
    logger.error("OPENAI_API_KEY not found in environment variables")
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# Check if API key looks valid
#if not re.match(r'^sk-[a-zA-Z0-9]+$', api_key):
#    logger.error(f"API key format appears invalid: {api_key}")
#    logger.error("Valid API keys should start with 'sk-' followed by alphanumeric characters")
#    raise ValueError("Invalid API key format. Please check your API key in .env file")

# Initialize OpenAI client
try:
    client = openai.OpenAI(api_key=api_key)
    logger.info("Successfully initialized OpenAI client")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    raise

# Test function
def test_openai_connection():
    try:
        logger.info("Starting OpenAI connection test...")
        
        # Test completion endpoint
        logger.info("Testing completion endpoint...")
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": "Hello, how are you?"}
                ]
            )
            logger.info(f"Response received: {response.choices[0].message.content}")
            logger.info("Completion endpoint test successful!")
        except Exception as e:
            logger.error(f"Completion endpoint test failed: {str(e)}")
            raise
        
        # Test embeddings endpoint
        logger.info("Testing embeddings endpoint...")
        try:
            response = client.embeddings.create(
                model="text-embedding-ada-002",
                input="Hello world"
            )
            logger.info(f"Embedding length: {len(response.data[0].embedding)}")
            logger.info("Embeddings endpoint test successful!")
        except Exception as e:
            logger.error(f"Embeddings endpoint test failed: {str(e)}")
            raise
        
        logger.info("All OpenAI tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during OpenAI test: {str(e)}")
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    try:
        test_openai_connection()
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        logger.error(traceback.format_exc())
        logger.error("\nPlease check your API key in the .env file. It should be in the format:")
        logger.error("OPENAI_API_KEY=sk-your-key-here")
        logger.error("You can find your API key at: https://platform.openai.com/account/api-keys")
        raise
