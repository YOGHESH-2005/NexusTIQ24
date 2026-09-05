import pandas as pd
from typing import List, Dict, Any
from src.validators import validate_and_normalize_data
from src.baseline import calculate_customer_baseline
from src.risk_engine import run_risk_engine
from src.retrieval import get_rule_retrieval_pipeline
from src.gemini_service import get_gemini_service
from src.models import InvestigationReport

def analyze_transaction_history(df: pd.DataFrame) -> InvestigationReport:
    """
    Complete end-to-end investigation pipeline:
    1. Validate input & normalize transactions
    2. Build customer historical baseline
    3. Run deterministic risk engine (R01, R02, R03, R04)
    4. Retrieve relevant rule knowledge base guidance via local RAG
    5. Generate evidence-grounded investigation report via Gemini (or fallback)
    """
    # Step 1: Input Validation
    transactions, validation = validate_and_normalize_data(df)

    # Step 2: Baseline Engine
    baseline = calculate_customer_baseline(transactions)

    # Step 3: Deterministic Risk Engine
    findings = run_risk_engine(transactions, baseline)

    # Step 4: Local RAG Retrieval
    triggered_rule_ids = [f.rule_id for f in findings]
    rag_pipeline = get_rule_retrieval_pipeline()
    retrieved_docs = rag_pipeline.retrieve_relevant_guidance(
        triggered_rule_ids=triggered_rule_ids, 
        query=" ".join([f.reason for f in findings])
    )

    # Step 5: Gemini Structured Report Synthesis
    svc = get_gemini_service()
    report = svc.generate_report(
        validation=validation,
        baseline=baseline,
        findings=findings,
        transactions=transactions,
        retrieved_docs=retrieved_docs
    )

    return report
