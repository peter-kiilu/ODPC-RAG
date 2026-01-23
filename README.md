# ODPC-RAG

A Retrieval-Augmented Generation (RAG) chatbot designed for the Office of the Data Protection Commissioner (ODPC) Kenya. This system crawls web data, indexes documents into a vector store, and provides both a CLI and a modern Web Interface for querying data protection information.

## Features

- 🔍 **RAG-powered Q&A**: Answers based on indexed ODPC documents using Groq's Llama 3 models.
- 🌐 **Multi-language Support**: Capable of understanding and responding in English, Swahili, and Sheng.
- 💻 **Dual Interface**:
  - **CLI**: Fast, terminal-based chat.
  - **Web UI**: Modern React-based chat interface.
- 🛡️ **Topic Boundaries**: Strictly focused on data protection topics.
- 🚀 **GPU Acceleration**: Automatic GPU detection for embeddings (defaults to CPU if unavailable).
- 🐳 **Dockerized**: Easy deployment with Docker Compose.

## Prerequisites

- **Docker Engine** & **Docker Compose** (Recommended for easiest setup)
- **Python 3.10+** (For manual backend setup)
- **Node.js 18+** (For manual frontend setup)
- **Groq API Key** (Required for the LLM)

## Quick Start (Docker)

The simplest way to run the application is using Docker. This spins up both the backend API and the frontend web server.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/peter-kiilu/ODPC-RAG.git
    cd ODPC-RAG
    ```

2.  **Configure Environment:**
    Create a `.env` file in the project root:
    ```bash
    cp .env.example .env  # If example exists, otherwise create it manually
    ```
    Add your API key to `.env`:
    ```env
    GROQ_API_KEY=your_groq_api_key_here
    ```

3.  **Start the Application:**
    ```bash
    docker-compose up -d --build
    ```

4.  **Access the App:**
    - **Frontend UI:** Open [http://localhost](http://localhost) in your browser.
    - **Backend API:** Accessible at [http://localhost:8000](http://localhost:8000).
    - **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

## Manual Installation (Local Development)

If you prefer to run services individually for development:

### 1. Backend Setup

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export GROQ_API_KEY=your_key_here  # Or create a .env file
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Important: Update API URL
# Open `services/apiService.ts` and ensure BASE_URL points to your local backend:
# const BASE_URL = 'http://localhost:8000';

# Start development server
npm run dev
```
Access the frontend at `http://localhost:5173` (or the port shown in your terminal).

## Usage Guide

### Data Pipeline (Crawling & Indexing)

Before the bot can answer questions, it needs data.

1.  **Crawl Data:**
    Downloads content from configured URLs.
    ```bash
    # Run from project root with venv activated
    python -m crawler.crawler
    ```

2.  **Index Data:**
    Processes downloaded data into the vector database.
    ```bash
    python -m rag_bot.main index
    
    # To clear existing index and re-index:
    python -m rag_bot.main index --clear
    ```

### Chat Interfaces

-   **CLI Chat:**
    ```bash
    python -m rag_bot.main chat
    ```
    Commands: `clear` (reset history), `quit` (exit).

-   **API Server:**
    ```bash
    uvicorn rag_bot.api:app --reload --host 0.0.0.0 --port 8000
    ```

## Project Structure

```
ODPC-RAG/
├── crawler/              # Web crawling module
│   ├── crawler.py        # Main crawler logic
│   └── ...
├── rag_bot/              # RAG Core & Backend
│   ├── api.py            # FastAPI endpoints
│   ├── main.py           # CLI entry point
│   ├── vector_store.py   # ChromaDB integration
│   ├── chroma_db/        # Vector database storage
│   └── ...
├── frontend/             # React Web Application
│   ├── src/
│   ├── services/         # API integration
│   └── ...
├── data/                 # Data storage
│   ├── documents/        # Raw downloaded files
│   └── markdown/         # Processed markdown
├── docker-compose.yml    # Docker orchestration
├── Dockerfile            # Multi-stage build definition
└── requirements.txt      # Python dependencies
```

## Troubleshooting

-   **Frontend Connection Error:**
    If the frontend says "Failed to get a response", check that:
    1.  The backend is running (`uvicorn` or Docker).
    2.  The `BASE_URL` in `frontend/services/apiService.ts` matches your backend URL.
    3.  You are not facing CORS issues (the backend is configured to allow all origins by default).

-   **Crawler/Indexing Issues:**
    -   Ensure `GROQ_API_KEY` is set for indexing (if using LLM for anything during ingest, though mostly used for chat).
    -   Delete `crawler_state.json` to force a fresh crawl.

-   **Docker Changes:**
    If you modify code, rebuild the containers:
    ```bash
    docker-compose up -d --build
    ```