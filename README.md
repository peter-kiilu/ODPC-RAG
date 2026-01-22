# ODPC-RAG

ODPC-RAG is a small Retrieval-Augmented Generation (RAG) demo that:
- Crawls web data,
- Chunks and indexes documents into a vector store,
- Provides a CLI chatbot backed by the vector index,
- Optionally exposes an HTTP API for the chatbot.

This README explains the typical local workflow: crawl → index → chat → (optional) run the API.

## Requirements

- Python 3.10+ (adjust if your project requires a different version)
- Git (to clone the repo)
- A virtual environment tool (venv, pyenv, conda, etc.)
- Internet access for crawling and any API calls (e.g., embeddings or LLM providers), if used

You will likely need credentials for your embedding/LLM provider (for example `OPENAI_API_KEY`) if the project uses external APIs. Set those as environment variables before running the index/chat steps.

## Install

1. Clone the repository:
   git clone https://github.com/peter-kiilu/ODPC-RAG.git
   cd ODPC-RAG

2. Create and activate a virtual environment:
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell/Cmd)

3. Install dependencies:
   pip install -r requirements.txt

If there is no `requirements.txt`, install dependencies documented in the repository (e.g., `uvicorn`, `fastapi`, `langchain`, `faiss` / `chromadb` / `weaviate-client`, `openai`, etc.) according to how this project is implemented.

## Typical workflow

All commands below assume your current working directory is the repository root (the project root — the folder that contains the `odcp_rag` package/module). The project’s code assumes a fresh crawler run when there is no `crawler_state.json` in the root (or the crawler working directory). If you want a full re-crawl, remove `crawler_state.json` before starting.

1. Start the crawler (download web data)
   - Ensure there is no `crawler_state.json` in the root (delete or move it if present).
   - Run:
     python -m crawler.crawler
   - This module downloads/collects web content and saves documents to the project data folder (refer to the project code for exact paths).

2. Index the documents (chunk + build the vector DB)
   - After crawling completes, create the vector index:
     python -m rag_bot.main index
   - This step reads the downloaded documents, splits/chunks them, computes embeddings, and saves the vector database to disk (or to the configured vector store).

3. Interact with the CLI chatbot
   - Start the CLI chat interface:
     python -m rag_bot.main chat
   - The CLI will prompt you for queries and respond using the RAG pipeline.

4. (Optional) Expose an HTTP API
   - Run the FastAPI (uvicorn) server to expose the chatbot via an API:
     uvicorn rag_bot.api:app --reload
   - By default uvicorn listens on `http://127.0.0.1:8000`. Check the `rag_bot.api` module for route details (endpoints, request/response formats, auth, etc.).

## Notes about crawler_state.json

- Purpose: `crawler_state.json` tracks crawl progress/state between runs.
- If you want to re-run crawling from scratch (re-download everything), remove this file before starting `python -m crawler.crawler`.
- If you want to resume a previous crawl, leave the file in place.

## Configuration and environment variables

This repository may use environment variables or configuration files for:
- Embedding/LLM provider keys (e.g. `OPENAI_API_KEY`)
- Vector DB backend or file paths
- Crawler options (start URLs, domains to include/exclude, rate limits)
- API host/port and authentication settings

Check the modules `crawler`, `rag_bot/main.py`, and `rag_bot/api.py` for exact configuration keys and defaults. Create a `.env` file or export the vars in your shell before running (for example):
export OPENAI_API_KEY="sk-..."

If the project uses a `.env` loader (like python-dotenv), you can place variables in `.env` at the repo root.

## Troubleshooting

- "No module named '...'":
  - Ensure you are running commands from the project root and the virtualenv is activated.
  - Confirm package structure; you may need `pip install -e .` if the project is a package.

- Crawler stuck or incomplete:
  - Check logs printed by the crawler for network errors, rate limiting, or blocked requests.
  - Ensure `crawler_state.json` is not corrupted. If it is and you want a fresh crawl, delete it.

- Indexing errors (embedding failures):
  - Verify API keys and network connectivity.
  - Confirm correct versions of embedding/LLM libraries are installed.

- Vector DB path/questions:
  - Check `rag_bot` code to see where the vector store is saved. If needed, pass an explicit path via environment variable or config.

## Development tips

- Use `--reload` (uvicorn) for API development to auto-reload on code changes.
- Use logging or print statements in `crawler.crawler` if you need more visibility into crawling progress.
- Consider running the crawler on a remote machine or VM for large crawls.

## Contributing

If you plan to contribute:
- Follow the repository's contributing guidelines (if present).
- Add tests for new behaviors and keep changes small and focused.
- Open issues with reproducible steps and logs.

## License

Check the repository root for a LICENSE file. If none exists, ask the project owner which license applies before redistributing.

---

If you want, I can:
- Generate a ready-to-add README.md file tailored to the exact code (I can inspect the repository to include exact dependency names, environment variable names, and paths).
- Or produce example `.env` and `run.sh` scripts to simplify steps.

Which would you prefer? (I can inspect the repo and then produce an exact README.) 
