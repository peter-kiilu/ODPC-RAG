"""Main CLI entry point for RAG Bot."""

import argparse
import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from .config import config
from .document_loader import DocumentLoader
from .chunker import TextChunker
from .vector_store import VectorStore
from .chat import ChatBot


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

console = Console()


def index_documents(data_dir: Path = None, clear: bool = False) -> None:
    """Index all documents into the vector store.
    
    Args:
        data_dir: Directory containing documents.
        clear: Whether to clear existing index first.
    """
    data_dir = data_dir or config.DATA_DIR
    downloads_dir = config.DOWNLOADS_DIR
    
    console.print(Panel.fit(
        "[bold blue]RAG Bot - Document Indexer[/bold blue]",
        border_style="blue"
    ))
    
    # Validate config
    if not config.validate():
        console.print("[red]Configuration error. Check your .env file.[/red]")
        return
    
    console.print(f"\n📁 Data directory: {data_dir}")
    console.print(f"📁 Downloads directory: {downloads_dir}")
    
    # Load documents
    console.print("\n[yellow]Loading documents...[/yellow]")
    loader = DocumentLoader(data_dir, downloads_dir)
    documents = loader.load_all()
    
    if not documents:
        console.print("[red]No documents found![/red]")
        return
    
    console.print(f"[green]✓ Loaded {len(documents)} documents[/green]")
    
    # Chunk documents
    console.print("\n[yellow]Chunking documents...[/yellow]")
    chunker = TextChunker(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP
    )
    chunks = chunker.chunk_documents(documents)
    console.print(f"[green]✓ Created {len(chunks)} chunks[/green]")
    
    # Initialize vector store
    console.print("\n[yellow]Initializing vector store...[/yellow]")
    vector_store = VectorStore()
    
    if clear:
        console.print("[yellow]Clearing existing index...[/yellow]")
        vector_store.clear()
    
    # Add chunks to vector store
    console.print("\n[yellow]Generating embeddings and indexing...[/yellow]")
    console.print("[dim](This may take a few minutes)[/dim]")
    
    vector_store.add_chunks(chunks)
    
    console.print(f"\n[green]✓ Indexing complete![/green]")
    console.print(f"[green]✓ Total documents in index: {vector_store.count}[/green]")


def start_chat() -> None:
    """Start the interactive chat interface."""
    console.print(Panel.fit(
        "[bold green]ODPC Kenya - AI Assistant[/bold green]\n"
        "[dim]Ask questions about data protection in Kenya[/dim]",
        border_style="green"
    ))
    
    # Validate config
    if not config.validate():
        console.print("[red]Configuration error. Check your .env file.[/red]")
        return
    
    # Check if index exists
    vector_store = VectorStore()
    if vector_store.count == 0:
        console.print("[yellow]No documents indexed. Run 'index' command first.[/yellow]")
        return
    
    console.print(f"\n[dim]Knowledge base: {vector_store.count} document chunks[/dim]")
    console.print("[dim]Type 'quit' to exit, 'clear' to reset conversation[/dim]\n")
    
    # Initialize chatbot
    bot = ChatBot()
    
    while True:
        try:
            # Get user input
            user_input = console.input("[bold cyan]You:[/bold cyan] ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["quit", "exit", "q"]:
                console.print("\n[yellow]Goodbye![/yellow]")
                break
            
            if user_input.lower() == "clear":
                bot.clear_history()
                console.print("[dim]Conversation cleared.[/dim]\n")
                continue
            
            # Get response
            console.print()
            with console.status("[bold green]Thinking...[/bold green]"):
                result = bot.chat(user_input)
            
            # Display response
            console.print("[bold green]Assistant:[/bold green]")
            console.print(Markdown(result["response"]))
            
            # Display sources
            if result.get("sources"):
                console.print("\n[dim]Sources:[/dim]")
                for source in result["sources"][:3]:
                    console.print(f"  [dim]• {source}[/dim]")
            
            console.print()
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            logger.exception("Chat error")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="RAG Bot - ODPC Kenya AI Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Index command
    index_parser = subparsers.add_parser("index", help="Index documents")
    index_parser.add_argument(
        "--data-dir",
        type=Path,
        help="Directory containing documents"
    )
    index_parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing index before indexing"
    )
    
    # Chat command
    subparsers.add_parser("chat", help="Start chat interface")
    
    args = parser.parse_args()
    
    if args.command == "index":
        index_documents(
            data_dir=args.data_dir,
            clear=args.clear
        )
    elif args.command == "chat":
        start_chat()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
