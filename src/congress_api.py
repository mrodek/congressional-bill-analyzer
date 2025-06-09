import requests
import os
from typing import Dict, List, Optional, Any
import logging
import traceback
from dataclasses import dataclass
from dotenv import load_dotenv

logger = logging.getLogger('CongressAPI')

@dataclass
class BillMetadata:
    congress: str
    bill_type: str  # "hr" for house bills, "s" for senate bills, etc.
    number: str
    title: str
    sponsor: str
    introduced_date: str
    committees: List[str]
    subjects: List[str]
    url: str

class CongressAPI:
    """
    Client for the Congress.gov API
    Documentation: https://github.com/LibraryOfCongress/api.congress.gov
    """
    
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('CONGRESS_GOV_API_KEY')
        if not self.api_key:
            raise ValueError("CONGRESS_GOV_API_KEY environment variable not set")
        
        self.base_url = "https://api.congress.gov/v3"
        self.session = requests.Session()
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a request to the Congress.gov API"""
        if params is None:
            params = {}
        
        # Always include the API key
        params['api_key'] = self.api_key
        
        url = f"{self.base_url}/{endpoint}"
        logger.info(f"Making API request to: {url}")
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise
    
    def parse_congress_url(self, url: str) -> Dict[str, str]:
        """Parse Congress.gov URL to extract bill identifiers"""
        # Example: https://www.congress.gov/bill/118th-congress/house-bill/1234
        import re
        
        # Extract congress and bill info from URL
        pattern = r"congress\.gov/bill/(\d+)(?:st|nd|rd|th)-congress/([^/]+)/(\d+)"
        match = re.search(pattern, url)
        
        if not match:
            raise ValueError(f"Invalid Congress.gov URL format: {url}")
        
        congress = match.group(1)
        bill_type = match.group(2)
        number = match.group(3)
        
        # Convert web URL bill type to API bill type
        bill_type_map = {
            "house-bill": "hr",
            "senate-bill": "s",
            "house-joint-resolution": "hjres",
            "senate-joint-resolution": "sjres",
            "house-concurrent-resolution": "hconres",
            "senate-concurrent-resolution": "sconres",
            "house-resolution": "hres",
            "senate-resolution": "sres"
        }
        
        api_bill_type = bill_type_map.get(bill_type)
        if not api_bill_type:
            raise ValueError(f"Unknown bill type: {bill_type}")
        
        return {
            "congress": congress,
            "bill_type": api_bill_type,
            "number": number
        }
    
    def get_bill_metadata(self, url: str) -> BillMetadata:
        """Get bill metadata from Congress.gov API using a web URL"""
        try:
            bill_info = self.parse_congress_url(url)
            congress = bill_info["congress"]
            bill_type = bill_info["bill_type"]
            number = bill_info["number"]
            
            endpoint = f"bill/{congress}/{bill_type}/{number}"
            data = self._make_request(endpoint)
            
            bill_data = data.get("bill", {})
            
            # Extract committees - check if it's a direct URL or has data
            committees = []
            if "committees" in bill_data:
                if isinstance(bill_data["committees"], dict) and "url" in bill_data["committees"]:
                    # If it's just a URL reference, we'll need to make another API call
                    # For now, we'll leave it empty to avoid extra API calls
                    pass
                elif isinstance(bill_data["committees"], list):
                    # Direct committee data
                    for committee in bill_data["committees"]:
                        name = committee.get("name", "")
                        if name:
                            committees.append(name)
            
            # Extract subjects - similar structure check
            subjects = []
            if "subjects" in bill_data and isinstance(bill_data["subjects"], dict):
                if "legislativeSubjects" in bill_data["subjects"]:
                    subjects_data = bill_data["subjects"]["legislativeSubjects"]
                    if isinstance(subjects_data, dict) and "items" in subjects_data:
                        for subject in subjects_data["items"]:
                            name = subject.get("name", "")
                            if name:
                                subjects.append(name)
            
            # Extract sponsor - sponsors is a direct list in the API
            sponsor = ""
            if "sponsors" in bill_data and isinstance(bill_data["sponsors"], list) and bill_data["sponsors"]:
                sponsor_data = bill_data["sponsors"][0]  # Get first sponsor
                sponsor = sponsor_data.get("fullName", "")
            
            # Get title - might be in different places depending on API version
            title = ""
            if "title" in bill_data:
                title = bill_data["title"]
            elif "titles" in bill_data and isinstance(bill_data["titles"], list) and bill_data["titles"]:
                for title_item in bill_data["titles"]:
                    if title_item.get("type") == "Official Title as Introduced":
                        title = title_item.get("title", "")
                        break
                if not title and bill_data["titles"]:
                    # Just take the first title if no official title found
                    title = bill_data["titles"][0].get("title", "")
            
            # Create metadata object
            metadata = BillMetadata(
                congress=congress,
                bill_type=bill_type,
                number=number,
                title=title,
                sponsor=sponsor,
                introduced_date=bill_data.get("introducedDate", ""),
                committees=committees,
                subjects=subjects,
                url=url
            )
            
            logger.info(f"Successfully retrieved metadata for bill: {congress}-{bill_type}-{number}")
            return metadata
            
        except Exception as e:
            logger.error(f"Error getting bill metadata from API: {str(e)}")
            raise
    
    def get_bill_text(self, url: str) -> str:
        """Get bill text from Congress.gov API using a web URL"""
        try:
            bill_info = self.parse_congress_url(url)
            congress = bill_info["congress"]
            bill_type = bill_info["bill_type"]
            number = bill_info["number"]
            
            # First, get the available text versions
            endpoint = f"bill/{congress}/{bill_type}/{number}/text"
            data = self._make_request(endpoint)
            
            # Check the structure of the response
            text_versions = []
            if "textVersions" in data:
                if isinstance(data["textVersions"], list):
                    text_versions = data["textVersions"]
                elif isinstance(data["textVersions"], dict) and "items" in data["textVersions"]:
                    text_versions = data["textVersions"]["items"]
                    
            if not text_versions:
                logger.warning(f"No text versions found for bill: {congress}-{bill_type}-{number}")
                return ""
            
            # Get the most recent text version (usually the first one)
            latest_version = text_versions[0]
            
            # Check formats structure
            formats = []
            if "formats" in latest_version:
                if isinstance(latest_version["formats"], list):
                    formats = latest_version["formats"]
                elif isinstance(latest_version["formats"], dict) and "items" in latest_version["formats"]:
                    formats = latest_version["formats"]["items"]
            
            # Look for plain text format
            text_url = None
            for fmt in formats:
                if fmt.get("type") == "Formatted Text" or fmt.get("type") == "PDF" or fmt.get("type") == "HTML":
                    text_url = fmt.get("url")
                    logger.info(f"Found text format: {fmt.get('type')} at URL: {text_url}")
                    break
            
            if not text_url:
                logger.warning(f"No suitable text format found for bill: {congress}-{bill_type}-{number}")
                return ""
            
            # Get the actual text content
            response = self.session.get(text_url)
            response.raise_for_status()
            
            # The response is HTML, extract the text content
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for elem in soup(['script', 'style']):
                elem.decompose()
            
            # Get text while preserving structure
            text = soup.get_text(separator='\n', strip=True)
            logger.info(f"Successfully retrieved text for bill: {congress}-{bill_type}-{number} ({len(text)} characters)")
            
            return text
            
        except Exception as e:
            logger.error(f"Error getting bill text from API: {str(e)}")
            logger.error(traceback.format_exc()) # Added traceback for more detail
            raise

    def get_bill_list(self, congress: Optional[int] = None, bill_type: Optional[str] = None, limit: int = 20, offset: int = 0, sort: str = "updateDate+desc", from_date_time: Optional[str] = None, to_date_time: Optional[str] = None) -> List[Dict]:
        """
        Get a list of bills from Congress.gov API.

        Args:
            congress: The congress number (e.g., 118).
            bill_type: The type of bill (e.g., "hr", "s").
            limit: Number of records to return. Max is 250.
            offset: Number of records to skip.
            sort: Sort order (e.g., "updateDate+desc", "number+asc").
            from_date_time: Filter for bills updated from this ISO 8601 datetime.
            to_date_time: Filter for bills updated up to this ISO 8601 datetime.

        Returns:
            A list of bill dictionaries.
        """
        endpoint = "bill"
        params = {
            "limit": limit,
            "offset": offset,
            "sort": sort,
            "format": "json" # Ensure we get JSON response
        }
        if congress:
            params["congress"] = congress
        if bill_type:
            params["billType"] = bill_type # API uses 'billType'
        if from_date_time:
            params["fromDateTime"] = from_date_time
        if to_date_time:
            params["toDateTime"] = to_date_time
        
        logger.info(f"Fetching bill list with params: {params}")
        try:
            data = self._make_request(endpoint, params=params)
            bills = data.get("bills", [])
            # API might return a dict with 'count', 'next', 'items' etc. for paginated bill lists
            # or just a list of bills directly if the endpoint behaves differently or for specific filters.
            if not isinstance(bills, list):
                logger.warning(f"'bills' field is not a list, actual type: {type(bills)}. Attempting to find items in response. Full data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
                    bills = data["items"]
                elif isinstance(data, dict) and isinstance(data.get("bills"), dict) and "items" in data["bills"] and isinstance(data["bills"]["items"], list):
                    # Sometimes 'bills' itself is an object containing 'items'
                    bills = data["bills"]["items"]
                else:
                    logger.warning("Could not reliably extract a list of bills from the response.")
                    bills = [] # Default to empty list if extraction fails
            
            logger.info(f"Successfully retrieved {len(bills)} bills. Offset: {offset}, Limit: {limit}")
            return bills
        except Exception as e:
            logger.error(f"Error getting bill list from API: {str(e)}")
            logger.error(traceback.format_exc())
            raise

if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()

    # Configure basic logging to see output
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Get API key from environment
    api_key = os.getenv("CONGRESS_GOV_API_KEY") # Changed to match .env file
    if not api_key:
        # Use the module-level logger if available, otherwise print
        if 'logger' in globals():
            logger.error("CONGRESS_GOV_API_KEY not found in environment variables.")
        else:
            print("ERROR: CONGRESS_GOV_API_KEY not found in environment variables.")
        exit()

    congress_api = CongressAPI() # API key is read from env var in _make_request
    module_logger = logging.getLogger('CongressAPI_Test') # Use a distinct logger for test script messages

    module_logger.info("Testing get_bill_list()...")
    try:
        # Test with default parameters (latest 5 bills)
        recent_bills = congress_api.get_bill_list(limit=5)
        module_logger.info(f"Retrieved {len(recent_bills)} recent bills.")
        if recent_bills:
            module_logger.info("First few recent bills:")
            for i, bill in enumerate(recent_bills[:3]): # Print details of first 3
                title = bill.get('title', 'N/A')
                bill_id = f"{bill.get('congress', 'N/A')}-{bill.get('type', 'N/A')}-{bill.get('number', 'N/A')}"
                last_action_date = bill.get('latestAction', {}).get('actionDate', 'N/A')
                module_logger.info(f"  {i+1}. ID: {bill_id}, Title: {title}, Last Action: {last_action_date}")
        else:
            module_logger.info("No recent bills found or an issue occurred.")

        # Test with specific parameters (e.g., 118th Congress, HR bills, limit 2, offset to get different ones)
        module_logger.info("\nTesting get_bill_list() with specific parameters (118th Congress, HR, limit 2, offset 10, sort by number)...")
        hr_bills = congress_api.get_bill_list(congress=118, bill_type="hr", limit=2, offset=10, sort="number+asc")
        module_logger.info(f"Retrieved {len(hr_bills)} HR bills from 118th Congress (offset 10).")
        if hr_bills:
            module_logger.info("Details of retrieved HR bills:")
            for i, bill in enumerate(hr_bills):
                title = bill.get('title', 'N/A')
                bill_id = f"{bill.get('congress', 'N/A')}-{bill.get('type', 'N/A')}-{bill.get('number', 'N/A')}"
                module_logger.info(f"  {i+1}. ID: {bill_id}, Title: {title}")
        else:
            module_logger.info("No HR bills found for the specified criteria or an issue occurred.")
            
    except Exception as e:
        module_logger.error(f"An error occurred during testing: {str(e)}")
        module_logger.error(traceback.format_exc())
