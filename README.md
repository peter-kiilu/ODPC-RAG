# ODPC Kenya RAG Bot

An intelligent AI chatbot for the [Office of the Data Protection Commissioner (ODPC) Kenya](https://www.odpc.go.ke/), powered by Retrieval-Augmented Generation (RAG). It crawls the official website, indexes the content, and provides accurate, sourced answers to user queries about data protection laws and regulations in Kenya.

## Features

- **Automated Crawler**: Scrapes ODPC website content and converts it to clean Markdown.
- **RAG Engine**: Uses `llama-index` and `chromadb` for semantic search and retrieval.
- **Persistent Memory**: Stores chat history and session context in a **PostgreSQL** database.
- **Session Management**: Supports multiple concurrent user sessions with independent history.
- **Source Citations**: Every answer includes links to the source documents used.
- **API First**: Fast, async API built with **FastAPI**.
- **Dockerized**: Fully containerized for easy deployment.

## Tech Stack

- **LLM**: Llama 3 (via Groq API)
- **Embeddings**: BAAI/bge-small-en-v1.5 (HuggingFace)
- **Vector Store**: ChromaDB
- **Database**: PostgreSQL (Chat History)
- **Backend**: Python 3.11, FastAPI, SQLAlchemy
- **Infrastructure**: Docker & Docker Compose

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/peter-kiilu/ODPC-RAG.git
cd ODPC-RAG
```

### 2. Configure Environment

Create a `.env` file in the root directory:

```env
# AI Provider
GROQ_API_KEY=gsk_your_groq_api_key_here

# Database (Default settings work out of the box with Docker)
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=odpc_chatdb

# Optional: Skip crawling on restart (true/false)
SKIP_CRAWL=false
```

### 3. Run with Docker

This command builds the image, starts the database, crawls the website (if not skipped), indexes documents, and launches the API.

```bash
docker compose up --build -d
```

### 4. Verify Deployment

- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## API Usage Examples

### Chat with the Bot

**POST** `/chat`

```json
{
  "message": "What are the rights of a data subject?",
  "session_id": "optional-uuid-here" 
}
```

### Get Chat History

**GET** `/chat/history/{session_id}`

### Clear Session History

**DELETE** `/chat/history/{session_id}`

---

## Development & Troubleshooting

### Re-crawl and Re-index Data

If you need to update the knowledge base with the latest data from the website:

```bash
# Set SKIP_CRAWL=false in .env or pass it inline
SKIP_CRAWL=false docker compose up --build -d
```

### View Logs

```bash
docker compose logs -f odpc-rag
```

### Database Reset

To completely wipe the database and vector store (start fresh):

```bash
docker compose down -v
docker compose up --build -d
```

### Project Structure

```
ODPC-RAG/
├── crawler/            # Web crawler logic (BeautifulSoup + Requests)
├── rag_bot/            # Core RAG application
│   ├── api.py          # FastAPI endpoints
│   ├── chat.py         # RAG logic & prompt engineering
│   ├── database.py     # PostgreSQL connection & models
│   └── vector_store.py # ChromaDB management
├── data/               # Local storage for scraped MD files (volume mounted)
├── docker-compose.yml  # Service orchestration
├── Dockerfile          # Multi-stage build (optimized for size)
└── requirements.txt    # Python dependencies
```

