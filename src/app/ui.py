from pathlib import Path
import streamlit as st
import time

from src.app.pipeline import InsightRAGPipeline
from src.config import settings

# Page Setup
st.set_page_config(
    page_title="InsightRAG | Document Intelligence Platform",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def get_pipeline():
    p = InsightRAGPipeline()
    for doc_file in settings.SAMPLE_DOCS_DIR.glob("*.*"):
        if doc_file.suffix.lower() in [".pdf", ".txt", ".md"]:
            try:
                p.ingest_file(doc_file)
            except Exception:
                pass
    return p

pipeline = get_pipeline()

# Styling
st.markdown("""
<style>
    .main-header { font-size: 1.85rem; font-weight: 600; color: #0F172A; margin-bottom: 0.1rem; }
    .sub-header { font-size: 0.95rem; color: #475569; margin-bottom: 1.5rem; }
    .status-pass { color: #15803D; font-weight: 600; }
    .status-warn { color: #B91C1C; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.subheader("InsightRAG")
    st.caption("Hybrid Retrieval & Document Intelligence")
    st.divider()

    st.markdown("**Index Status**")
    stats = pipeline.stats()
    st.write(f"Chunks: `{stats['dense_vectors_count']}`")
    st.write(f"Documents: `{len(stats['indexed_documents'])}`")
    st.write(f"Embedding: `{settings.DENSE_MODEL_NAME.split('/')[-1]}`")
    st.write(f"Reranker: `{settings.RERANKER_MODEL_NAME.split('/')[-1]}`")
    st.write(f"LLM: `{settings.LLM_PROVIDER}`")
    st.divider()

    st.markdown("**Ingest Document**")
    uploaded_file = st.file_uploader("Upload PDF, TXT, or MD", type=["pdf", "txt", "md"])
    if uploaded_file is not None:
        if st.button("Index Document", type="primary"):
            save_path = settings.SAMPLE_DOCS_DIR / uploaded_file.name
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            with st.spinner("Processing document..."):
                res = pipeline.ingest_file(save_path)
                st.success(f"Indexed {res['chunks_indexed']} chunks in {res['ingestion_time_ms']} ms")
                st.rerun()

# Main Header
st.markdown('<div class="main-header">InsightRAG: Document Intelligence Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Multi-stage hybrid retrieval with Reciprocal Rank Fusion, Cross-Encoder reranking, and citation guardrails.</div>', unsafe_allow_html=True)

tab_query, tab_inspector, tab_eval = st.tabs(["Query", "Retrieval Inspector", "Evaluation"])

with tab_query:
    col1, col2 = st.columns([2, 1])

    with col1:
        sample_queries = [
            "What was the total Cloud revenue in FY2024 and how does it compare to FY2023?",
            "What were the key operating risks identified in the enterprise report?",
            "Summarize the capital expenditure and R&D spending from the financial tables.",
        ]
        selected_sample = st.selectbox("Sample queries:", ["Custom Question"] + sample_queries)
        default_q = "" if selected_sample == "Custom Question" else selected_sample
        user_query = st.text_input("Query:", value=default_q, placeholder="e.g. What were the quarterly profit margins?")

        col_btn, col_k = st.columns([1, 2])
        with col_btn:
            submit_btn = st.button("Search", type="primary", use_container_width=True)
        with col_k:
            top_k_slider = st.slider("Top-K Reranked Context", min_value=1, max_value=5, value=3)

    if submit_btn and user_query:
        if pipeline.dense_store.count() == 0:
            st.warning("No documents indexed. Ingest a document in the sidebar to begin.")
        else:
            with st.spinner("Retrieving and generating..."):
                response = pipeline.query(user_query, top_k_final=top_k_slider)
            st.session_state["last_response"] = response

    if "last_response" in st.session_state:
        resp = st.session_state["last_response"]

        st.divider()
        st.markdown("**Answer**")
        st.markdown(resp.answer)

        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Latency", f"{resp.total_latency_ms} ms")
        m2.metric("Retrieval (RRF)", f"{resp.latency_breakdown_ms['hybrid_retrieval_ms']} ms")
        m3.metric("Rerank", f"{resp.latency_breakdown_ms['reranking_ms']} ms")
        m4.metric("Faithfulness", f"{resp.guardrail['faithfulness_score'] * 100:.1f}%")

        if resp.citations:
            st.markdown("**Citations**")
            for c in resp.citations:
                with st.expander(f"{c['source_file']} (Page {c['page_number']})"):
                    st.caption(f"Doc ID: {c['doc_id']}")
                    if "|" in c['snippet'] and "---" in c['snippet']:
                        st.markdown(c['snippet'])
                    else:
                        st.text(c['snippet'])

with tab_inspector:
    st.subheader("Retrieval Breakdown")
    st.caption("Comparison of Dense Cosine Similarity and Sparse BM25 ranks fused via RRF and reranked by Cross-Encoder.")

    if "last_response" in st.session_state:
        resp = st.session_state["last_response"]
        for idx, sc in enumerate(resp.retrieved_chunks, start=1):
            with st.container(border=True):
                st.markdown(f"**Rank #{idx}: {sc['metadata'].get('source_file', sc['doc_id'])} (Page {sc['page_number']})**")
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Rerank Score", sc.get("rerank_score", "N/A"))
                c2.metric("RRF Score", sc.get("rrf_score", "N/A"))
                c3.metric("Dense Rank / Sim", f"#{sc.get('dense_rank')} ({sc.get('dense_score')})")
                c4.metric("BM25 Rank / Score", f"#{sc.get('sparse_rank')} ({sc.get('sparse_score')})")

                st.markdown("**Excerpt:**")
                if sc.get("chunk_type") == "table" or ("|" in sc.get("content", "") and "---" in sc.get("content", "")):
                    st.markdown(sc["content"])
                else:
                    st.text(sc["content"])
    else:
        st.info("Run a query to inspect internal score weights.")

with tab_eval:
    st.subheader("Evaluation Metrics")
    if "last_response" in st.session_state:
        resp = st.session_state["last_response"]
        eval_data = resp.evaluation
        guard = resp.guardrail

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("**Guardrail Checks**")
            status_text = "PASSED" if guard["passed"] else "ATTENTION NEEDED"
            css_class = "status-pass" if guard["passed"] else "status-warn"
            st.markdown(f"Status: <span class='{css_class}'>{status_text}</span>", unsafe_allow_html=True)
            st.write(f"- Verified Citations: `{guard['verified_citations']}`")
            st.write(f"- Unverified Citations: `{guard['unverified_citations']}`")
            if guard["hallucinated_numbers"]:
                st.warning(f"Unverified numeric claims: {guard['hallucinated_numbers']}")
            else:
                st.success("All numbers and statistics verified in source context.")

        with col_g2:
            st.markdown("**RAG Triad Metrics**")
            st.metric("Context Relevance", f"{eval_data['context_relevance'] * 100:.1f}%")
            st.metric("Groundedness", f"{eval_data['groundedness'] * 100:.1f}%")
            st.metric("Answer Relevance", f"{eval_data['answer_relevance'] * 100:.1f}%")
            st.metric("Composite Score", f"{eval_data['composite_rag_score'] * 100:.1f}%")
    else:
        st.info("Run a query to inspect metrics.")
