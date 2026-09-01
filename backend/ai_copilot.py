"""
TrustBridge AI Risk Analyst Copilot

Backend-only AI integration. Provides controlled, structured context to LLM
for explaining TrustBridge risk intelligence data.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import settings


@dataclass
class CopilotContext:
    """Structured context sent to the LLM."""
    user_query: str
    intent: str
    trust_data: Optional[Dict[str, Any]] = None
    transaction_data: Optional[List[Dict[str, Any]]] = None
    risk_events: Optional[List[Dict[str, Any]]] = None
    ml_explanation: Optional[Dict[str, Any]] = None
    payment_data: Optional[Dict[str, Any]] = None
    ledger_data: Optional[List[Dict[str, Any]]] = None
    model_metrics: Optional[Dict[str, Any]] = None
    comparison_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


class IntentClassifier:
    """Classify user intent to determine what context to fetch."""

    INTENT_KEYWORDS = {
        "trust_score": ["trust score", "trust", "reliability", "verdict", "components"],
        "fraud_flag": ["flagged", "fraud", "rule", "amount spike", "high risk transaction"],
        "ml_anomaly": ["anomaly", "ml", "isolation forest", "anomaly score", "model"],
        "payment_risk": ["payment", "risk assessment", "risk decision", "proceed", "reject", "flag"],
        "ledger": ["ledger", "debit", "credit", "balance", "double entry"],
        "user_profile": ["user", "profile", "raj", "priya", "anil", "identity"],
        "model_performance": ["precision", "recall", "f1", "accuracy", "evaluation", "metrics"],
        "rule_vs_ml": ["comparison", "rule vs ml", "both", "rule only", "ml only"],
        "explain_transaction": ["why", "explain", "reason", "contributing", "indicators"],
        "general": ["help", "what", "how", "difference", "summary"],
    }

    @classmethod
    def classify(cls, query: str) -> str:
        query_lower = query.lower()
        scores = {}
        for intent, keywords in cls.INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                scores[intent] = score
        if not scores:
            return "general"
        return max(scores, key=scores.get)


class ContextBuilder:
    """Build controlled context for the LLM based on user query and intent."""

    def __init__(self, session):
        self.session = session

    def build_context(self, query: str, user_id: Optional[int] = None,
                      transaction_id: Optional[int] = None,
                      payment_id: Optional[int] = None) -> CopilotContext:
        intent = IntentClassifier.classify(query)

        context = CopilotContext(user_query=query, intent=intent)

        # Fetch relevant data based on intent
        if intent in ("trust_score", "user_profile", "general") and user_id:
            context.trust_data = self._get_trust_data(user_id)

        if intent in ("trust_score", "user_profile", "fraud_flag", "ml_anomaly",
                      "explain_transaction", "general") and user_id:
            context.transaction_data = self._get_user_transactions(user_id, limit=20)

        if intent in ("fraud_flag", "ml_anomaly", "risk_events", "explain_transaction",
                      "rule_vs_ml", "model_performance") and user_id:
            context.risk_events = self._get_user_risk_events(user_id)

        if intent in ("ml_anomaly", "explain_transaction") and transaction_id:
            context.ml_explanation = self._get_ml_explanation(transaction_id)

        if intent in ("payment_risk", "ledger") and payment_id:
            context.payment_data = self._get_payment_data(payment_id)
            context.ledger_data = self._get_ledger_data(payment_id)

        if intent in ("model_performance", "general"):
            context.model_metrics = self._get_model_metrics()

        if intent in ("rule_vs_ml", "general"):
            context.comparison_data = self._get_comparison_data()

        return context

    def _get_trust_data(self, user_id: int) -> Dict[str, Any]:
        from engine.trust_score import calculate_trust_score
        from database.models import User
        user = self.session.query(User).filter(User.id == user_id).first()
        if not user:
            return {}
        trust_data = calculate_trust_score(user_id, self.session)
        return {
            "user_id": user_id,
            "user_name": user.name,
            "trust_score": trust_data["trust_score"],
            "verdict": trust_data.get("verdict", ""),
            "components": trust_data["components"],
        }

    def _get_user_transactions(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        from engine.trust_score import get_user_transactions
        from database.models import Transaction
        txns = get_user_transactions(user_id, self.session, limit=limit)
        return [
            {
                "id": t.id,
                "amount": float(t.amount) / 100.0,
                "type": t.transaction_type.value,
                "status": t.status.value,
                "merchant": t.merchant_name,
                "category": t.merchant_category,
                "city": t.location_city,
                "timestamp": t.timestamp.isoformat(),
                "is_anomaly": t.is_anomaly,
                "anomaly_type": t.anomaly_type,
            }
            for t in txns
        ]

    def _get_user_risk_events(self, user_id: int) -> List[Dict[str, Any]]:
        from engine.fraud_rules import get_flagged_transactions
        from engine.ml_fraud import score_all_transactions
        events = []

        # Rule-based flags
        flagged = get_flagged_transactions(user_id, self.session, multiplier=3.0)
        for f in flagged:
            events.append({
                "source": "rule",
                "transaction_id": f["transaction_id"],
                "amount": f["transaction_amount"],
                "risk_level": f["risk_level"],
                "reason": f["reason"],
                "ratio": f["ratio"],
            })

        # ML anomalies
        try:
            ml_results = score_all_transactions(user_id)
            for r in ml_results:
                if r["is_anomaly"]:
                    events.append({
                        "source": "ml",
                        "transaction_id": r["transaction_id"],
                        "amount": r["amount"] / 100.0,
                        "risk_level": r["risk_level"],
                        "anomaly_score": r["anomaly_score"],
                        "ground_truth": r["ground_truth_anomaly"],
                    })
        except Exception:
            pass

        return events

    def _get_ml_explanation(self, transaction_id: int) -> Dict[str, Any]:
        from engine.ml_fraud import explain_anomaly
        try:
            return explain_anomaly(transaction_id)
        except Exception:
            return {"error": "Could not generate explanation"}

    def _get_payment_data(self, payment_id: int) -> Dict[str, Any]:
        from database.models import PaymentTransaction
        payment = self.session.query(PaymentTransaction).filter(
            PaymentTransaction.id == payment_id
        ).first()
        if not payment:
            return {}
        return {
            "id": payment.id,
            "reference_id": payment.reference_id,
            "amount": float(payment.amount) / 100.0,
            "status": payment.status.value,
            "payment_method": payment.payment_method.value,
            "trust_score": payment.trust_score,
            "fraud_rule_flagged": payment.fraud_rule_flagged,
            "fraud_rule_reason": payment.fraud_rule_reason,
            "ml_anomaly_score": payment.ml_anomaly_score,
            "ml_is_anomaly": payment.ml_is_anomaly,
            "risk_policy_decision": payment.risk_policy_decision,
            "failure_reason": payment.failure_reason,
        }

    def _get_ledger_data(self, payment_id: int) -> List[Dict[str, Any]]:
        from database.models import LedgerEntry, TransactionType
        entries = self.session.query(LedgerEntry).filter(
            LedgerEntry.payment_transaction_id == payment_id
        ).all()
        return [
            {
                "account_id": e.account_id,
                "entry_type": e.entry_type.value,
                "amount": float(e.amount) / 100.0,
                "balance_after": float(e.balance_after) / 100.0,
                "description": e.description,
            }
            for e in entries
        ]

    def _get_model_metrics(self) -> Dict[str, Any]:
        from engine.ml_fraud import evaluate_model
        try:
            eval_result = evaluate_model()
            return {
                "precision": eval_result.get("precision", 0),
                "recall": eval_result.get("recall", 0),
                "f1": eval_result.get("f1", 0),
                "confusion_matrix": eval_result.get("confusion_matrix", []),
                "total_transactions": eval_result.get("total_transactions", 0),
                "true_anomalies": eval_result.get("true_anomalies", 0),
                "predicted_anomalies": eval_result.get("predicted_anomalies", 0),
                "anomalies_detected": eval_result.get("anomalies_detected", 0),
                "false_positives": eval_result.get("false_positives", 0),
                "false_negatives": eval_result.get("false_negatives", 0),
            }
        except Exception:
            return {"error": "Model evaluation unavailable"}

    def _get_comparison_data(self) -> Dict[str, Any]:
        from engine.ml_fraud import compare_rule_vs_ml
        try:
            return compare_rule_vs_ml()
        except Exception:
            return {"error": "Comparison unavailable"}


SYSTEM_PROMPT = """You are the TrustBridge AI Risk Analyst Copilot.

You help analysts understand financial trust scores, fraud detection results, and payment risk decisions.
You have access to structured TrustBridge data but MUST follow these rules:

CORE PRINCIPLES:
1. Trust Score ≠ Fraud Risk. Trust Score reflects long-term behavioural reliability. Fraud Risk evaluates individual transaction anomalies.
2. ML anomaly indicators are CONTRIBUTING INDICATORS, not causal explanations. Never say "X caused fraud."
3. All data is from a SYNTHETIC DEMO DATASET (399 transactions, 2 injected anomalies, 24 behavioural features).
4. Model is Isolation Forest (unsupervised). Evaluation is on injected anomalies only — not production performance.
5. Payment methods are SIMULATED (UPI_SIMULATED, BANK_TRANSFER_SIMULATED, WALLET_SIMULATED). No real money moves.

RESPONSE STYLE:
- Be precise, professional, and concise
- Reference actual data values from context
- Clearly distinguish: Trust Score components, Rule-based flags, ML anomaly scores
- When explaining anomalies, use "contributing anomaly indicators" not "causes"
- Disclose limitations: synthetic data, small sample, injected anomalies only
- If data is unavailable, say so — never fabricate

FORMAT:
- Use clear sections with headers
- Include specific numbers from context
- End with "Data source: TrustBridge synthetic demo dataset" when referencing data
"""


def build_messages(context: CopilotContext) -> List[Dict[str, str]]:
    """Build messages for the LLM API."""
    context_json = json.dumps(context.to_dict(), indent=2, default=str)

    user_message = f"""User Query: {context.user_query}

Structured Context (JSON):
{context_json}

Please analyze this TrustBridge data and answer the user's question. Follow the system prompt guidelines."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]


async def call_llm(messages: List[Dict[str, str]]) -> str:
    """Call the configured LLM provider."""
    if not settings.ai_configured:
        return ("AI Copilot unavailable — configure the server-side AI provider "
                "to enable analysis. Set AI_API_KEY in .env with a valid key "
                "for your chosen provider (openai, anthropic, google).")

    provider = settings.ai_provider.lower()

    try:
        if provider == "openai":
            return await _call_openai(messages)
        elif provider == "anthropic":
            return await _call_anthropic(messages)
        elif provider == "google":
            return await _call_google(messages)
        else:
            return f"Unsupported AI provider: {provider}"
    except Exception as e:
        return f"AI provider error: {type(e).__name__}. Check server logs for details."


async def _call_openai(messages: List[Dict[str, str]]) -> str:
    import httpx
    headers = {
        "Authorization": f"Bearer {settings.ai_api_key}",
        "Content-Type": "application/json",
    }
    base_url = settings.ai_base_url or "https://api.openai.com/v1"
    payload = {
        "model": settings.ai_model,
        "messages": messages,
        "max_tokens": settings.ai_max_tokens,
        "temperature": settings.ai_temperature,
    }
    async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
        response = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def _call_anthropic(messages: List[Dict[str, str]]) -> str:
    import httpx
    # Convert to Anthropic format
    system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
    user_msgs = [m for m in messages if m["role"] == "user"]
    headers = {
        "x-api-key": settings.ai_api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": settings.ai_model,
        "system": system_msg,
        "messages": user_msgs,
        "max_tokens": settings.ai_max_tokens,
        "temperature": settings.ai_temperature,
    }
    async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
        response = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]


async def _call_google(messages: List[Dict[str, str]]) -> str:
    import httpx
    # Convert to Google Gemini format
    combined = "\n\n".join(f"{m['role']}: {m['content']}" for m in messages)
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": combined}]}],
        "generationConfig": {
            "maxOutputTokens": settings.ai_max_tokens,
            "temperature": settings.ai_temperature,
        },
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.ai_model}:generateContent?key={settings.ai_api_key}"
    async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]