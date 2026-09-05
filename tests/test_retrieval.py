"""
test_retrieval.py — Tests for the local semantic RAG pipeline.

Coverage:
  A. Chunking — rule documents split into section chunks with source metadata
  B. Cosine similarity — NumPy-based ranking
  C. Embedding retrieval — mocked Gemini, correct top chunks selected
  D. Offline fallback — retrieval still works with no API key / embedding error
  E. Existing report retrieval — retrieved docs reach the report generation path
"""

import types
import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_mock_client(vectors_per_call=None):
    """
    Build a minimal mock of google.genai.Client that satisfies
    client.models.embed_content(model=..., contents=...).

    vectors_per_call : list of list[float] | None
        If provided, successive calls return these vectors in order.
        After exhaustion, returns a zero vector of dim 8.
    """
    call_index = {"i": 0}
    default_dim = 8

    def embed_content(model, contents):
        idx = call_index["i"]
        if vectors_per_call and idx < len(vectors_per_call):
            vec = vectors_per_call[idx]
        else:
            vec = [0.0] * default_dim
        call_index["i"] += 1

        # Build a minimal response object
        EmbeddingVal = types.SimpleNamespace(values=vec)
        return types.SimpleNamespace(embeddings=[EmbeddingVal])

    models_ns = types.SimpleNamespace(embed_content=embed_content)
    client = types.SimpleNamespace(models=models_ns)
    return client


# ---------------------------------------------------------------------------
# A. Chunking tests
# ---------------------------------------------------------------------------

class TestChunking:
    def test_chunks_produced_from_rule_doc(self):
        """Each rule document should produce at least 2 chunks (intro + sections)."""
        from src.retrieval import _chunk_document
        text = """# Risk Rule R01: Unusually Large Transfer

## Purpose & Scope
This rule evaluates transaction amounts.

## Objective Evaluation Criteria
- Threshold: 5x median

## Investigator Guidance
1. Compare flagged transaction.
2. Do NOT mark as fraud solely on amount.
"""
        chunks = _chunk_document("R01", "rule_R01.md", text)
        assert len(chunks) >= 3, "Expected at least 3 section chunks"

    def test_chunk_retains_source_metadata(self):
        """Every chunk must carry its source doc_id and filename."""
        from src.retrieval import _chunk_document
        text = "# R02\n\n## Section A\nContent here.\n\n## Section B\nMore content here.\n"
        chunks = _chunk_document("R02", "rule_R02.md", text)
        for chunk in chunks:
            assert chunk.doc_id == "R02"
            assert chunk.doc_filename == "rule_R02.md"
            assert chunk.chunk_id.startswith("R02_chunk_")

    def test_chunk_section_title_extracted(self):
        """Section titles should be captured in section_title field or chunk content."""
        from src.retrieval import _chunk_document
        # Use a document with a substantial intro so it is not merged into the section.
        text = (
            "# Risk Rule R03: Odd-Hours Activity\n\n"
            "## Investigator Guidance\n"
            "1. Determine if odd-hours execution is accompanied by other risk signals.\n"
            "2. Check for international travel context or automated subscription charges.\n"
            "3. If executed via mobile banking in the middle of the night, elevate priority.\n"
        )
        chunks = _chunk_document("R03", "rule_R03.md", text)
        # Either the section_title contains the heading, or the content contains it
        all_text = " ".join(c.section_title + " " + c.content for c in chunks)
        assert "Investigator Guidance" in all_text

    def test_chunk_as_dict_has_required_keys(self):
        """as_dict() must return keys: id, filename, content."""
        from src.retrieval import _chunk_document
        text = "# R04\n\n## Purpose\nDetects deviations.\n"
        chunk = _chunk_document("R04", "rule_R04.md", text)[0]
        d = chunk.as_dict()
        assert "id" in d
        assert "filename" in d
        assert "content" in d

    def test_pipeline_loads_real_rule_files(self):
        """Integration: pipeline loads chunks from actual data/rules/ directory."""
        from src.retrieval import RuleRetrievalPipeline
        pipeline = RuleRetrievalPipeline(gemini_client=None)
        # Should have loaded the 5 .md files
        assert len(pipeline.documents) >= 4, "Expected at least R01–R04 documents"
        # Chunks should be more numerous than documents (sectioned)
        assert len(pipeline.chunks) > len(pipeline.documents)

    def test_tiny_chunks_merged_into_predecessor(self):
        """Chunks shorter than MIN_CHUNK_CHARS should be merged, not orphaned."""
        from src.retrieval import _chunk_document
        text = "# Rule\n\n## Limitations\nShort.\n\n## Long Section\n" + "Word " * 20 + "\n"
        chunks = _chunk_document("TEST", "test.md", text)
        # None of the chunks should be trivially short standalone text
        for chunk in chunks:
            assert len(chunk.content) >= 10, f"Chunk too short: {chunk!r}"


# ---------------------------------------------------------------------------
# B. Cosine similarity tests
# ---------------------------------------------------------------------------

class TestCosineSimilarity:
    def test_identical_vectors_score_one(self):
        from src.retrieval import _cosine_similarity
        v = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        matrix = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)
        scores = _cosine_similarity(v, matrix)
        assert abs(scores[0] - 1.0) < 1e-5

    def test_orthogonal_vectors_score_zero(self):
        from src.retrieval import _cosine_similarity
        v = np.array([1.0, 0.0], dtype=np.float32)
        matrix = np.array([[0.0, 1.0]], dtype=np.float32)
        scores = _cosine_similarity(v, matrix)
        assert abs(scores[0]) < 1e-5

    def test_ranking_order(self):
        """Closest vector should rank first."""
        from src.retrieval import _cosine_similarity
        query = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        matrix = np.array([
            [0.0, 1.0, 0.0],   # orthogonal — score ~ 0
            [1.0, 0.1, 0.0],   # close to query — score ~ high
            [0.5, 0.5, 0.0],   # intermediate
        ], dtype=np.float32)
        scores = _cosine_similarity(query, matrix)
        assert scores[1] > scores[2] > scores[0]

    def test_zero_query_vector_returns_zeros(self):
        from src.retrieval import _cosine_similarity
        v = np.zeros(4, dtype=np.float32)
        matrix = np.ones((3, 4), dtype=np.float32)
        scores = _cosine_similarity(v, matrix)
        assert np.all(scores == 0.0)

    def test_zero_doc_vector_safe(self):
        """A zero-norm document row must not cause division-by-zero."""
        from src.retrieval import _cosine_similarity
        v = np.array([1.0, 0.0], dtype=np.float32)
        matrix = np.array([[0.0, 0.0], [1.0, 0.0]], dtype=np.float32)
        scores = _cosine_similarity(v, matrix)
        assert scores[0] == pytest.approx(0.0, abs=1e-5)
        assert scores[1] == pytest.approx(1.0, abs=1e-5)


# ---------------------------------------------------------------------------
# C. Embedding retrieval tests (mocked Gemini)
# ---------------------------------------------------------------------------

class TestEmbeddingRetrieval:
    def _build_pipeline_with_mock(self, chunk_vecs, query_vec):
        """
        Build a pipeline whose chunks are already loaded from real files,
        then manually set its embedding matrix to chunk_vecs (as ndarray)
        and mark index ready.  The mock client will return query_vec for any
        embed_content call.
        """
        from src.retrieval import RuleRetrievalPipeline
        pipeline = RuleRetrievalPipeline(gemini_client=None)

        n_chunks = len(pipeline.chunks)
        # Pad/truncate chunk_vecs to match real chunk count
        dim = len(chunk_vecs[0]) if chunk_vecs else 4
        matrix = np.zeros((n_chunks, dim), dtype=np.float32)
        for i, v in enumerate(chunk_vecs):
            if i < n_chunks:
                matrix[i] = v

        pipeline._embedding_matrix = matrix
        pipeline._index_ready = True

        # Mock client returns query_vec on every embed_content call
        mock_client = _make_mock_client(vectors_per_call=[query_vec] * 20)
        pipeline._client = mock_client

        return pipeline

    def test_top_chunk_is_most_similar(self):
        """When query vec == chunk[0] vec, chunk[0] should be ranked first."""
        from src.retrieval import RuleRetrievalPipeline
        pipeline = RuleRetrievalPipeline(gemini_client=None)
        n_chunks = len(pipeline.chunks)
        assert n_chunks >= 2, "Need at least 2 chunks for this test"

        dim = 8
        # Make chunk 0 identical to the query; all others orthogonal
        matrix = np.zeros((n_chunks, dim), dtype=np.float32)
        matrix[0] = [1.0] + [0.0] * (dim - 1)

        pipeline._embedding_matrix = matrix
        pipeline._index_ready = True

        query_vec = [1.0] + [0.0] * (dim - 1)
        mock_client = _make_mock_client(vectors_per_call=[query_vec] * 20)
        pipeline._client = mock_client

        results = pipeline.embed_and_search("test query", top_k=2)
        assert len(results) >= 1
        # The first result should correspond to chunk 0's doc_id
        first_chunk_doc_id = pipeline.chunks[0].doc_id
        assert results[0]["id"] == first_chunk_doc_id

    def test_returns_top_k_results(self):
        """embed_and_search should return at most top_k chunks."""
        from src.retrieval import RuleRetrievalPipeline
        pipeline = RuleRetrievalPipeline(gemini_client=None)
        n_chunks = len(pipeline.chunks)
        dim = 4
        matrix = np.random.rand(n_chunks, dim).astype(np.float32)
        pipeline._embedding_matrix = matrix
        pipeline._index_ready = True

        query_vec = [0.5, 0.5, 0.5, 0.5]
        mock_client = _make_mock_client(vectors_per_call=[query_vec] * 5)
        pipeline._client = mock_client

        results = pipeline.embed_and_search("query", top_k=3)
        assert len(results) <= 3

    def test_retrieve_relevant_guidance_calls_semantic_path_when_client_set(self):
        """retrieve_relevant_guidance should use embedding when client is available."""
        from src.retrieval import RuleRetrievalPipeline
        pipeline = RuleRetrievalPipeline(gemini_client=None)
        n_chunks = len(pipeline.chunks)
        dim = 4
        matrix = np.ones((n_chunks, dim), dtype=np.float32)
        pipeline._embedding_matrix = matrix
        pipeline._index_ready = True

        query_vec = [1.0, 1.0, 1.0, 1.0]
        mock_client = _make_mock_client(vectors_per_call=[query_vec] * 20)
        pipeline._client = mock_client

        results = pipeline.retrieve_relevant_guidance(
            triggered_rule_ids=["R01"], query="large transfer amount baseline"
        )
        assert isinstance(results, list)
        assert len(results) >= 1
        for r in results:
            assert "id" in r
            assert "content" in r

    def test_index_build_called_lazily(self):
        """Index should be built on first embed_and_search call, not at init."""
        build_calls = {"n": 0}

        from src.retrieval import RuleRetrievalPipeline
        pipeline = RuleRetrievalPipeline(gemini_client=None)
        assert not pipeline._index_ready  # Should NOT be built at init without client

        # Now attach a mock client that supplies enough vectors for all chunks
        n_chunks = len(pipeline.chunks)
        dim = 4
        chunk_vecs = [[1.0, 0.0, 0.0, 0.0]] * n_chunks
        query_vec = [1.0, 0.0, 0.0, 0.0]
        all_vecs = chunk_vecs + [query_vec] * 5
        mock_client = _make_mock_client(vectors_per_call=all_vecs)
        pipeline.set_client(mock_client)

        # Index should still not be built until we call embed_and_search
        assert not pipeline._index_ready

        results = pipeline.embed_and_search("test", top_k=2)
        assert pipeline._index_ready
        assert isinstance(results, list)


# ---------------------------------------------------------------------------
# D. Offline fallback tests
# ---------------------------------------------------------------------------

class TestOfflineFallback:
    def test_no_client_uses_keyword_fallback(self):
        """Pipeline with no Gemini client must return results via keyword path."""
        from src.retrieval import RuleRetrievalPipeline
        pipeline = RuleRetrievalPipeline(gemini_client=None)
        results = pipeline.retrieve_relevant_guidance(
            triggered_rule_ids=["R01"], query="large transfer"
        )
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_r01_in_triggered_ids_returned_by_fallback(self):
        """Rule-ID direct match must return R01 doc when R01 is triggered."""
        from src.retrieval import RuleRetrievalPipeline
        pipeline = RuleRetrievalPipeline(gemini_client=None)
        results = pipeline._keyword_retrieve(["R01"], "")
        ids = [r["id"] for r in results]
        assert "R01" in ids

    def test_embedding_failure_falls_back_gracefully(self):
        """If embed_content raises, retrieval must not crash and must return results."""
        from src.retrieval import RuleRetrievalPipeline

        pipeline = RuleRetrievalPipeline(gemini_client=None)
        n_chunks = len(pipeline.chunks)
        # Simulate a broken embedding index
        pipeline._embedding_matrix = np.ones((n_chunks, 4), dtype=np.float32)
        pipeline._index_ready = True

        # Client that always raises
        def bad_embed(**kwargs):
            raise RuntimeError("Network error")

        bad_models = types.SimpleNamespace(embed_content=bad_embed)
        bad_client = types.SimpleNamespace(models=bad_models)
        pipeline._client = bad_client

        # Should not raise; falls back to keyword matching
        results = pipeline.retrieve_relevant_guidance(
            triggered_rule_ids=["R02"], query="new payee burst"
        )
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_empty_triggered_ids_and_empty_query_returns_guidance(self):
        """Even with no triggered IDs and empty query, master guidance is returned."""
        from src.retrieval import RuleRetrievalPipeline
        pipeline = RuleRetrievalPipeline(gemini_client=None)
        results = pipeline._keyword_retrieve([], "")
        # Should return the investigator guidance fallback
        assert len(results) >= 1

    def test_no_crash_when_rules_dir_has_files(self):
        """Pipeline initialisation must succeed and load documents without error."""
        from src.retrieval import RuleRetrievalPipeline
        pipeline = RuleRetrievalPipeline(gemini_client=None)
        assert len(pipeline.documents) > 0
        assert len(pipeline.chunks) > 0


# ---------------------------------------------------------------------------
# E. Report integration — retrieved docs reach report generation
# ---------------------------------------------------------------------------

class TestReportIntegration:
    def test_retrieved_docs_in_report(self):
        """
        End-to-end: the report pipeline must attach retrieved_rule_docs to the
        InvestigationReport even in offline (no-API-key) mode.
        """
        import pandas as pd
        from src.report_generator import analyze_transaction_history

        # Minimal CSV-like DataFrame: 5 historical + 1 current (clean, no risk)
        data = [
            {"transaction_id": f"TXN-H{i}", "date": "2026-08-01", "time": "10:00:00",
             "payee": "Supermart", "amount": 3000.0, "channel": "UPI", "is_historical": True}
            for i in range(5)
        ] + [
            {"transaction_id": "TXN-C1", "date": "2026-09-01", "time": "11:00:00",
             "payee": "Supermart", "amount": 3200.0, "channel": "UPI", "is_historical": False}
        ]
        df = pd.DataFrame(data)
        report = analyze_transaction_history(df)

        # Report must have the field (may be empty if no rules triggered and no guidance)
        assert hasattr(report, "retrieved_rule_docs")
        assert isinstance(report.retrieved_rule_docs, list)

    def test_retrieved_docs_in_report_with_risk(self):
        """
        When a rule fires, retrieved_rule_docs must contain at least one doc.
        Uses offline fallback (no GEMINI_API_KEY in test env).
        """
        import pandas as pd
        from src.report_generator import analyze_transaction_history

        data = [
            {"transaction_id": f"TXN-H{i}", "date": "2026-08-01", "time": "10:00:00",
             "payee": "Shop", "amount": 2000.0, "channel": "UPI", "is_historical": True}
            for i in range(5)
        ] + [
            {"transaction_id": "TXN-C1", "date": "2026-09-01", "time": "14:00:00",
             "payee": "NewVendor", "amount": 80000.0, "channel": "IMPS", "is_historical": False}
        ]
        df = pd.DataFrame(data)
        report = analyze_transaction_history(df)

        # R01 (large transfer) should fire, and retrieved docs should be non-empty
        rule_ids = [f.rule_id for f in report.rules_triggered]
        assert "R01" in rule_ids
        assert len(report.retrieved_rule_docs) >= 1

    def test_report_contains_evidence_citations(self):
        """
        The deterministic fallback report must contain [EVIDENCE: TXN-xxx] citations
        when rules are triggered.
        """
        import pandas as pd
        from src.report_generator import analyze_transaction_history

        data = [
            {"transaction_id": f"TXN-H{i}", "date": "2026-08-01", "time": "10:00:00",
             "payee": "GroceryStore", "amount": 1500.0, "channel": "UPI", "is_historical": True}
            for i in range(5)
        ] + [
            {"transaction_id": "TXN-FLAG", "date": "2026-09-01", "time": "02:00:00",
             "payee": "NightVendor", "amount": 90000.0, "channel": "IMPS", "is_historical": False}
        ]
        df = pd.DataFrame(data)
        report = analyze_transaction_history(df)

        assert "[EVIDENCE: TXN-FLAG]" in report.summary
