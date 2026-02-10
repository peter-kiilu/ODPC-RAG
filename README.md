# ODPC Kenya Shield Bot

An intelligent AI chatbot for the [Office of the Data Protection Commissioner (ODPC) Kenya](https://www.odpc.go.ke/), powered by Retrieval-Augmented Generation (RAG). This system automatically crawls the official ODPC website, indexes content, and provides accurate, source-backed answers to queries about Kenyan data protection laws and regulations.

## Overview

ODPC Shield Bot bridges the gap between complex legal documentation and public understanding. By combining web crawling, semantic search, and large language models, it delivers precise answers with verifiable sources, making data protection information accessible to everyone.

### Key Features

- **Automated Knowledge Base**: Continuously scrapes and indexes ODPC website content in clean Markdown format
- **Intelligent Search**: Semantic retrieval using ChromaDB vector database for context-aware responses
- **Conversational Memory**: PostgreSQL-backed session management maintains context across conversations
- **Source Attribution**: Every response includes citations with direct links to source documents
- **Production Ready**: Fully containerized with Docker, optimized for performance and reliability
- **RESTful API**: Built on FastAPI for high-performance, asynchronous request handling

## Technology Stack

| Component | Technology |
|-----------|-----------|
| **LLM** | Llama 3.1 via Groq API |
| **Embeddings** | BAAI/bge-small-en-v1.5 (HuggingFace) |
| **Vector Store** | ChromaDB |
| **Database** | PostgreSQL 15 |
| **Backend** | Python 3.11, FastAPI, SQLAlchemy |
| **Web Scraping** | BeautifulSoup4, Requests |
| **Infrastructure** | Docker, Docker Compose |

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Groq API key ([get one here](https://console.groq.com/))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/peter-kiilu/ODPC-RAG.git
   cd ODPC-RAG
   ```

2. **Configure environment variables**
   
   Create a `.env` file in the project root:
   ```bash
   # Required
   GROQ_API_KEY=gsk_your_actual_api_key_here

   # Database Configuration (optional - defaults provided)
   POSTGRES_USER=user
   POSTGRES_PASSWORD=password
   POSTGRES_DB=odpc_chatdb

   # Crawler Control (optional)
   SKIP_CRAWL=false
   ```

3. **Launch the application**
   ```bash
   docker compose up --build -d
   ```
   
   The API will be available at `http://localhost:8032`

4. **Verify deployment**
   - Health Check: [http://localhost:8032/health](http://localhost:8032/health)
   - Interactive API Documentation: [http://localhost:8032/docs](http://localhost:8032/docs)

## API Reference

### Send a Chat Message

Start or continue a conversation with the bot.

```http
POST /chat
Content-Type: application/json

{
  "message": "What are the rights of a data subject under the DPA?",
  "session_id": "optional-session-uuid"
}
```

**Response:**
```json
{
  "response": "Under the Data Protection Act, data subjects have several rights...",
  "sources": [
    {
      "title": "Rights of Data Subjects",
      "url": "https://www.odpc.go.ke/data-subject-rights"
    }
  ],
  "session_id": "generated-or-provided-uuid"
}
```

### Retrieve Chat History

Get the complete conversation history for a session.

```http
GET /chat/history/{session_id}
```

### Clear Session History

Delete all messages for a specific session.

```http
DELETE /chat/history/{session_id}
```

## Project Structure

```
ODPC-RAG/
├── crawler/                    # Web scraping engine
│   ├── crawler.py             # Main crawler logic
│   └── crawler_state.json     # Crawl progress tracker
├── rag_bot/                   # Core RAG application
│   ├── api.py                 # FastAPI endpoints
│   ├── chat.py                # RAG engine & prompt engineering
│   ├── database.py            # PostgreSQL models & connections
│   ├── db_init.py             # Database initialization
│   ├── vector_store.py        # ChromaDB management
│   └── chroma_db/             # Vector database storage (volume)
├── data/                      # Scraped content storage (volume)
│   ├── markdown/              # Cleaned markdown files
│   └── documents/             # Original HTML documents
├── docker-compose.yml         # Service orchestration
├── Dockerfile                 # Multi-stage optimized build
├── entrypoint.sh             # Container startup script
├── requirements.txt          # Python dependencies
└── .env                      # Environment configuration
```

## Configuration

### Crawler Behavior

The crawler runs automatically on container startup, indexing the ODPC website.

**Skip crawling** (useful for faster restarts with existing data):
```bash
SKIP_CRAWL=true docker compose up -d
```

**Force a fresh crawl** from scratch:
```bash
# Remove the crawl state
rm data/crawler_state.json

# Ensure crawling is enabled
SKIP_CRAWL=false docker compose up --build -d
```

### Database Management

**Connect to the database:**
```bash
docker exec -it odpc-postgres psql -U user -d odpc_chatdb
```

**Inspect tables:**
```sql
\dt                           -- List all tables
SELECT * FROM chat_sessions;  -- View sessions
SELECT * FROM chat_messages;  -- View message history
```

**Complete reset** (removes all data):
```bash
docker compose down -v
docker compose up --build -d
```

## Performance Optimization

The system includes several optimizations for production use:

- **Model Caching**: HuggingFace embeddings cached in persistent volume (saves 30-40s per restart)
- **Multi-stage Docker Build**: Separates build and runtime dependencies for smaller images
- **Connection Pooling**: Efficient database connection management via SQLAlchemy
- **Async Architecture**: Non-blocking I/O for concurrent request handling
- **Health Checks**: Automatic container monitoring and restart policies

## Monitoring & Troubleshooting

### View Logs

**All services:**
```bash
docker compose logs -f
```

**Specific service:**
```bash
docker compose logs -f odpc-rag
docker compose logs -f postgres
```

### Common Issues

**Slow startup on first run:**
- The embedding model (~133MB) downloads on first launch
- Subsequent starts use the cached model (near-instant)

**Crawler fails:**
- Check network connectivity to odpc.go.ke
- Verify crawler state file isn't corrupted: `rm data/crawler_state.json`

**Database connection errors:**
- Ensure PostgreSQL is healthy: `docker compose ps`
- Check credentials in `.env` match those in `docker-compose.yml`

**Out of memory:**
- Increase Docker memory limit in Docker Desktop settings
- Consider using a smaller embedding model

## Development

### Running Tests

```bash
# Inside the container
docker exec -it odpc-rag bash
pytest tests/
```

### Rebuilding After Code Changes

```bash
docker compose down
docker compose up --build -d
```

### Adding New Data Sources

Modify `crawler/crawler.py` to include additional URLs or domains.

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Office of the Data Protection Commissioner Kenya for maintaining comprehensive data protection resources
- The open-source community for the incredible tools that power this project
- Groq for providing fast LLM inference infrastructure

## Support

For issues, questions, or feature requests, please open an issue on GitHub or contact the maintainers.

---