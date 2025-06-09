from openai import OpenAI
import logging
import re
import textwrap
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class IdeologyAnalysis:
    score: float
    reasoning: str
    confidence: float
    key_phrases: List[str]

IDEOLOGY_PROMPT = """
Analyze this congressional bill and score its political ideology on a scale of -10 to +10:
- -10: Ultra-liberal (maximum government intervention, progressive social policies)
- -5: Liberal (increased government role, social programs)
- 0: Moderate/Bipartisan
- +5: Conservative (limited government, traditional approaches)
- +10: Ultra-conservative (minimal government, strong traditional values)

Consider these factors:
1. Economic policy direction (spending, taxation, regulation)
2. Role of government (expansion vs. limitation)
3. Social policy implications
4. Regulatory approach
5. Fiscal impact

Bill text: {bill_text}

Provide:
1. Overall score (-10 to +10)
2. Detailed reasoning (200 words)
3. Confidence level (0-100%)
4. Key phrases that influenced the score
"""

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)

    def _chunk_text(self, text: str, max_chunk_size: int = 12000) -> List[str]:
        """Split text into chunks of max_chunk_size characters"""
        return textwrap.wrap(text, max_chunk_size, break_long_words=False, replace_whitespace=False)
    
    def generate_executive_summary(self, bill_text: str, metadata: Dict[str, str]) -> str:
        """Generate a high-level summary of the bill"""
        # Truncate bill text if it's too long
        if len(bill_text) > 30000:  # Roughly 7500 tokens
            bill_text = bill_text[:30000] + "\n\n[Bill text truncated due to length...]\n\n"
        
        prompt = f"""
        Write a 200-300 word executive summary of this congressional bill:
        - Title: {metadata['title']}
        - Sponsor: {metadata['sponsor']}
        - Introduced: {metadata['introduced_date']}
        
        Key points to include:
        1. Purpose of the bill
        2. Main provisions and changes
        3. Potential impact on stakeholders
        4. Timeline and implementation
        
        Bill text: {bill_text}
        """
        
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo-16k",  # Using a model with larger context window
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content

    def generate_section_breakdown(self, sections: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Analyze each section individually"""
        analysis = []
        
        # Limit to first 10 sections to avoid rate limits
        sections_to_analyze = sections[:10] if len(sections) > 10 else sections
        
        for section in sections_to_analyze:
            # Truncate very long sections
            content = section['content']
            if len(content) > 12000:  # Roughly 3000 tokens
                content = content[:12000] + "\n\n[Section content truncated due to length...]\n\n"
                
            prompt = f"""
            Analyze this section of a congressional bill:
            
            Section Header: {section['header']}
            Content: {content}
            
            Provide:
            1. Summary of key provisions
            2. Policy implications
            3. Stakeholder impact
            4. Implementation considerations
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo-16k",  # Using a model with larger context window
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300
            )
            


            analysis.append({
                'header': section['header'],
                'analysis': response.choices[0].message.content
            })
        
        # If we limited the sections, add a note
        if len(sections) > 10:
            analysis.append({
                'header': "Note",
                'analysis': f"Analysis limited to first 10 of {len(sections)} sections to avoid rate limits."
            })
            
        return analysis

    def score_political_ideology(self, bill_text: str, metadata: Dict[str, str]) -> IdeologyAnalysis:
        """Generate political ideology score using GPT"""
        # Truncate bill text if it's too long
        if len(bill_text) > 30000:  # Roughly 7500 tokens
            bill_text = bill_text[:30000] + "\n\n[Bill text truncated due to length...]\n\n"
            
        # Enhanced prompt with more structured output format
        prompt = f"""
        You are a political science expert analyzing congressional bills for ideological orientation. Analyze this bill and assign a political ideology score from -10 to +10 based on the detailed criteria below.

        SCORING FRAMEWORK:

        LIBERAL INDICATORS (-10 to -1):
        - Economic Policy: New government spending programs, tax increases on wealthy/corporations, wealth redistribution, universal programs, economic stimulus, job guarantee programs
        - Government Role: Federal agency creation/expansion, new federal oversight, centralized control, national standards, federal mandates on states
        - Social Policy: Civil rights expansions, LGBTQ+ protections, reproductive rights, criminal justice reform, immigration pathways, diversity/equity initiatives
        - Regulation: Environmental protections, financial regulations, consumer safety rules, labor protections, corporate accountability measures
        - Fiscal: Deficit spending for social programs, progressive taxation, social safety net expansion

        CONSERVATIVE INDICATORS (+1 to +10):
        - Economic Policy: Tax cuts (especially business/high earners), spending reductions, privatization, free market solutions, deregulation, elimination of programs
        - Government Role: State/local control, federal agency reduction, private sector solutions, reduced federal oversight, block grants to states
        - Social Policy: Traditional family values, religious freedom protections, law enforcement support, border security, parental rights, merit-based policies
        - Regulation: Regulatory rollbacks, reduced compliance burdens, industry-friendly policies, property rights protections
        - Fiscal: Balanced budgets, debt reduction, spending caps, elimination of agencies/programs

        MODERATE/BIPARTISAN INDICATORS (0):
        - Bipartisan cosponsorship, incremental reforms, maintains status quo, technical/administrative changes, widely supported issues (infrastructure, veterans), procedural bills

        SCORING SCALE:
        -10 to -8: Revolutionary progressive change (major wealth redistribution, massive government expansion)
        -7 to -5: Strongly liberal (significant new programs, major government role expansion)
        -4 to -2: Moderately liberal (modest spending increases, some new regulations)
        -1 to +1: Moderate/Bipartisan (minor changes, broad consensus issues)
        +2 to +4: Moderately conservative (modest deregulation, limited spending cuts)
        +5 to +7: Strongly conservative (major deregulation, significant spending cuts, traditional values emphasis)
        +8 to +10: Revolutionary conservative change (major government reduction, dramatic deregulation)

        ANALYSIS INSTRUCTIONS:
        1. Identify the bill's PRIMARY purpose and main provisions
        2. Categorize each major provision using the indicators above
        3. Weight provisions by their significance and scope
        4. Consider the overall direction and magnitude of change proposed
        5. Assign a score that reflects the NET ideological direction
        6. Be specific about which provisions drove your scoring decision

        Bill Text: {bill_text}

        REQUIRED RESPONSE FORMAT:
        OVERALL SCORE: [single number from -10 to +10, can include decimals like -3.5]
        DETAILED REASONING: [150-200 words explaining your scoring rationale, citing specific bill provisions]
        CONFIDENCE LEVEL: [0-100, where 100 = completely certain]
        KEY PHRASES: ["phrase 1", "phrase 2", "phrase 3"] [exact quotes from bill text that most influenced your score]
        IDEOLOGICAL CATEGORY: [Ultra-Liberal/Liberal/Moderate-Liberal/Moderate/Moderate-Conservative/Conservative/Ultra-Conservative]
        """
        
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo-16k",  # Using a model with larger context window
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        
        logger.info(f"Model Response: {response} \n{response.choices[0].message.content}")

        content = response.choices[0].message.content
        
        try:
            # Try multiple regex patterns to extract the score
            score_match = re.search(r'OVERALL SCORE:\s*([+-]?\d+(?:\.\d+)?)', content, re.IGNORECASE)
            if not score_match:
                score_match = re.search(r'Overall score:\s*([+-]?\d+(?:\.\d+)?)', content, re.IGNORECASE)
            if not score_match:
                score_match = re.search(r'Score:\s*([+-]?\d+(?:\.\d+)?)', content, re.IGNORECASE)
            if not score_match:
                # If all regex patterns fail, default to a moderate score
                score = 0.0
            else:
                score = float(score_match.group(1))
            logger.info(f"Parsed score from model response: {score}")
                
            # Try multiple regex patterns for reasoning
            reasoning_match = re.search(r'DETAILED REASONING:\s*(.+?)(?:\n\n|\nCONFIDENCE|\nKEY PHRASES|$)', content, re.DOTALL | re.IGNORECASE)
            if not reasoning_match:
                reasoning_match = re.search(r'Detailed reasoning:\s*(.+?)(?:\n\n|\nCONFIDENCE|\nKEY PHRASES|$)', content, re.DOTALL | re.IGNORECASE)
            if not reasoning_match:
                reasoning = "No detailed reasoning provided."
            else:
                reasoning = reasoning_match.group(1).strip()
                
            # Try multiple regex patterns for confidence
            confidence_match = re.search(r'CONFIDENCE LEVEL:\s*(\d+(?:\.\d+)?)', content, re.IGNORECASE)
            if not confidence_match:
                confidence_match = re.search(r'Confidence level:\s*(\d+(?:\.\d+)?)', content, re.IGNORECASE)
            if not confidence_match:
                confidence_match = re.search(r'Confidence:\s*(\d+(?:\.\d+)?)', content, re.IGNORECASE)
            if not confidence_match:
                # Default confidence if not found
                confidence = 50.0
            else:
                confidence = float(confidence_match.group(1))
                
            # Extract key phrases - try multiple patterns
            key_phrases = re.findall(r'"([^"]+)"', content)
            if not key_phrases:
                # Try alternative quote styles
                key_phrases =  re.findall(r'([\\^]+)', content)
            if not key_phrases:
                # Look for phrases after KEY PHRASES: label
                phrases_section = re.search(r'KEY PHRASES:\s*(.+?)(?:\n\n|$)', content, re.DOTALL | re.IGNORECASE)
                if phrases_section:
                    # Split by commas, newlines, or bullet points
                    phrases_text = phrases_section.group(1)
                    key_phrases = [p.strip(' "\'-•*') for p in re.split(r'[,\n•\*-]', phrases_text) if p.strip()]
            
            if not key_phrases:
                key_phrases = ["No key phrases identified"]
                
        except Exception as e:
            import logging
            logging.error(f"Error parsing ideology analysis: {str(e)}")
            # Provide default values if parsing fails
            score = 0.0
            reasoning = "Error parsing ideology analysis. The bill's content may be too complex or the analysis format was unexpected."
            confidence = 50.0
            key_phrases = ["Error in analysis"]
        
        ideology_obj = IdeologyAnalysis(
            score=score,
            reasoning=reasoning,
            confidence=confidence,
            key_phrases=key_phrases
        )
        logger.info(f"Parsed score: {score}")
        logger.info(f"Returning IdeologyAnalysis object: {ideology_obj}")
        return ideology_obj
