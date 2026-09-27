"""
query_app.py — Chat with your knowledge base. Answers are grounded strictly in
retrieved content, rendered as markdown (so code blocks display properly),
with model choice and retrieval/generation settings configurable in the sidebar.

Run with: streamlit run query_app.py
"""

import time

import streamlit as st

import config
import rag_core as core


def render_source_line(doc, score, discarded: bool = False):
    source = doc.metadata.get("source_book", "unknown")
    method = doc.metadata.get("chunking_method", "unknown")
    suffix = " (above threshold, discarded)" if discarded else ""
    st.markdown(
        f"**{source}** · _{method} chunking_ — relevance score `{score:.3f}`{suffix}")


def split_answer(response):
    marker = "**Answer:**"
    if marker in response:
        reasoning, answer = response.split(marker, 1)
        return reasoning.replace("**Reasoning:**", "").strip(), answer.strip()
    return "", response.strip()


def render_answer_details(details):
    with st.expander("ⓘ Answer details"):
        elapsed = details.get("elapsed_seconds")
        if elapsed is not None:
            st.caption(f"Generated in {elapsed:.1f} seconds")

        reasoning = details.get("reasoning")
        if reasoning:
            st.markdown("**Reasoning**")
            st.markdown(reasoning)

        matches = details.get("matches") or []
        if matches:
            st.markdown("**Retrieved sources**")
            for doc, score in matches:
                render_source_line(
                    doc, score, discarded=details.get("discarded", False))
                st.text(
                    doc.page_content[:300] + ("..." if len(doc.page_content) > 300 else ""))


st.set_page_config(page_title="Ask Your Knowledge Base",
                   page_icon="🤖", layout="wide")
st.title("🤖 Ask Your Knowledge Base")
st.caption(
    "Answers come only from your knowledge sources — no outside knowledge, no internet calls.")

# --- Health check ------------------------------------------------------------

healthy, detail = core.check_ollama_health()
if not healthy:
    st.error(f"Ollama isn't reachable: {detail}")
    st.info("Start Ollama, then refresh this page.")
    st.stop()

missing = core.check_models_available(
    [config.EMBED_MODEL] + config.AVAILABLE_MODELS, detail)
if missing:
    st.warning(
        f"Some configured models aren't pulled yet: {', '.join(missing)}. "
        f"They'll still show in the dropdown, but selecting one will fail until you run "
        f"`ollama pull <model>` for it."
    )

# --- Sidebar: model + config ------------------------------------------------

with st.sidebar:
    st.header("Settings")

    model = st.selectbox(
        "Model (SLM/LLM)",
        options=config.AVAILABLE_MODELS,
        index=0,
        help="phi4-mini is the recommended small model for strict, grounded "
             "answers. qwen3:8b / qwen3:14b are larger — slower but sometimes "
             "better reasoning — useful for comparison.",
    )

    st.divider()
    st.subheader("Retrieval")

    top_k = st.slider(
        "Chunks to retrieve (top_k)", min_value=1, max_value=10,
        value=config.TOP_K_DEFAULT,
        help="How many chunks from the knowledge base to hand to the model per question.",
    )

    relevance_threshold = st.slider(
        "Relevance threshold (cosine distance)", min_value=0.0, max_value=2.0,
        value=config.RELEVANCE_THRESHOLD_DEFAULT, step=0.05,
        help="Lower = stricter (only very close matches count as relevant). "
             "0 = identical, 2 = completely unrelated. Raise this if the model "
             "refuses questions the books actually cover; lower it if it's "
             "answering from irrelevant chunks.",
    )

    st.divider()
    st.subheader("Generation")

    temperature = st.slider(
        "Temperature", min_value=0.0, max_value=1.0,
        value=config.TEMPERATURE_DEFAULT, step=0.05,
        help="0 = fully deterministic, grounded answers. Higher = more varied "
             "wording, but less predictable — usually keep this low for RAG.",
    )

    st.divider()
    show_details = st.checkbox("Show technical answer details", value=True)

    if st.button("🔄 Reset conversation"):
        st.session_state.messages = []
        st.rerun()

# --- Load vector store (cached so it's not reloaded every rerun) -----------


@st.cache_resource
def load_store():
    return core.get_vectorstore()


try:
    vectorstore = load_store()
except Exception as e:
    st.error(f"Could not load the knowledge base: {e}")
    st.info("Ingest some knowledge sources first using knowledge_builder_app.py.")
    st.stop()

manifest = core.load_manifest()
if not manifest:
    st.warning("Your knowledge base is empty. Ingest knowledge sources using knowledge_builder_app.py before asking questions.")

# --- Chat state --------------------------------------------------------------

if "messages" not in st.session_state:
    # each item: {"role": ..., "content": ..., "sources": [...] or None}
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("details"):
            render_answer_details(msg["details"])

# --- New question ------------------------------------------------------------

question = st.chat_input("Ask something about your knowledge sources...")

if question:
    st.session_state.messages.append(
        {"role": "user", "content": question, "sources": None})
    with st.chat_message("user"):
        st.markdown(question)

    context, matches = core.retrieve_context(
        vectorstore, question, top_k, relevance_threshold)

    with st.chat_message("assistant"):
        if context is None:
            answer = "I don't have information about this in the provided knowledge source."
            st.markdown(answer)
            st.caption(
                "No answer generated because no relevant source was found.")
            if show_details and matches:
                render_answer_details({
                    "matches": matches,
                    "discarded": True,
                })
            details = {"matches": matches, "discarded": True}
        else:
            history = []
            for m in st.session_state.messages[:-1]:
                history.append({"role": m["role"], "content": m["content"]})
            # Keep only the most recent turns, matching the CLI's memory window
            max_messages = config.MAX_HISTORY_TURNS * 2
            history = history[-max_messages:]

            answer_placeholder = st.empty()
            full_response = ""
            started_at = time.perf_counter()
            try:
                with st.spinner("Thinking..."):
                    for piece in core.stream_answer(
                            model, history, question, context, temperature):
                        full_response += piece
                        _, visible_answer = split_answer(full_response)
                        answer_placeholder.markdown(
                            visible_answer or "Thinking...")
                reasoning, answer = split_answer(full_response)
                elapsed = time.perf_counter() - started_at
                answer_placeholder.markdown(answer)
                st.caption(f"Generated in {elapsed:.1f} seconds")
                details = {
                    "reasoning": reasoning,
                    "matches": matches,
                    "elapsed_seconds": elapsed,
                }
            except Exception as e:
                answer = f"⚠️ Generation failed: {e}"
                st.error(answer)
                details = {"matches": matches}

            if show_details:
                render_answer_details(details)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "details": details,
    })
