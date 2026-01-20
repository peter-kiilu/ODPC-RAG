import logging
import traceback
from pathlib import Path
from rag_crawler.link_extractor import LinkExtractor

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def main():
    try:
        output_dir = Path("output_single")
        extractor = LinkExtractor(output_dir)
        print(f"Loaded {len(extractor.all_links)} pages.")
        
        # print("Running deduplication...")
        # removed = extractor.deduplicate_links()
        # print(f"Removed {removed} duplicates.")
        
        print("Getting statistics...")
        stats = extractor.get_statistics()
        print(f"Stats: {stats}")
        
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
