# Congressional Bill Analyzer

A Python-based web application that analyzes congressional bills from Congress.gov using AI to provide political ideology scoring and comprehensive analysis.

## Features

- Fetches bills directly from Congress.gov
- AI-powered bill analysis and summarization
- Political ideology scoring (-10 to +10)
- Interactive Q&A system using RAG
- Modern web interface with Gradio
- Vector database storage using ChromaDB

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy and configure environment variables:
```bash
cp .env.example .env
```

3. Run the application:
```bash
python src/app.py
```

## Project Structure

```
congressional-bill-analyzer/
├── src/
│   ├── __init__.py
│   ├── bill_scraper.py
│   ├── text_processor.py
│   ├── ai_analyzer.py
│   ├── qa_system.py
│   └── app.py
├── data/
│   └── chromadb/
├── config/
│   ├── settings.py
│   └── prompts.py
├── tests/
│   ├── test_bill_scraper.py
│   ├── test_text_processor.py
│   ├── test_ai_analyzer.py
│   └── test_qa_system.py
├── requirements.txt
├── .env.example
└── README.md
```

## License

MIT License
