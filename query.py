"""
query.py — CLI chat. For most day-to-day use, query_app.py (the Streamlit UI)
is more convenient — this is kept for quick terminal testing.

Usage:
    python query.py
"""

import config
import rag_core as core


def main():
    healthy, detail = core.check_ollama_health()
    if not healthy:
        print(f"ERROR: {detail}")
        return

    print(f"Loading knowledge base from '{config.PERSIST_DIR}'...")
    try:
        vectorstore = core.get_vectorstore()
    except Exception as e:
        print(f"Could not load vector store: {e}")
        print("Did you run 'python feeder.py <books_folder>' first?")
        return

    print(f"Ready. Answering strictly from your books using '{config.DEFAULT_MODEL}'.")
    print("Type your question, '/reset' to clear conversation memory, or 'exit' to quit.\n")

    conversation_history = []

    while True:
        question = input("You: ").strip()
        if question.lower() in ("exit", "quit", "/bye"):
            break
        if question.lower() == "/reset":
            conversation_history = []
            print("Conversation memory cleared.\n")
            continue
        if not question:
            continue

        context, matches = core.retrieve_context(vectorstore, question)

        if context is None:
            print("\nSLM: I don't have information about this in the provided knowledge source.\n")
            continue

        print("  [debug] retrieval scores (lower = more relevant):")
        for doc, score in matches:
            source = doc.metadata.get("source_book", "unknown")
            method = doc.metadata.get("chunking_method", "unknown")
            print(f"    {score:.3f}  ({source}, {method} chunking)")

        print(f"\n[{config.DEFAULT_MODEL}] thinking...\n")
        full_response = ""
        for piece in core.stream_answer(config.DEFAULT_MODEL, conversation_history, question, context):
            print(piece, end="", flush=True)
            full_response += piece
        print()

        conversation_history.append({"role": "user", "content": question})
        conversation_history.append({"role": "assistant", "content": full_response})
        max_messages = config.MAX_HISTORY_TURNS * 2
        if len(conversation_history) > max_messages:
            del conversation_history[:len(conversation_history) - max_messages]

        print()


if __name__ == "__main__":
    main()
