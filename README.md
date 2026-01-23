# ODPC-RAG

A Retrieval-Augmented Generation (RAG) chatbot for the Office of the Data Protection Commissioner (ODPC) Kenya. This system crawls web data, indexes documents into a vector store, and provides both CLI and API interfaces for querying data protection information.

## Requirements

- Python 3.10+
- Virtual environment tool (venv, conda, etc.)
- Internet access for crawling and API calls

## Installation

```bash
# Clone the repository
git clone https://github.com/peter-kiilu/ODPC-RAG.git
cd ODPC-RAG

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root with your API keys:

```env
GROQ_API_KEY=your_groq_api_key_here
# Add other environment variables as needed
```

## Usage

### 1. Crawl Web Data

Download and collect web content:

```bash
# Remove existing state for fresh crawl (optional)
rm crawler_state.json

# Start crawler
python -m crawler.crawler
```

### 2. Index Documents

Build the vector database from crawled content:

```bash
python -m rag_bot.main index

# Or clear existing index and re-index
python -m rag_bot.main index --clear
```

### 3. Chat Interface (CLI)

Interact with the chatbot via command line:

```bash
python -m rag_bot.main chat
```

Available commands:

- Type your question to get answers
- `clear` - Reset conversation history
- `quit` or `exit` - Close the chat

### 4. API Server (Optional)

Expose the chatbot via HTTP API:

```bash
uvicorn rag_bot.api:app --reload --host 0.0.0.0 --port 8000
```

**API Endpoints:**

- `GET /health` - Check system status
- `POST /chat` - Send message and get response
- `POST /clear` - Clear conversation history

**Example API request:**

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What are data subject rights in Kenya?"}'
```

## Project Structure

```
ODPC-RAG/
├── crawler/              # Web crawling module
│   ├── __init__.py
│   ├── config.py
│   ├── crawler.py
│   └── utils.py
├── rag_bot/              # RAG chatbot implementation
│   ├── __init__.py
│   ├── api.py            # FastAPI server
│   ├── chat.py           # Chat logic
│   ├── chunker.py        # Text chunking
│   ├── config.py         # Configuration
│   ├── document_loader.py # Document loading
│   ├── embeddings.py     # Embedding generation (GPU-enabled)
│   ├── main.py           # CLI entry point
│   ├── prompts.py        # Prompt templates
│   ├── retriever.py      # Document retrieval
│   └── vector_store.py   # ChromaDB vector database
├── frontend/             # React frontend (optional)
├── data/                 # Crawled documents storage
├── venv/                 # Virtual environment
├── .env                  # Environment variables
├── .gitignore
├── requirements.txt      # Python dependencies
```

## Docker Deployment

Run the entire application using Docker Compose:

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+

### Quick Start

```bash
# 1. Copy environment template and add your API keys
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# 2. Build and start containers
docker-compose up -d --build

# 3. Check status
docker-compose ps

# 4. View logs
docker-compose logs -f
```

### Access Points

| Service      | URL                          | Description    |
| ------------ | ---------------------------- | -------------- |
| Frontend     | http://localhost:3000        | Chat interface |
| Backend API  | http://localhost:8000        | REST API       |
| Health Check | http://localhost:8000/health | System status  |

### Docker Commands

```bash
# Stop containers
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# View backend logs only
docker-compose logs -f backend

# Enter backend container
docker-compose exec backend bash

# Remove all containers and images
docker-compose down --rmi all -v
```

### Data Persistence

- **Vector Database**: Persisted in `./rag_bot/chroma_db`
- **Documents**: Mounted read-only from `./data`

---

## Troubleshooting

**Module not found errors:**

- Ensure virtualenv is activated
- Run commands from project root

**Crawler issues:**

- Check network connectivity
- Delete `crawler_state.json` for fresh start

**Indexing failures:**

- Verify API keys in `.env`
- Check internet connectivity

**CORS errors (API):**

- Update `origins` list in `rag_bot/api.py`
- For Cloud Workstations, add `credentials: 'include'` in frontend fetch requests

## Features

- 🔍 **RAG-powered Q&A** - Answers based on indexed ODPC documents
- 🌐 **Multi-language support** - English, Swahili, and Sheng
- 💬 **Conversation history** - Maintains context across questions
- 🛡️ **Topic boundaries** - Focused on data protection topics only
- 🚀 **GPU acceleration** - Automatic GPU detection for embeddings
- 📊 **Source citations** - Tracks and displays information sources
