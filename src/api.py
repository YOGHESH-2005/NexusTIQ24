import os
import glob
import io
import json
import pandas as pd
from fastapi import APIRouter, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
from src.report_generator import analyze_transaction_history

router = APIRouter()

SCENARIOS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "scenarios")
RULES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "rules", "risk_rules.json")

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "TrustTrace AI — Transaction Risk Investigation Assistant",
        "version": "1.0.0",
        "track_id": "PS6"
    }

@router.get("/api/rules")
def get_rules():
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"rules": []}

@router.get("/api/sample-cases")
def list_sample_cases():
    scenarios = [
        {"id": "normal_customer", "name": "Normal Customer (Routine Activity)", "description": "Routine daytime transactions fitting historical baseline. Expected: NO ATTENTION REQUIRED."},
        {"id": "large_transfer", "name": "Large Transfer (R01 Signal)", "description": "Single transfer ₹185,000 exceeding historical median ₹14,200 (13.03x ratio). Expected: R01 Triggered."},
        {"id": "new_payee_burst", "name": "New Payee Burst (R02 Signal)", "description": "Rapid sequence of payments to unseen payee 'QuickMoney Services'. Expected: R02 Triggered."},
        {"id": "odd_hours", "name": "Odd-Hours Activity (R03 Signal)", "description": "High-value transfer executed at 03:17 AM outside normal hours window. Expected: R03 Triggered."},
        {"id": "behaviour_deviation", "name": "Behaviour Deviation (R04 Signal)", "description": "Multi-factor shift (IMPS wire at 03:00 AM for ₹150,000). Expected: R04 Triggered."},
        {"id": "multiple_rules", "name": "Multiple Risk Signals (R01 + R02 + R03)", "description": "High-value odd-hours burst to new payee. Expected: Multiple Rules Triggered & Priority Ranked."},
        {"id": "incomplete_data", "name": "Incomplete Data Edge Case", "description": "Missing payees and timestamps in raw input. Expected: Unknowns surfaced gracefully."},
        {"id": "contradictory_data", "name": "Contradictory Ledger Data Edge Case", "description": "Primary amount ₹50,000 conflicts with secondary ledger record ₹5,000. Expected: ESCALATE TO HUMAN."},
        {"id": "insufficient_history", "name": "Insufficient History Edge Case", "description": "Only 1 past transaction available. Expected: INSUFFICIENT EVIDENCE & Low Confidence."}
    ]
    return {"scenarios": scenarios}

@router.get("/api/sample-cases/{scenario_id}")
def analyze_sample_case(scenario_id: str):
    filepath = os.path.join(SCENARIOS_DIR, f"{scenario_id}.csv")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found.")
    
    try:
        df = pd.read_csv(filepath)
        report = analyze_transaction_history(df)
        return {
            "scenario_id": scenario_id,
            "filename": f"{scenario_id}.csv",
            "transaction_count": len(df),
            "report": report.model_dump(),
            "raw_transactions": df.fillna("").to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing scenario: {str(e)}")

@router.post("/api/analyze")
async def analyze_file(file: UploadFile = File(...)):
    filename = file.filename or "upload.csv"
    contents = await file.read()

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        elif filename.endswith(".json"):
            data = json.loads(contents.decode("utf-8"))
            df = pd.DataFrame(data if isinstance(data, list) else [data])
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload CSV or JSON.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse uploaded file: {str(e)}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        report = analyze_transaction_history(df)
        return {
            "filename": filename,
            "transaction_count": len(df),
            "report": report.model_dump(),
            "raw_transactions": df.fillna("").to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis pipeline error: {str(e)}")
