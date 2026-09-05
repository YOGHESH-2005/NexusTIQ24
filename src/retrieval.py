"""
retrieval.py — Local semantic RAG pipeline for TrustTrace AI.

Architecture (when GEMINI_API_KEY is available):
    Load rule .md files
    → section-level chunking (split on ## headings)
    → Gemini gemini-embedding-001 embeddings per chunk
    → local NumPy vector store (in-memory)
    → cosine similarity at query time
    → top-K chunks returned

Offline fallback (GEMINI_API_KEY missing / embedding fails):
    → rule-ID direct match + keyword term counting (original behaviour)

No external / hosted vector databases.
"""

import os
import glob
import re
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------
RULES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "rules"
)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class DocumentChunk:
    """A single chunk produced from a rule document section."""
    __slots__ = ("chunk_id", "doc_id", "doc_filename", "section_title", "content")

    def __init__(
        self,
        chunk_id: str,
        doc_id: str,
        doc_filename: str,
        section_title: str,
        content: str,
    ):
        self.chunk_id = chunk_id          # e.g. "R01_chunk_0"
        self.doc_id = doc_id              # e.g. "R01"
        self.doc_filename = doc_filename  # e.g. "rule_R01.md"
        self.section_title = section_title  # e.g. "Investigator Guidance"
        self.content = content            # raw text of this chunk

    def as_dict(self) -> Dict[str, str]:
        """Serialise to the legacy Dict[str, str] format expected by callers."""
        return {
            "id": self.doc_id,
            "filename": self.doc_filename,
            "section": self.section_title,
            "content": f"[{self.doc_id} — {self.section_title}]\n{self.content}",
        }


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _chunk_document(doc_id: str, filename: str, raw_text: str) -> List[DocumentChunk]:
    """
    Split a rule document into section-level chunks by splitting on '## ' headings.

    Strategy:
    - Treat the text before the first '## ' heading as chunk 0 (the document title/intro).
    - Each '## heading' block becomes its own chunk.
    - Chunks shorter than 30 characters are merged into the preceding chunk to
      avoid trivially small slices.
    - Each chunk retains its source doc_id and section title for metadata.
    """
    # Split on lines that start with "## " (second-level headings)
    section_pattern = re.compile(r"^## .+", re.MULTILINE)
    split_points = [m.start() for m in section_pattern.finditer(raw_text)]

    sections: List[Tuple[str, str]] = []  # (title, body)

    if not split_points:
        # No headings — treat whole document as one chunk
        sections.append(("Document", raw_text.strip()))
    else:
        # Intro block (everything before first ## heading)
        intro = raw_text[: split_points[0]].strip()
        if intro:
            # Extract doc title from first # heading if present
            title_match = re.match(r"^# (.+)", intro)
            title = title_match.group(1).strip() if title_match else "Introduction"
            sections.append((title, intro))

        # Each ## section
        for i, start in enumerate(split_points):
            end = split_points[i + 1] if i + 1 < len(split_points) else len(raw_text)
            block = raw_text[start:end].strip()
            # First line is the heading
            lines = block.splitlines()
            heading = lines[0].lstrip("#").strip() if lines else "Section"
            body = "\n".join(lines[1:]).strip()
            sections.append((heading, body))

    # Build chunk objects, merging tiny chunks into predecessor
    chunks: List[DocumentChunk] = []
    MIN_CHUNK_CHARS = 30

    for idx, (title, body) in enumerate(sections):
        text = body if body else title
        if len(text) < MIN_CHUNK_CHARS and chunks:
            # Append to previous chunk's content
            chunks[-1].content += f"\n\n{title}\n{text}"
        else:
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{doc_id}_chunk_{idx}",
                    doc_id=doc_id,
                    doc_filename=filename,
                    section_title=title,
                    content=text,
                )
            )

    return chunks


# ---------------------------------------------------------------------------
# Cosine similarity
# ---------------------------------------------------------------------------

def _cosine_similarity(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarity between a 1-D query vector and each row of a 2-D matrix.

    Returns a 1-D array of similarity scores in [−1, 1] with length == matrix.shape[0].
    Safe against zero-norm vectors (returns 0.0 similarity).
    """
    q_norm = np.linalg.norm(query_vec)
    if q_norm == 0.0:
        return np.zeros(matrix.shape[0], dtype=np.float32)

    row_norms = np.linalg.norm(matrix, axis=1)  # (N,)
    # Avoid division by zero for zero-norm document rows
    safe_norms = np.where(row_norms == 0.0, 1.0, row_norms)
    dot_products = matrix @ query_vec           # (N,)
    return (dot_products / (safe_norms * q_norm)).astype(np.float32)


# ---------------------------------------------------------------------------
# Main pipeline class
# ---------------------------------------------------------------------------

class RuleRetrievalPipeline:
    """
    Local RAG pipeline for retrieval of relevant rule documents and investigator guidance.

    Semantic path (GEMINI_API_KEY present):
        chunks → gemini-embedding-001 embeddings → NumPy cosine similarity → top-K

    Keyword fallback (no API key / embedding error):
        rule-ID direct match → keyword term-overlap count
    """

    def __init__(self, gemini_client: Any = None):
        """
        Parameters
        ----------
        gemini_client : google.genai.Client or None
            Injected at runtime from GeminiInvestigationService.
            If None, pipeline initialises in offline-fallback mode.
        """
        # Raw document store (dict list — backward compat with callers)
        self.documents: List[Dict[str, str]] = []

        # Chunk store
        self.chunks: List[DocumentChunk] = []

        # Embedding matrix — shape (N_chunks, embedding_dim), float32
        self._embedding_matrix: Optional[np.ndarray] = None

        # Whether embedding index has been built successfully
        self._index_ready: bool = False

        # Gemini client (may be set later by set_client())
        self._client = gemini_client

        # Load documents & chunks from disk
        self._load_documents()

    # ------------------------------------------------------------------
    # Public API: client injection
    # ------------------------------------------------------------------

    def set_client(self, client: Any) -> None:
        """Inject / replace the Gemini API client after construction."""
        self._client = client
        # Reset the index so it is rebuilt with the new client
        self._index_ready = False
        self._embedding_matrix = None

    # ------------------------------------------------------------------
    # Document loading
    # ------------------------------------------------------------------

    def _load_documents(self) -> None:
        """Load all *.md files from data/rules/ and build section-level chunks."""
        self.documents = []
        self.chunks = []

        md_files = sorted(glob.glob(os.path.join(RULES_DIR, "*.md")))
        for filepath in md_files:
            filename = os.path.basename(filepath)
            rule_id = (
                filename
                .replace("rule_", "")
                .replace(".md", "")
                .upper()
            )
            try:
                with open(filepath, "r", encoding="utf-8") as fh:
                    content = fh.read()
            except Exception as exc:
                print(f"[RAG] Warning: Could not read {filepath}: {exc}")
                continue

            # Legacy document record (whole file)
            self.documents.append({
                "id": rule_id,
                "filename": filename,
                "content": content,
            })

            # Section-level chunks
            doc_chunks = _chunk_document(rule_id, filename, content)
            self.chunks.extend(doc_chunks)

        print(f"[RAG] Loaded {len(self.documents)} documents, {len(self.chunks)} chunks from {RULES_DIR}")

    # ------------------------------------------------------------------
    # Embedding index build
    # ------------------------------------------------------------------

    def _build_embedding_index(self) -> bool:
        """
        Generate gemini-embedding-001 embeddings for all chunks and store in NumPy matrix.

        Returns True on success, False on any failure (triggers keyword fallback).
        """
        if not self._client:
            return False
        if not self.chunks:
            return False

        try:
            vectors: List[np.ndarray] = []
            for chunk in self.chunks:
                response = self._client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=chunk.content,
                )
                # The SDK returns an EmbedContentResponse; extract the values list
                embedding = response.embeddings[0].values  # list[float]
                vectors.append(np.array(embedding, dtype=np.float32))

            if not vectors:
                return False

            self._embedding_matrix = np.vstack(vectors)  # (N_chunks, dim)
            self._index_ready = True
            print(
                f"[RAG] Embedding index built: {self._embedding_matrix.shape[0]} chunks, "
                f"dim={self._embedding_matrix.shape[1]}"
            )
            return True

        except Exception as exc:
            print(f"[RAG] Embedding index build failed: {exc}. Using keyword fallback.")
            self._index_ready = False
            self._embedding_matrix = None
            return False

    # ------------------------------------------------------------------
    # Semantic retrieval (live path)
    # ------------------------------------------------------------------

    def embed_and_search(
        self,
        query: str,
        top_k: int = 4,
    ) -> List[Dict[str, str]]:
        """
        Semantic retrieval using gemini-embedding-001 and NumPy cosine similarity.

        Steps:
        1. Lazily build the chunk embedding index if not already built.
        2. Embed the query string with gemini-embedding-001.
        3. Compute cosine similarity against the stored chunk matrix.
        4. Return the top-K chunks as dicts (backward-compatible with prompt builder).

        Falls back to keyword retrieval on any error.
        """
        # Lazy index build
        if not self._index_ready:
            success = self._build_embedding_index()
            if not success:
                return self._keyword_retrieve([], query)

        # Embed the query
        try:
            response = self._client.models.embed_content(
                model="gemini-embedding-001",
                contents=query,
            )
            query_vec = np.array(
                response.embeddings[0].values, dtype=np.float32
            )
        except Exception as exc:
            print(f"[RAG] Query embedding failed: {exc}. Using keyword fallback.")
            return self._keyword_retrieve([], query)

        # Cosine similarity ranking
        similarities = _cosine_similarity(query_vec, self._embedding_matrix)
        # Top-K indices (descending)
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = [self.chunks[i].as_dict() for i in top_indices]
        print(
            f"[RAG] Semantic retrieval: top-{len(results)} chunks "
            f"(scores: {[round(float(similarities[i]), 3) for i in top_indices]})"
        )
        return results

    # ------------------------------------------------------------------
    # Keyword / rule-ID fallback (offline path)
    # ------------------------------------------------------------------

    def _keyword_retrieve(
        self,
        triggered_rule_ids: List[str],
        query: str,
    ) -> List[Dict[str, str]]:
        """
        Offline fallback: rule-ID direct match + keyword term-overlap count.
        Operates on whole documents (legacy behaviour), no external API calls.
        """
        results: List[Dict[str, str]] = []
        retrieved_ids: set = set()

        # 1. Direct rule-ID match
        for doc in self.documents:
            doc_id = doc["id"]
            if doc_id in triggered_rule_ids and doc_id not in retrieved_ids:
                results.append(doc)
                retrieved_ids.add(doc_id)

        # 2. Keyword term overlap for remaining docs
        query_terms = set(query.lower().split())
        for doc in self.documents:
            if doc["id"] not in retrieved_ids:
                doc_text = doc["content"].lower()
                matches = sum(1 for term in query_terms if term in doc_text)
                if matches >= 2 or "guidance" in doc["id"].lower():
                    results.append(doc)
                    retrieved_ids.add(doc["id"])

        # 3. Last resort: return master guidance if still empty
        if not results:
            for doc in self.documents:
                if "guidance" in doc["filename"].lower():
                    results.append(doc)

        return results

    # ------------------------------------------------------------------
    # Main public entry point (called by report_generator.py)
    # ------------------------------------------------------------------

    def retrieve_relevant_guidance(
        self,
        triggered_rule_ids: List[str],
        query: str = "",
    ) -> List[Dict[str, str]]:
        """
        Main retrieval entry point used by the live report pipeline.

        Decision logic:
        - If Gemini client available AND query is non-empty → semantic retrieval
          (embed_and_search), enriched with any directly triggered rule chunks.
        - Otherwise → keyword / rule-ID fallback (_keyword_retrieve).

        Always returns a list of dicts with keys: id, filename, content (± section).
        Never raises — on any error falls back to keyword retrieval.
        """
        # --- Semantic path ---
        if self._client and query.strip():
            try:
                semantic_results = self.embed_and_search(query=query, top_k=4)

                # Ensure any directly triggered rules are included even if they
                # scored lower in semantic ranking (exact match guarantee)
                semantic_ids = {r["id"] for r in semantic_results}
                for doc in self.documents:
                    if doc["id"] in triggered_rule_ids and doc["id"] not in semantic_ids:
                        semantic_results.append(doc)

                return semantic_results
            except Exception as exc:
                print(f"[RAG] Semantic path error: {exc}. Using keyword fallback.")

        # --- Offline keyword fallback ---
        return self._keyword_retrieve(triggered_rule_ids, query)


# ---------------------------------------------------------------------------
# Global singleton — client injected lazily by gemini_service.py
# ---------------------------------------------------------------------------
_pipeline: Optional[RuleRetrievalPipeline] = None


def get_rule_retrieval_pipeline(gemini_client: Any = None) -> RuleRetrievalPipeline:
    """
    Return the global singleton pipeline.

    If a gemini_client is supplied (first call from gemini_service), the
    client is injected so the embedding index can be built on next retrieval.
    Subsequent calls without a client reuse the existing singleton.
    """
    global _pipeline
    if _pipeline is None:
        _pipeline = RuleRetrievalPipeline(gemini_client=gemini_client)
    elif gemini_client is not None and not _pipeline._index_ready:
        _pipeline.set_client(gemini_client)
    return _pipeline
