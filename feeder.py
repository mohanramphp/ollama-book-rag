"""
feeder.py — CLI ingestion. For most day-to-day use, feeder_app.py (the
Streamlit UI) is more convenient — this is kept for scripting/automation.

Usage:
    python feeder.py <folder_with_books> [--semantic]
"""

import sys
from pathlib import Path

import config
import rag_core as core


def main():
    if len(sys.argv) < 2:
        print("Usage: python feeder.py <folder_with_books> [--semantic]")
        sys.exit(1)

    healthy, detail = core.check_ollama_health()
    if not healthy:
        print(f"ERROR: {detail}")
        sys.exit(1)

    use_semantic = "--semantic" in sys.argv
    books_dir = Path(sys.argv[1])
    if not books_dir.is_dir():
        print(f"Folder not found: {books_dir}")
        sys.exit(1)

    files = sorted(p for p in books_dir.glob("*") if p.suffix.lower() in (".pdf", ".epub", ".txt", ".md"))
    if not files:
        print(f"No supported files found in {books_dir}")
        sys.exit(1)

    print(f"Found {len(files)} file(s) in {books_dir}\n")

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

    print("\nAll done. Run 'python query.py' or 'streamlit run query_app.py' to ask questions.")


if __name__ == "__main__":
    main()
