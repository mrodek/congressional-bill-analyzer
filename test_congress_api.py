import requests
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv('CONGRESS_GOV_API_KEY')
if not api_key:
    raise ValueError("CONGRESS_GOV_API_KEY environment variable not set")

# Test with a known bill
congress = "118"  # Use 118th Congress (current)
bill_type = "hr"  # House bill
number = "1"      # Bill number 1

# Make API request
url = f"https://api.congress.gov/v3/bill/{congress}/{bill_type}/{number}"
params = {'api_key': api_key}

print(f"Making request to: {url}")
response = requests.get(url, params=params)
response.raise_for_status()

# Print response structure
data = response.json()
print("API Response Structure:")
print(json.dumps(data, indent=2)[:2000])  # Print first 2000 chars to avoid overwhelming output

# Check specific paths that might be causing the error
if "bill" in data:
    print("\nBill data exists")
    bill_data = data["bill"]
    
    # Check sponsors structure
    if "sponsors" in bill_data:
        print("Sponsors data exists")
        sponsors = bill_data["sponsors"]
        print(f"Sponsors type: {type(sponsors)}")
        print(f"Sponsors content: {sponsors}")
        
        # If sponsors is a list, we need to handle it differently
        if isinstance(sponsors, list):
            print("Sponsors is a list, not a dict with 'items' key")
        elif isinstance(sponsors, dict) and "items" in sponsors:
            print("Sponsors is a dict with 'items' key as expected")
    else:
        print("No sponsors data found")
else:
    print("No bill data found")
