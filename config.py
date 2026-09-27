"""
config.py — Centralized configuration for the whole project.

Every value here can be overridden with an environment variable of the same
name (see the .env.example file), so you can tune behavior without editing
code — useful once you're running this as more than a personal experiment.
"""

import os

# --- Paths -----------------------------------------------------------------

SOURCES_DIR = os.environ.get(
    "RAG_SOURCES_DIR",
    "./knowledge_sources",
)
PERSIST_DIR = os.environ.get("RAG_PERSIST_DIR", "./chroma_db")
MANIFEST_PATH = os.environ.get(
    "RAG_MANIFEST_PATH", "./knowledge_sources_manifest.json")

# --- Models ------------------------------------------------------------

EMBED_MODEL = os.environ.get("RAG_EMBED_MODEL", "nomic-embed-text")
DEFAULT_MODEL = os.environ.get("RAG_DEFAULT_MODEL", "phi4-mini")
AVAILABLE_MODELS = [
    m.strip() for m in os.environ.get(
        "RAG_AVAILABLE_MODELS", "phi4-mini,gemma3:4b,qwen3:8b,qwen3:14b"
    ).split(",")
]

# --- Chunking ------------------------------------------------------------

CHUNK_SIZE = int(os.environ.get("RAG_CHUNK_SIZE", 800))
CHUNK_OVERLAP = int(os.environ.get("RAG_CHUNK_OVERLAP", 120))
SEMANTIC_MAX_CHUNK_SIZE = int(
    os.environ.get("RAG_SEMANTIC_MAX_CHUNK_SIZE", 1200))

# --- Retrieval + generation defaults (adjustable live in query_app.py) -----

TOP_K_DEFAULT = int(os.environ.get("RAG_TOP_K", 4))
RELEVANCE_THRESHOLD_DEFAULT = float(
    os.environ.get("RAG_RELEVANCE_THRESHOLD", 0.8))
MAX_CHUNKS_PER_SOURCE_DEFAULT = int(
    os.environ.get("RAG_MAX_CHUNKS_PER_SOURCE", 2))
TEMPERATURE_DEFAULT = float(os.environ.get("RAG_TEMPERATURE", 0.0))
MAX_HISTORY_TURNS = int(os.environ.get("RAG_MAX_HISTORY_TURNS", 6))

# --- Resilience (retry/backoff for embedding calls) ------------------------

EMBED_BATCH_SIZE = int(os.environ.get("RAG_EMBED_BATCH_SIZE", 40))
SEMANTIC_EMBED_BATCH_SIZE = int(
    os.environ.get("RAG_SEMANTIC_EMBED_BATCH_SIZE", 20))
MAX_RETRIES = int(os.environ.get("RAG_MAX_RETRIES", 4))
RETRY_DELAY_SECONDS = int(os.environ.get("RAG_RETRY_DELAY_SECONDS", 10))
RETRY_MAX_DELAY_SECONDS = int(
    os.environ.get("RAG_RETRY_MAX_DELAY_SECONDS", 120))

# --- Ollama connection -------------------------------------------------

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
