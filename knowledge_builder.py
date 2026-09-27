"""
knowledge_builder.py — CLI ingestion. For most day-to-day use, knowledge_builder_app.py (the
Streamlit UI) is more convenient — this is kept for scripting/automation.

Usage:
    py knowledge_builder.py <knowledge_sources_folder> [--semantic]
"""

import sys
from pathlib import Path

import config
import rag_core as core


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: py knowledge_builder.py <knowledge_sources_folder> [--semantic]")
        sys.exit(1)

    healthy, detail = core.check_ollama_health()
    if not healthy:
        print(f"ERROR: {detail}")
        sys.exit(1)

    use_semantic = "--semantic" in sys.argv
    sources_dir = Path(sys.argv[1])
    if not sources_dir.is_dir():
        print(f"Folder not found: {sources_dir}")
        sys.exit(1)

    files = sorted(p for p in sources_dir.glob(
        "*") if p.suffix.lower() in (".pdf", ".epub", ".txt", ".md"))
    if not files:
        print(f"No supported files found in {sources_dir}")
        sys.exit(1)

    print(f"Found {len(files)} file(s) in {sources_dir}\n")

    for f in files:
        print(f"Ingesting: {f.name}")
        for update in core.ingest_book(f, semantic=use_semantic):
            if update["stage"] == "error":
                print(f"  ERROR: {update['message']}")
                break
            if update["stage"] == "duplicate":
                print(f"  SKIPPED: {update['message']}")
                break
            print(f"  {update['message']}")

    print("\nAll done. Run 'py query.py' or 'streamlit run query_app.py' to query the knowledge base.")


if __name__ == "__main__":
    main()
