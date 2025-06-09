import os
import re
import sys
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test the regex pattern
def test_regex_pattern():
    content = """
    OVERALL SCORE: 5.5
    DETAILED REASONING: This is a test reasoning.
    CONFIDENCE LEVEL: 75
    KEY PHRASES: "phrase one", "phrase two", 'phrase three'
    """
    
    try:
        # Test double quotes pattern
        double_quotes = re.findall(r'"([^"]+)"', content)
        print(f"Double quotes matches: {double_quotes}")
        
        # Test single quotes pattern
        single_quotes = re.findall(r"'([^']+)'", content)
        print(f"Single quotes matches: {single_quotes}")
        
        # Test key phrases section pattern
        phrases_section = re.search(r'KEY PHRASES:\s*(.+?)(?:\n\n|$)', content, re.DOTALL | re.IGNORECASE)
        if phrases_section:
            phrases_text = phrases_section.group(1)
            print(f"Phrases section: {phrases_text}")
            
            # Split by commas, newlines, or bullet points
            split_phrases = [p.strip(' "\'*-') for p in re.split(r'[,\n\*-]', phrases_text) if p.strip()]
            print(f"Split phrases: {split_phrases}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        print(traceback.format_exc())

if __name__ == "__main__":
    test_regex_pattern()
