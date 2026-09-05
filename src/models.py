from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Transaction(BaseModel):
    transaction_id: str
    date: str
    time: str = ""
    description: str = ""
    payee: str = ""
    amount: float = 0.0
    channel: str = "UNKNOWN"
    is_historical: bool = True
    secondary_amount_record: Optional[float] = None
    flags: List[str] = Field(default_factory=list)

class CustomerBaseline(BaseModel):
    historical_count: int
    median_amount: float
    mean_amount: float
    min_amount: float
    max_amount: float
    percentile_95_amount: float
    typical_range_str: str
    active_hours_start: int = 8
    active_hours_end: int = 22
    active_hours_str: str = "08:00–22:00"
    common_channels: List[str] = Field(default_factory=list)
    common_payees: List[str] = Field(default_factory=list)
    avg_daily_transactions: float = 1.0
    baseline_confidence: str = "HIGH"  # HIGH, MEDIUM, LOW

class EvidenceItem(BaseModel):
    field: str
    value: str
    source: str = "transaction_history"

class RuleFinding(BaseModel):
    rule_id: str
    rule_name: str
    severity: str
    transaction_ids: List[str]
    reason: str
    ratio: Optional[float] = None
    evidence: List[EvidenceItem] = Field(default_factory=list)

class ValidationResult(BaseModel):
    is_valid: bool = True
    total_rows: int = 0
    historical_rows: int = 0
    current_rows: int = 0
    duplicate_ids: List[str] = Field(default_factory=list)
    missing_payees: List[str] = Field(default_factory=list)
    missing_amounts: List[str] = Field(default_factory=list)
    missing_timestamps: List[str] = Field(default_factory=list)
    contradictions: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class PriorityTransaction(BaseModel):
    rank: int
    transaction_id: str
    amount: float
    payee: str
    date_time: str
    reason: str
    triggered_rules: List[str]

class InvestigationReport(BaseModel):
    status: str  # NO_ATTENTION_REQUIRED | ATTENTION_REQUIRED | INSUFFICIENT_EVIDENCE | INVESTIGATOR_REVIEW_REQUIRED
    risk_level: str  # LOW | MEDIUM | HIGH | UNKNOWN
    summary: str
    rules_triggered: List[RuleFinding] = Field(default_factory=list)
    customer_baseline: CustomerBaseline
    priority_transactions: List[PriorityTransaction] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    recommended_investigator_action: str
    human_judgement_required: bool = True
    retrieved_rule_docs: List[Dict[str, str]] = Field(default_factory=list)
