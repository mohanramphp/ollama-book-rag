"""
knowledge_builder_app.py — Upload knowledge sources and watch them get ingested into the local
knowledge base, with live progress and a catalog of what's already in.

Run with: streamlit run knowledge_builder_app.py
"""

import streamlit as st

import config
import rag_core as core

st.set_page_config(page_title="Knowledge Builder",
                   page_icon="📚", layout="wide")
st.title("📚 Knowledge Builder")
st.caption("Upload documents to add them to your local, offline knowledge base.")

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

st.subheader("Add knowledge sources")

chunking_method = st.radio(
    "Chunking method",
    options=["Recursive (fast, fixed-size)",
             "Semantic (slower, groups by meaning)"],
    horizontal=True,
    help="Semantic chunking embeds sentence-by-sentence to find natural topic "
         "breaks — better quality for prose, but noticeably slower on CPU.",
)
use_semantic = chunking_method.startswith("Semantic")

uploaded_files = st.file_uploader(
    "Choose PDF, EPUB, TXT, or Markdown files",
    type=["pdf", "epub", "txt", "md"],
    accept_multiple_files=True,
)

if uploaded_files and st.button("Ingest selected files", type="primary"):
    for uploaded_file in uploaded_files:
        file_bytes = uploaded_file.getvalue()

        st.markdown(f"### {uploaded_file.name}")

        dest_path = core.SOURCES_DIR / uploaded_file.name
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
                # don't leave a redundant renamed copy on disk
                dest_path.unlink(missing_ok=True)
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
st.subheader("📖 Catalog — sources in your knowledge base")

manifest = core.load_manifest()

if not manifest:
    st.info("No knowledge sources ingested yet. Upload some above to get started.")
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
    st.caption(
        f"{len(rows)} book(s), {total_chunks} total chunks in the knowledge base.")

    with st.expander("⚠️ Danger zone: reset everything"):
        st.write("This deletes the vector database, the catalog, **and the uploaded "
                 "source files themselves** from the `./knowledge_sources` folder. This can't be undone.")
        if st.button("Delete knowledge base, catalog, and book files", type="secondary"):
            import shutil
            from pathlib import Path

            shutil.rmtree(config.PERSIST_DIR, ignore_errors=True)
            Path(config.MANIFEST_PATH).unlink(missing_ok=True)

            for f in core.SOURCES_DIR.glob("*"):
                if f.is_file() and f.name != ".gitkeep":
                    f.unlink()

            st.success(
                "Reset. Upload your knowledge sources again to rebuild the knowledge base.")
            st.rerun()
