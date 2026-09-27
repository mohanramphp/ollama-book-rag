"""
rag_core.py — Shared logic for the knowledge-base project. Every entry point
(knowledge_builder_app.py, query_app.py, knowledge_builder.py, query.py) imports from here, so
there's exactly one implementation of chunking/embedding/retrieval/chat to
keep correct instead of several copies drifting apart.
"""

import hashlib
import json
import time
from datetime import datetime
from pathlib import Path

import requests
from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredEPubLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
import ollama

import config

SOURCES_DIR = Path(config.SOURCES_DIR)
SOURCES_DIR.mkdir(exist_ok=True)

SYSTEM_PROMPT = """You are a knowledge assistant that answers questions using ONLY the
context provided below, which comes from the user's own book collection.

Respond in exactly this two-part format:

**Reasoning:** One or two sentences on which part of the provided context (and
which source book) you're drawing from, and why it answers the question.
If nothing in the context is relevant, say so here.

**Answer:** Your actual answer to the question, using only the provided context.

Rules you must follow strictly:
- Answer using only the information in the provided context.
- Do not use any outside knowledge, even if you know the answer from training.
- If the context does not contain enough information to answer, the Answer
  line must be exactly:
  "I don't have information about this in the provided knowledge source."
- Do not speculate or fill gaps with assumptions.
- If the context includes code, or the question asks for code, include it in
  your Answer using a fenced markdown code block with the correct language
  tag (for example ```javascript), reproduced accurately from the context.
  Do not paraphrase code into prose.
"""


# --- Health check ---------------------------------------------------------

def check_ollama_health(timeout: int = 3):
    """
    Returns (is_healthy: bool, detail: str or list[str]).
    On success, detail is the list of locally available model names.
    On failure, detail is a human-readable reason, so callers can show a
    clear message instead of a raw connection traceback.
    """
    try:
        resp = requests.get(f"{config.OLLAMA_HOST}/api/tags", timeout=timeout)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        return True, models
    except requests.exceptions.ConnectionError:
        return False, (
            f"Could not connect to Ollama at {config.OLLAMA_HOST}. "
            "Is the Ollama app/service running?"
        )
    except Exception as e:
        return False, f"Unexpected error reaching Ollama: {e}"


def check_models_available(required_models: list, available_models: list) -> list:
    """Returns the subset of required_models that are NOT in available_models."""
    missing = []
    for m in required_models:
        # Ollama sometimes reports "name:latest" — compare loosely
        if not any(m == avail or avail.startswith(m + ":") for avail in available_models):
            missing.append(m)
    return missing


# --- Manifest (dedup + catalog tracking) ---------------------------------

def load_manifest() -> dict:
    manifest_path = Path(config.MANIFEST_PATH)
    if not manifest_path.exists():
        return {}
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(manifest: dict):
    with open(config.MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def content_text_hash(docs) -> str:
    """
    Hashes the *extracted text*, not the raw file bytes. This is the mechanism
    that actually matters for dedup: a renamed file, a re-saved PDF, or a
    re-exported EPUB can all produce different raw bytes for the exact same
    text content — hashing the extracted text catches all of those as the
    same book, where a raw file hash would miss them.
    """
    combined = "\n".join(d.page_content for d in docs)
    return hashlib.sha256(combined.encode("utf-8", errors="ignore")).hexdigest()


def is_already_ingested(content_hash: str) -> bool:
    return content_hash in load_manifest()


# --- Loading + chunking ---------------------------------------------------

def load_file(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return PyPDFLoader(str(path)).load()
    elif suffix == ".epub":
        return UnstructuredEPubLoader(str(path)).load()
    elif suffix in (".txt", ".md"):
        return TextLoader(str(path), encoding="utf-8").load()
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")


class ResilientOllamaEmbeddings(OllamaEmbeddings):
    """Batches + retries embed_documents() calls so a large request can't
    overwhelm or crash the local Ollama runner."""
    batch_size: int = config.SEMANTIC_EMBED_BATCH_SIZE
    max_retries: int = config.MAX_RETRIES
    retry_delay_seconds: int = config.RETRY_DELAY_SECONDS

    def embed_documents(self, texts):
        all_embeddings = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start:start + self.batch_size]
            for attempt in range(1, self.max_retries + 1):
                try:
                    all_embeddings.extend(super().embed_documents(batch))
                    break
                except Exception:
                    if attempt == self.max_retries:
                        raise
                    time.sleep(self.retry_delay_seconds)
        return all_embeddings


def ingest_book(file_path: Path, semantic: bool = False):
    """
    Generator that yields progress updates as dicts, so a UI or CLI can
    render live progress. Yields:
      {"stage": "loading" | "duplicate" | "chunking" | "embedding" | "done" | "error", ...}

    Blocks ingestion (yields "duplicate" and stops) if this book's extracted
    text content matches something already in the knowledge base — even if
    the filename is different or the underlying file bytes differ slightly.
    """
    try:
        yield {"stage": "loading", "message": f"Loading {file_path.name}..."}
        docs = load_file(file_path)
        for d in docs:
            d.metadata["source_book"] = file_path.name

        yield {"stage": "loading", "message": f"Loaded {len(docs)} page(s)/section(s)"}

        content_hash = content_text_hash(docs)
        manifest = load_manifest()
        if content_hash in manifest:
            existing = manifest[content_hash]
            yield {
                "stage": "duplicate",
                "message": (
                    f"This book's content matches '{existing['filename']}', "
                    f"already ingested on {existing['ingested_at']}. Skipping "
                    f"to avoid duplicate chunks in the knowledge base."
                ),
                "existing": existing,
            }
            return

        if semantic:
            yield {"stage": "chunking", "message": "Splitting semantically (embeds sentence-by-sentence first)..."}
            from langchain_experimental.text_splitter import SemanticChunker
            splitter = SemanticChunker(
                ResilientOllamaEmbeddings(model=config.EMBED_MODEL),
                breakpoint_threshold_type="percentile",
            )
        else:
            yield {"stage": "chunking", "message": "Splitting into fixed-size chunks..."}
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=config.CHUNK_SIZE,
                chunk_overlap=config.CHUNK_OVERLAP,
                separators=["\n\n", "\n", ". ", " ", ""],
            )

        chunks = splitter.split_documents(docs)
        method_label = "semantic" if semantic else "recursive"
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunking_method"] = method_label
            chunk.metadata["chunk_index"] = i
        yield {"stage": "chunking", "message": f"Created {len(chunks)} chunks", "total_chunks": len(chunks)}

        embeddings = OllamaEmbeddings(model=config.EMBED_MODEL)
        vectorstore = Chroma(
            persist_directory=config.PERSIST_DIR,
            embedding_function=embeddings,
            collection_metadata={"hnsw:space": "cosine"},
        )

        total = len(chunks)
        for start in range(0, total, config.EMBED_BATCH_SIZE):
            batch = chunks[start:start + config.EMBED_BATCH_SIZE]
            for attempt in range(1, config.MAX_RETRIES + 1):
                try:
                    vectorstore.add_documents(batch)
                    break
                except Exception:
                    if attempt == config.MAX_RETRIES:
                        raise
                    time.sleep(config.RETRY_DELAY_SECONDS)
            done = min(start + config.EMBED_BATCH_SIZE, total)
            yield {
                "stage": "embedding",
                "message": f"Embedded {done}/{total} chunks",
                "current": done,
                "total": total,
            }

        manifest = load_manifest()
        manifest[content_hash] = {
            "filename": file_path.name,
            "ingested_at": datetime.now().isoformat(timespec="seconds"),
            "pages": len(docs),
            "chunks": len(chunks),
            "chunking_method": "semantic" if semantic else "recursive",
        }
        save_manifest(manifest)

        yield {"stage": "done", "message": f"Done — {file_path.name} is ready to query", "chunks": len(chunks)}

    except Exception as e:
        yield {"stage": "error", "message": str(e)}


# --- Retrieval + chat -------------------------------------------------------

def get_vectorstore():
    embeddings = OllamaEmbeddings(model=config.EMBED_MODEL)
    return Chroma(
        persist_directory=config.PERSIST_DIR,
        embedding_function=embeddings,
        collection_metadata={"hnsw:space": "cosine"},
    )


def retrieve_context(vectorstore, question: str, top_k: int = None, relevance_threshold: float = None):
    """Returns (context_string_or_None, list_of_(doc, score)_all_results)."""
    top_k = top_k if top_k is not None else config.TOP_K_DEFAULT
    relevance_threshold = relevance_threshold if relevance_threshold is not None else config.RELEVANCE_THRESHOLD_DEFAULT

    results = vectorstore.similarity_search_with_score(question, k=top_k)
    if not results:
        return None, []

    relevant = [(doc, score)
                for doc, score in results if score <= relevance_threshold]
    if not relevant:
        return None, results

    context_blocks = []
    for doc, score in relevant:
        source = doc.metadata.get("source_book", "unknown")
        context_blocks.append(f"[Source: {source}]\n{doc.page_content}")

    return "\n\n---\n\n".join(context_blocks), relevant


def stream_answer(model: str, history: list, question: str, context: str, temperature: float = None):
    """Yields response text pieces as they're generated (for live streaming)."""
    temperature = temperature if temperature is not None else config.TEMPERATURE_DEFAULT

    user_message = f"""Context from the user's books (for this question only):

{context}

Question: {question}"""

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + \
               [{"role": "user", "content": user_message}]

    stream = ollama.chat(
        model=model,
        messages=messages,
        options={"temperature": temperature},
        stream=True,
    )
    for chunk in stream:
        yield chunk["message"]["content"]
