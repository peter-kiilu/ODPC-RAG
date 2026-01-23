---

# ODPC-RAG

A Retrieval-Augmented Generation (RAG) chatbot for the Office of the Data Protection Commissioner (ODPC) Kenya.

---

## Requirements

* Docker
* Docker Compose
* Groq API Key

---

## Quick Start (Recommended)

### 1. Clone

```bash
git clone https://github.com/peter-kiilu/ODPC-RAG.git
cd ODPC-RAG
```

---

### 2. Configure env

Create `.env` in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here

# Database Configuration
POSTGRES_USER=user
POSTGRES_PASSWORD=userpassword
POSTGRES_DB=db_name
```

---

### 3. Build image

```bash
docker compose build
```

---

### 4. Crawl + index data (run once or when updating)

```bash
docker compose run --rm odpc-rag
```

---

### 5. Start the API

```bash
docker compose up -d
```

---

## Access

* API: [http://localhost:8000](http://localhost:8000)
* Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
* Health: [http://localhost:8000/health](http://localhost:8000/health)

---

## Update Data

Re-crawl and re-index:

```bash
docker compose run --rm odpc-rag
```

---

## Useful Commands

```bash
docker ps                 # list containers
docker logs -f odpc-rag   # view logs
docker compose down       # stop
docker compose down -v    # stop + delete data
```

---

## Project Structure

```
ODPC-RAG/
├── crawler/
├── rag_bot/
│   └── chroma_db/
├── data/
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Notes

* Docker is the default
* Data persists in volumes
* Rebuild image only if code changes

---

