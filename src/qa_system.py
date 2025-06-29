import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from typing import List, Dict, Tuple
from openai import OpenAI

class QASystem:
    def __init__(self, api_key: str, db_path: str):
        self.api_key = api_key
        self.openai_client = OpenAI(api_key=api_key)
        self.db_path = db_path
        self.chroma_client = chromadb.Client(Settings(persist_directory=db_path))
        # Initialize OpenAI embedding function to be used consistently
        self.embedding_function = OpenAIEmbeddingFunction(
            api_key=api_key,
            model_name="text-embedding-ada-002"
        )
        self.collection = self._setup_collection()
        self.bill_metadatas = {}  # To store bill-level metadata

    def _setup_collection(self) -> chromadb.Collection:
        """Initialize or get the ChromaDB collection"""
        try:
            # Try to get existing collection and set its embedding function
            collection = self.chroma_client.get_collection(
                name="congressional_bills",
                embedding_function=self.embedding_function
            )
        except:
            # Create new collection with our embedding function
            collection = self.chroma_client.create_collection(
                name="congressional_bills",
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
        return collection

    def store_bill_chunks(self, bill_id: str, chunks: List[str], metadata: Dict[str, str]) -> None:
        """Store bill chunks in ChromaDB with metadata"""
        chunk_ids = [f"{bill_id}_chunk_{i}" for i in range(len(chunks))]
        
        # Sanitize metadata - ChromaDB doesn't accept empty lists, dicts, or non-primitive types
        sanitized_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                sanitized_metadata[key] = value
            elif isinstance(value, list) and value:  # Non-empty list
                # Convert lists to strings
                sanitized_metadata[key] = ", ".join(str(item) for item in value)
            elif isinstance(value, dict) and value:  # Non-empty dict
                # Convert dicts to strings
                sanitized_metadata[key] = str(value)
            else:
                # Skip empty lists/dicts or convert to appropriate default value
                if isinstance(value, list):
                    sanitized_metadata[key] = ""  # Empty string for empty lists
                elif isinstance(value, dict):
                    sanitized_metadata[key] = "{}"  # String representation of empty dict
                else:
                    sanitized_metadata[key] = str(value)  # Convert other types to string
        
        # Add bill_id to metadata for easier querying
        sanitized_metadata["bill_id"] = bill_id
        
        self.collection.add(
            ids=chunk_ids,
            documents=chunks,
            metadatas=[sanitized_metadata] * len(chunks)
        )

    def get_relevant_context(self, question: str, bill_id: str, k: int = 5) -> List[Dict[str, any]]:
        """Retrieve relevant bill sections for a question"""
        # Use the collection's embedding function directly
        results = self.collection.query(
            query_texts=[question],  # Let ChromaDB handle the embedding
            n_results=k,
            where={"bill_id": bill_id}
        )
        
        return [
            {
                "text": doc,
                "section": meta.get('section', 'Unknown'),
                "relevance_score": score
            }
            for doc, meta, score in zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )
        ]

    def generate_contextualized_response(self, question: str, context: List[Dict[str, any]], metadata: Dict[str, str]) -> str:
        """Generate LLM response with retrieved context"""
        # Limit context to avoid token limits
        if len(context) > 5:
            context = context[:5]  # Use only top 5 most relevant chunks
            
        context_str = "\n\n".join([
            f"Section: {c['section']}\nContent: {c['text']}\nRelevance Score: {c['relevance_score']}"
            for c in context
        ])

        prompt = f"""
        You are an expert congressional bill analyst. Answer the user's question about the bill using the provided context.

        Bill Information:
        - Title: {metadata['title']}
        - Congress: {metadata['congress']}
        - Sponsor: {metadata['sponsor']}
        - Type: {metadata['bill_type']}

        Relevant Bill Sections:
        {context_str}

        User Question: {question}

        Instructions:
        1. Answer based primarily on the provided bill text
        2. If information is not in the bill, clearly state this
        3. Reference specific sections when possible
        4. Explain implications and potential impacts
        5. Use clear, accessible language
        6. If the question involves comparison to current law, note that as context

        Answer:
        """

        response = self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo-16k",  # Using a model with larger context window
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content

    def store_bill_metadata(self, bill_id: str, metadata: dict):
        """Store bill-level metadata."""
        self.bill_metadatas[bill_id] = metadata

    def query_bill(self, question: str, bill_id: str, k: int = 5) -> str:
        """Answer questions about a specific bill using vector search + LLM"""
        context = self.get_relevant_context(question, bill_id, k)
        # Retrieve stored bill-level metadata
        bill_level_metadata = self.bill_metadatas.get(bill_id, {})
        # Ensure default values if keys are missing in stored metadata, to prevent KeyErrors in prompt
        prompt_metadata = {
            'title': bill_level_metadata.get('title', 'N/A'),
            'congress': bill_level_metadata.get('congress', 'N/A'),
            'sponsor': bill_level_metadata.get('sponsor', 'N/A'), # Sponsor is a string (name)
            'bill_type': bill_level_metadata.get('bill_type', 'N/A')
        }
        return self.generate_contextualized_response(question, context, prompt_metadata)
