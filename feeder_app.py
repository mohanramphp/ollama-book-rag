"""
feeder_app.py — Upload books and watch them get ingested into the local
knowledge base, with live progress and a catalog of what's already in.

Run with: streamlit run feeder_app.py
"""

import streamlit as st

import config
import rag_core as core

st.set_page_config(page_title="Book Feeder", page_icon="📚", layout="wide")
st.title("📚 Book Feeder")
st.caption("Upload books to add them to your local, offline knowledge base.")

# --- Health check ------------------------------------------------------------

healthy, detail = core.check_ollama_health()
if not healthy:
    st.error(f"Ollama isn't reachable: {detail}")
    st.info("Start Ollama, then refresh this page.")
    st.stop()

missing = core.check_models_available([config.EMBED_MODEL], detail)
if missing:
    st.error(f"Required model(s) not pulled yet: {', '.join(missing)}")
    st.code(f"ollama pull {missing[0]}")
    st.stop()

# --- Upload + ingest ------------------------------------------------------

st.subheader("Add books")

chunking_method = st.radio(
    "Chunking method",
    options=["Recursive (fast, fixed-size)", "Semantic (slower, groups by meaning)"],
    horizontal=True,
    help="Semantic chunking embeds sentence-by-sentence to find natural topic "
         "breaks — better quality for prose, but noticeably slower on CPU.",
)
use_semantic = chunking_method.startswith("Semantic")

uploaded_files = st.file_uploader(
    "Choose PDF, EPUB, or TXT files",
    type=["pdf", "epub", "txt", "md"],
    accept_multiple_files=True,
)

if uploaded_files and st.button("Ingest selected files", type="primary"):
    for uploaded_file in uploaded_files:
        file_bytes = uploaded_file.getvalue()

        st.markdown(f"### {uploaded_file.name}")

        dest_path = core.BOOKS_DIR / uploaded_file.name
        with open(dest_path, "wb") as f:
            f.write(file_bytes)

        progress_bar = st.progress(0, text="Starting...")
        status_text = st.empty()

        for update in core.ingest_book(dest_path, semantic=use_semantic):
            stage = update["stage"]

            if stage == "error":
                progress_bar.empty()
                st.error(f"Failed: {update['message']}")
                break

            elif stage == "duplicate":
                progress_bar.empty()
                st.warning(update["message"])
                dest_path.unlink(missing_ok=True)  # don't leave a redundant renamed copy on disk
                break

            elif stage == "embedding":
                pct = int(100 * update["current"] / update["total"])
                progress_bar.progress(pct, text=update["message"])

            elif stage == "done":
                progress_bar.progress(100, text=update["message"])
                st.success(f"✅ {update['message']}")

            else:
                status_text.text(update["message"])

    st.rerun()

# --- Catalog ---------------------------------------------------------------

st.divider()
st.subheader("📖 Catalog — books in your knowledge base")

manifest = core.load_manifest()

if not manifest:
    st.info("No books ingested yet. Upload some above to get started.")
else:
    rows = []
    for content_hash, info in manifest.items():
        rows.append({
            "Book": info["filename"],
            "Ingested": info["ingested_at"],
            "Pages": info["pages"],
            "Chunks": info["chunks"],
            "Method": info["chunking_method"],
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

    total_chunks = sum(r["Chunks"] for r in rows)
    st.caption(f"{len(rows)} book(s), {total_chunks} total chunks in the knowledge base.")

    with st.expander("⚠️ Danger zone: reset everything"):
        st.write("This deletes the vector database, the catalog, **and the uploaded "
                 "book files themselves** from the `./books` folder. This can't be undone.")
        if st.button("Delete knowledge base, catalog, and book files", type="secondary"):
            import shutil
            from pathlib import Path

            shutil.rmtree(config.PERSIST_DIR, ignore_errors=True)
            Path(config.MANIFEST_PATH).unlink(missing_ok=True)

            for f in core.BOOKS_DIR.glob("*"):
                if f.is_file() and f.name != ".gitkeep":
                    f.unlink()

            st.success("Reset. Upload your books again to rebuild the knowledge base.")
            st.rerun()
