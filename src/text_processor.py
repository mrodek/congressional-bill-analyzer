import re
from typing import List, Dict
from sentence_transformers import SentenceTransformer
import numpy as np

class TextProcessor:
    def __init__(self):
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

    def clean_bill_text(self, raw_text: str) -> str:
        """Clean bill text by removing formatting artifacts while preserving structure"""
        # Remove multiple newlines
        text = re.sub(r'\n\s*\n', '\n\n', raw_text)
        
        # Remove page headers/footers
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
        
        # Remove section markers that aren't part of content
        text = re.sub(r'\n\s*Section\s+\d+\.\s*\n', '\n', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def extract_sections(self, text: str) -> List[Dict[str, str]]:
        """Parse bill into logical sections"""
        # Split by section headers (Section 1., (a), (b), etc.)
        sections = []
        current_section = {'header': '', 'content': ''}
        
        # Split by major section headers
        parts = re.split(r'(Section\s+\d+\.|\(\w\)\s+)', text)
        
        for part in parts:
            if re.match(r'Section\s+\d+\.|\(\w\)\s+', part):
                if current_section['content'].strip():
                    sections.append(current_section)
                current_section = {'header': part.strip(), 'content': ''}
            else:
                current_section['content'] += part
        
        if current_section['content'].strip():
            sections.append(current_section)
        
        return sections

    def chunk_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """Split text into overlapping chunks for vectorization"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size):
            # Take chunk_size words, but overlap with previous chunk
            end = min(i + chunk_size, len(words))
            chunk = ' '.join(words[i:end])
            chunks.append(chunk)
        
        return chunks

    def vectorize_text(self, text: str) -> np.ndarray:
        """Convert text to vector embedding"""
        return self.embedder.encode(text)

    def process_bill(self, raw_text: str) -> Dict[str, any]:
        """Process bill text through all stages"""
        clean_text = self.clean_bill_text(raw_text)
        sections = self.extract_sections(clean_text)
        chunks = self.chunk_text(clean_text)
        
        return {
            'clean_text': clean_text,
            'sections': sections,
            'chunks': chunks,
            'embeddings': [self.vectorize_text(chunk) for chunk in chunks]
        }
