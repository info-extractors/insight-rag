import os
import re
import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from src.retrieval.hybrid import ScoredChunk
from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    doc_id: str
    page_number: int
    source_file: str
    snippet: str


@dataclass
class GenerationResult:
    answer: str
    citations: List[Citation]
    latency_ms: float
    model_name: str
    context_tokens_approx: int
    used_chunks: List[Dict[str, Any]] = field(default_factory=list)


class RAGGenerator:
    """Handles prompt assembly and generation dispatch with citation grounding."""

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or settings.LLM_PROVIDER
        self.qwen_model_name = getattr(settings, "QWEN_MODEL_NAME", "Qwen/Qwen2.5-0.5B-Instruct")
        self._qwen_model = None
        self._qwen_tokenizer = None
        self.gemini_key = os.getenv("GEMINI_API_KEY", settings.GEMINI_API_KEY)
        self.openai_key = os.getenv("OPENAI_API_KEY", settings.OPENAI_API_KEY)

    def _build_context_prompt(self, query: str, context_chunks: List[ScoredChunk]) -> str:
        formatted_blocks = []
        for idx, sc in enumerate(context_chunks, start=1):
            source = sc.chunk.metadata.get("source_file", sc.chunk.doc_id)
            page = sc.chunk.page_number
            block_type = sc.chunk.chunk_type.upper()
            formatted_blocks.append(
                f"[Source {idx} | {source} | Page {page} | {block_type}]\n{sc.chunk.content}"
            )

        context_str = "\n\n".join(formatted_blocks)
        prompt = (
            "You are an enterprise document intelligence assistant.\n"
            "Answer the query using ONLY the verified context below.\n"
            "Requirements:\n"
            "1. Append an inline citation tag to each claim or figure: [Doc: <source>, Page: <page>].\n"
            "2. If the context is insufficient, explicitly return: 'Insufficient data in provided context.'\n"
            "3. Do not invent or extrapolate statistics not directly mentioned.\n\n"
            f"--- CONTEXT ---\n{context_str}\n\n"
            f"--- QUESTION ---\n{query}\n\n"
            "--- RESPONSE ---"
        )
        return prompt

    def generate(self, query: str, context_chunks: List[ScoredChunk]) -> GenerationResult:
        t0 = time.perf_counter()

        if not context_chunks:
            return GenerationResult(
                answer="No relevant documents found matching query.",
                citations=[],
                latency_ms=0.0,
                model_name=self.provider,
                context_tokens_approx=0,
                used_chunks=[]
            )

        prompt = self._build_context_prompt(query, context_chunks)
        approx_tokens = len(prompt.split())

        citations: List[Citation] = []
        for sc in context_chunks:
            if sc.chunk.chunk_type == "table":
                snippet_text = sc.chunk.content
            else:
                snippet_text = sc.chunk.content[:200] + ("..." if len(sc.chunk.content) > 200 else "")

            citations.append(
                Citation(
                    doc_id=sc.chunk.doc_id,
                    page_number=sc.chunk.page_number,
                    source_file=sc.chunk.metadata.get("source_file", sc.chunk.doc_id),
                    snippet=snippet_text
                )
            )

        if self.provider == "qwen":
            answer = self._call_qwen(query, context_chunks)
        elif self.provider == "gemini" and self.gemini_key:
            answer = self._call_gemini(prompt)
        elif self.provider == "openai" and self.openai_key:
            answer = self._call_openai(prompt)
        else:
            answer = self._generate_deterministic_fallback(query, context_chunks)

        elapsed = (time.perf_counter() - t0) * 1000.0

        return GenerationResult(
            answer=answer,
            citations=citations,
            latency_ms=round(elapsed, 2),
            model_name=self.provider,
            context_tokens_approx=approx_tokens,
            used_chunks=[c.to_dict() for c in context_chunks]
        )

    def _call_qwen(self, query: str, context_chunks: List[ScoredChunk]) -> str:
        """Executes local generative inference using Qwen 2.5 0.5B on CPU."""
        try:
            if self._qwen_model is None:
                from transformers import AutoModelForCausalLM, AutoTokenizer
                import torch
                logger.info("Initializing local %s on CPU (low memory footprint)...", self.qwen_model_name)
                self._qwen_tokenizer = AutoTokenizer.from_pretrained(self.qwen_model_name)
                self._qwen_model = AutoModelForCausalLM.from_pretrained(
                    self.qwen_model_name,
                    torch_dtype=torch.float32,
                    low_cpu_mem_usage=True
                )

            prompt = self._build_context_prompt(query, context_chunks)
            messages = [
                {
                    "role": "system",
                    "content": "You are an enterprise document intelligence assistant. Answer the user question based strictly on the provided context documents. Include inline citations like [Doc: <name>, Page: <page>]. Do not fabricate statistics."
                },
                {"role": "user", "content": prompt}
            ]

            text = self._qwen_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = self._qwen_tokenizer([text], return_tensors="pt")

            with torch.inference_mode():
                generated_ids = self._qwen_model.generate(
                    **inputs,
                    max_new_tokens=140,
                    do_sample=False,  # Greedy decoding is significantly faster on CPU & deterministic
                    use_cache=True,
                    pad_token_id=self._qwen_tokenizer.eos_token_id
                )
            generated_ids = [
                output_ids[len(input_ids):] for input_ids, output_ids in zip(inputs.input_ids, generated_ids)
            ]
            response = self._qwen_tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return response.strip()
        except Exception as err:
            logger.warning("Local Qwen generation exception (%s). Falling back to verified grounded synthesis.", err)
            return self._generate_deterministic_fallback(query, context_chunks)

    def _call_gemini(self, prompt: str) -> str:
        try:
            from google import genai
            client = genai.Client(api_key=self.gemini_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text
        except ImportError:
            logger.error("google-genai library not found. Falling back to local synthesizer.")
            return self._generate_deterministic_fallback(prompt, [])
        except Exception as err:
            logger.error("Gemini API call failed: %s", err)
            return f"Error contacting model provider: {err}"

    def _call_openai(self, prompt: str) -> str:
        try:
            import httpx
            headers = {"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0
            }
            with httpx.Client(timeout=30.0) as client:
                res = client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()
                return data["choices"][0]["message"]["content"]
        except Exception as err:
            logger.error("OpenAI call failed: %s", err)
            return f"Error contacting OpenAI: {err}"

    def _generate_deterministic_fallback(self, query: str, context_chunks: List[ScoredChunk]) -> str:
        """Deterministic, grounded extractive synthesis for offline/testing mode without API keys."""
        if not context_chunks:
            return "No context provided."

        top_chunk = context_chunks[0]
        source_name = top_chunk.chunk.metadata.get("source_file", top_chunk.chunk.doc_id)
        page = top_chunk.chunk.page_number

        query_terms = set(re.findall(r"\b\w{3,}\b", query.lower()))
        matched_sentences = []
        table_blocks = []

        for sc in context_chunks:
            src = sc.chunk.metadata.get("source_file", sc.chunk.doc_id)
            p = sc.chunk.page_number

            if sc.chunk.chunk_type == "table" or ("|" in sc.chunk.content and "---" in sc.chunk.content):
                table_blocks.append(f"{sc.chunk.content.strip()}\n\n[Doc: {src}, Page: {p}]")
            else:
                sentences = re.split(r"(?<=[.!?])\s+", sc.chunk.content)
                for s in sentences:
                    s_words = set(re.findall(r"\b\w{3,}\b", s.lower()))
                    if s_words & query_terms:
                        clean = s.strip()
                        if clean and clean not in matched_sentences:
                            matched_sentences.append(f"{clean} [Doc: {src}, Page: {p}]")

        parts = []
        if matched_sentences:
            parts.append(" ".join(matched_sentences[:3]))
        if table_blocks:
            # Preserve raw markdown table formatting with surrounding blank lines
            parts.append(table_blocks[0])

        if parts:
            evidence = "\n\n".join(parts)
            return (
                f"{evidence}\n\n"
                f"Source: Verified from {source_name} (Page {page})."
            )

        snippet = " ".join(top_chunk.chunk.content.split()[:45])
        return (
            f"According to {source_name} (Page {page}):\n\n"
            f"\"{snippet}...\" [Doc: {source_name}, Page: {page}]."
        )
