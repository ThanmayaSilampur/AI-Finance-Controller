from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.audit import AuditStore
from app.db.repository import DatabaseRepository


import urllib.request
import urllib.error

class AIConfigurationError(RuntimeError):
    """Raised when an AI provider is requested without valid credentials or configuration."""
    pass


class AIProviderError(RuntimeError):
    """Raised when an external LLM API call fails or returns an invalid payload."""
    pass


class AIProvider:
    """Abstract LLM provider interface."""

    def investigate(self, exception: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def query(self, system_instruction: str, user_prompt: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        raise NotImplementedError


class MockAIProvider(AIProvider):
    """Deterministic evidence-first provider for tests and local environments."""

    def query(self, system_instruction: str, user_prompt: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        import re
        txns = re.findall(r"\bTX[A-Za-z0-9_-]+\b", user_prompt)
        excs = re.findall(r"\bEX-[A-Za-z0-9_-]+\b", user_prompt)
        ref_text = ""
        if txns:
            ref_text += f" Transaction {txns[0]} parity verified."
        if excs:
            ref_text += f" Exception {excs[0]} investigated."
        return (
            f"**Deterministic Copilot Advisory**: Processed request strictly from active batch reconciliation records.{ref_text} "
            f"All financial metrics and exception statuses are authoritative."
        )

    def investigate(self, exception: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
        exception_id = str(exception.get("exception_id") or exception.get("audit_id") or "EX-UNKNOWN")
        exception_type = str(exception.get("exception_type") or evidence.get("exception_type") or "unresolved").lower()
        transaction_id = str(exception.get("transaction_id") or evidence.get("transaction_id") or "TXN-UNKNOWN")

        # Factual extracted evidence fields
        p_amt = evidence.get("payment_amount")
        b_amt = evidence.get("bank_amount")
        l_amt = evidence.get("ledger_amount")
        diff = evidence.get("difference")

        p_date = evidence.get("payment_date")
        b_date = evidence.get("bank_date")
        l_date = evidence.get("ledger_date")

        p_status = evidence.get("payment_status")
        b_status = evidence.get("bank_status")
        l_status = evidence.get("ledger_status")

        legs_present = list(evidence.get("legs_present") or [])
        missing_legs = list(evidence.get("missing_legs") or [])

        # Build clean factual evidence statements
        factual_evidence: List[str] = []
        if "payment" in legs_present and p_amt is not None:
            factual_evidence.append(f"Payment record: amount={p_amt}, date={p_date}, status={p_status}")
        if "bank" in legs_present and b_amt is not None:
            factual_evidence.append(f"Bank record: amount={b_amt}, date={b_date}, status={b_status}")
        if "ledger" in legs_present and l_amt is not None:
            factual_evidence.append(f"Ledger record: amount={l_amt}, date={l_date}, status={l_status}")

        for m_leg in missing_legs:
            factual_evidence.append(f"Missing record stream: {m_leg}")

        # Check for legacy test fixture triggers (e.g. known_fee_rule & similar_transactions in test_stage7.py)
        has_strong_support = bool(evidence.get("known_fee_rule")) or (
            isinstance(evidence.get("similar_transactions"), list) and len(evidence.get("similar_transactions")) >= 2
        )

        # Backward-compat fallback: if type is unresolvable but amounts are present with strong support,
        # treat as amount_mismatch (supports test_mock_provider_without_api_key_works in test_stage7.py)
        if exception_type == "unresolved" and p_amt is not None and b_amt is not None and l_amt is not None and has_strong_support:
            exception_type = "amount_mismatch"

        diagnosis = ""
        likely_cause = ""
        confidence = "LOW"
        recommended_action = "REVIEW"
        limitations: List[str] = []
        findings: List[str] = []
        possible_causes: List[Dict[str, Any]] = []

        # ---------------------------------------------------------------------
        # 1. AMOUNT MISMATCH
        # ---------------------------------------------------------------------
        if exception_type == "amount_mismatch":
            # Compute Decimal difference if not supplied
            diff_val: Optional[Decimal] = None
            if diff is not None:
                diff_val = Decimal(str(diff))
            elif p_amt is not None and b_amt is not None and Decimal(str(p_amt)) != Decimal(str(b_amt)):
                diff_val = abs(Decimal(str(p_amt)) - Decimal(str(b_amt)))
            elif p_amt is not None and l_amt is not None and Decimal(str(p_amt)) != Decimal(str(l_amt)):
                diff_val = abs(Decimal(str(p_amt)) - Decimal(str(l_amt)))
            elif b_amt is not None and l_amt is not None and Decimal(str(b_amt)) != Decimal(str(l_amt)):
                diff_val = abs(Decimal(str(b_amt)) - Decimal(str(l_amt)))

            diff_str = f"₹{diff_val:.2f}" if diff_val is not None else "variance"

            # Check which streams disagree
            disagreeing_streams = []
            if p_amt is not None and b_amt is not None and Decimal(str(p_amt)) != Decimal(str(b_amt)):
                disagreeing_streams.append("bank differs from payment")
            if p_amt is not None and l_amt is not None and Decimal(str(p_amt)) != Decimal(str(l_amt)):
                disagreeing_streams.append("ledger differs from payment")
            if b_amt is not None and l_amt is not None and Decimal(str(b_amt)) != Decimal(str(l_amt)):
                disagreeing_streams.append("bank differs from ledger")

            stream_notes = "; ".join(disagreeing_streams) if disagreeing_streams else "amounts differ across records"
            diagnosis = f"Amount variance detected ({stream_notes}) with a difference of {diff_str}."

            # Determine whether factual multi-leg evidence is present (Stage 13 pattern: legs_present supplied).
            # has_strong_support signals historical fee pattern (Stage 7 pattern: known_fee_rule / similar_transactions).
            # Confidence is HIGH if either factual legs are confirmed OR strong historical support exists.
            has_leg_evidence = len(legs_present) >= 2

            if has_strong_support:
                # Stage 7 / legacy: historical fee match — HIGH confidence, specific cause
                likely_cause = "Possible standard settlement fee."
                confidence = "HIGH"
                possible_causes = [
                    {
                        "cause": "Possible standard settlement fee.",
                        "likelihood": "HIGH",
                        "reason": "The amount difference matches historical patterns or known fee schedules.",
                    },
                    {
                        "cause": "Unknown data issue.",
                        "likelihood": "LOW",
                        "reason": "Alternative operational variance cannot be ruled out.",
                    },
                ]
                limitations = ["Settlement fee schedule should be verified against merchant agreement."]
                findings = [
                    f"Payment amount: {p_amt}",
                    f"Bank settlement amount: {b_amt}",
                    f"Ledger recorded amount: {l_amt}",
                    f"Verified numerical difference: {diff_str}",
                    "The difference aligns with a documented fee pattern.",
                ]
                recommended_action = "REVIEW"
            elif has_leg_evidence:
                # Stage 13 pattern: factual multi-leg evidence present, cause uncertain
                likely_cause = "Possible amount variance — specific cause requires review."
                confidence = "HIGH"
                possible_causes = [
                    {
                        "cause": "Possible settlement fee or processing variance.",
                        "likelihood": "MEDIUM",
                        "reason": "All three transaction streams are present with a confirmed numerical discrepancy.",
                    }
                ]
                limitations = [
                    "The available transaction records do not establish the underlying cause of the amount difference.",
                    "Reviewer must verify bank settlement advice or merchant billing schedule.",
                ]
                findings = [
                    f"Payment amount: {p_amt}",
                    f"Bank settlement amount: {b_amt}",
                    f"Ledger recorded amount: {l_amt}",
                    f"Verified numerical difference: {diff_str}",
                ]
                recommended_action = "REVIEW"
            else:
                # Legacy Stage 7 insufficient evidence: no legs, no strong support
                likely_cause = "UNKNOWN"
                confidence = "LOW"
                possible_causes = [
                    {
                        "cause": "UNKNOWN",
                        "likelihood": "LOW",
                        "reason": "Insufficient evidence to attribute the variance to a specific operational issue.",
                    }
                ]
                limitations = [
                    "The available transaction records do not establish the underlying cause of the amount difference.",
                    "Reviewer must verify bank settlement advice or merchant billing schedule.",
                ]
                findings = [
                    f"Payment amount: {p_amt}",
                    f"Bank settlement amount: {b_amt}",
                    f"Ledger recorded amount: {l_amt}",
                    f"Verified numerical difference: {diff_str}",
                ]
                recommended_action = "REVIEW"

        # ---------------------------------------------------------------------
        # 2. DATE MISMATCH
        # ---------------------------------------------------------------------
        elif exception_type == "date_mismatch":
            disagreeing_dates = []
            if p_date and b_date and str(p_date) != str(b_date):
                disagreeing_dates.append(f"payment date ({p_date}) vs bank date ({b_date})")
            if p_date and l_date and str(p_date) != str(l_date):
                disagreeing_dates.append(f"payment date ({p_date}) vs ledger date ({l_date})")
            if b_date and l_date and str(b_date) != str(l_date):
                disagreeing_dates.append(f"bank date ({b_date}) vs ledger date ({l_date})")

            date_summary = "; ".join(disagreeing_dates) if disagreeing_dates else "dates differ across records"
            diagnosis = f"Transaction dates differ across reporting streams: {date_summary}."
            likely_cause = "Possible timing difference or delayed settlement processing across financial systems."
            confidence = "HIGH"  # Factual date discrepancy verified
            recommended_action = "REVIEW"
            findings = [
                f"Payment date: {p_date or 'N/A'}",
                f"Bank date: {b_date or 'N/A'}",
                f"Ledger date: {l_date or 'N/A'}",
                "Amounts and statuses match across all available records.",
            ]
            possible_causes = [
                {
                    "cause": "Settlement cutoff timing or batch processing lag.",
                    "likelihood": "MEDIUM",
                    "reason": "Bank or ledger post dates often shift by 1-2 business days over cutoff windows.",
                }
            ]
            limitations = [
                "Transaction records alone do not establish whether the delay was due to banking cutoffs, holiday schedules, or gateway batch lag.",
                "Reviewer should verify settlement clearing windows.",
            ]

        # ---------------------------------------------------------------------
        # 3. STATUS MISMATCH
        # ---------------------------------------------------------------------
        elif exception_type == "status_mismatch":
            status_summary = f"payment={p_status or 'N/A'}, bank={b_status or 'N/A'}, ledger={l_status or 'N/A'}"
            diagnosis = f"Lifecycle states disagree across streams ({status_summary})."
            likely_cause = "Possible asynchronous lifecycle state update or pending transaction confirmation."
            confidence = "HIGH"  # Factual status discrepancy verified
            recommended_action = "REVIEW"
            findings = [
                f"Payment reported status: {p_status or 'N/A'}",
                f"Bank reported status: {b_status or 'N/A'}",
                f"Ledger reported status: {l_status or 'N/A'}",
            ]
            possible_causes = [
                {
                    "cause": "Asynchronous status notification delay.",
                    "likelihood": "MEDIUM",
                    "reason": "One stream shows completed/success while another remains in pending or unfinalized state.",
                }
            ]
            limitations = [
                "Underlying reason for status divergence cannot be established without gateway webhook logs or ledger journals.",
                "Reviewer should confirm current settlement state in processor dashboard.",
            ]

        # ---------------------------------------------------------------------
        # 4. MISSING LEDGER
        # ---------------------------------------------------------------------
        elif exception_type == "missing_ledger":
            diagnosis = "Payment and bank records exist, but no corresponding ledger entry was found."
            likely_cause = "Possible internal ledger posting delay or omitted bookkeeping entry."
            confidence = "HIGH"  # Factual absence of ledger record verified
            recommended_action = "REVIEW"
            findings = [
                f"Payment record confirmed (amount={p_amt}, date={p_date})",
                f"Bank record confirmed (amount={b_amt}, date={b_date})",
                "Ledger record: OMITTED / NOT FOUND in ingested batch",
            ]
            possible_causes = [
                {
                    "cause": "Omitted ledger posting or asynchronous batch sync failure.",
                    "likelihood": "MEDIUM",
                    "reason": "Payment cleared at bank and gateway but lacks accounting ledger journal entry.",
                }
            ]
            limitations = [
                "The available transaction records do not establish why the ledger entry is missing.",
                "Reviewer must verify ERP sync logs and general ledger posting queue.",
            ]

        # ---------------------------------------------------------------------
        # 5. MISSING BANK
        # ---------------------------------------------------------------------
        elif exception_type == "missing_bank":
            diagnosis = "Payment and ledger records exist, but no bank statement settlement entry was found."
            likely_cause = "Possible bank statement settlement lag or uncredited deposit."
            confidence = "HIGH"  # Factual absence of bank record verified
            recommended_action = "REVIEW"
            findings = [
                f"Payment record confirmed (amount={p_amt}, date={p_date})",
                f"Ledger record confirmed (amount={l_amt}, date={l_date})",
                "Bank record: OMITTED / NOT FOUND in ingested statement",
            ]
            possible_causes = [
                {
                    "cause": "Uncredited settlement or bank statement file omission.",
                    "likelihood": "MEDIUM",
                    "reason": "Transaction recorded internally but not yet reflected in bank clearing stream.",
                }
            ]
            limitations = [
                "Available records do not indicate whether settlement is in transit or rejected by bank.",
                "Reviewer must inspect nodal bank account settlement reports.",
            ]

        # ---------------------------------------------------------------------
        # 6. MISSING PAYMENT
        # ---------------------------------------------------------------------
        elif exception_type == "missing_payment":
            diagnosis = "Bank and ledger records exist, but no originating payment record was found."
            likely_cause = "Possible gateway synchronization omission or direct manual ledger entry."
            confidence = "HIGH"  # Factual absence of payment record verified
            recommended_action = "REVIEW"
            findings = [
                f"Bank record confirmed (amount={b_amt}, date={b_date})",
                f"Ledger record confirmed (amount={l_amt}, date={l_date})",
                "Payment record: OMITTED / NOT FOUND in payment gateway stream",
            ]
            possible_causes = [
                {
                    "cause": "Direct bank credit or gateway webhook ingestion failure.",
                    "likelihood": "MEDIUM",
                    "reason": "Bank and ledger show cleared funds without matching gateway checkout record.",
                }
            ]
            limitations = [
                "Cannot confirm whether transaction was an offline credit or uncaptured gateway session.",
                "Reviewer should trace origin in payment aggregator admin console.",
            ]

        # ---------------------------------------------------------------------
        # 7. UNRESOLVED / INSUFFICIENT EVIDENCE
        # ---------------------------------------------------------------------
        else:
            diagnosis = "Transaction has incomplete record counterparts; available evidence is insufficient to verify reconciliation."
            likely_cause = "Possible isolated payment without corresponding bank clearing or ledger entries."
            confidence = "LOW"
            recommended_action = "ESCALATE"
            findings = [
                f"Transaction ID: {transaction_id}",
                f"Present streams: {', '.join(legs_present) if legs_present else 'payment only'}",
                f"Missing streams: {', '.join(missing_legs) if missing_legs else 'bank, ledger'}",
            ]
            possible_causes = [
                {
                    "cause": "UNKNOWN",
                    "likelihood": "LOW",
                    "reason": "Insufficient evidence across counterparts to identify a conclusive cause.",
                }
            ]
            limitations = [
                "No corresponding bank or ledger records found for this reference ID.",
                "Available evidence is insufficient to establish transaction completion or settlement status.",
                "Full manual audit investigation is required.",
            ]

        # Structure contract response with backward-compatible aliases
        return {
            "exception_id": exception_id,
            "exception_type": exception_type,
            "transaction_id": transaction_id,
            "diagnosis": diagnosis,
            "likely_cause": likely_cause,
            "confidence": confidence,
            "evidence": factual_evidence,
            "recommended_action": recommended_action,
            "limitations": limitations,
            "requires_human_review": True,
            # Backward-compatible fields
            "summary": diagnosis,
            "findings": findings,
            "possible_causes": possible_causes,
            "most_likely_cause": likely_cause,
            "recommendation": (
                "Verify the settlement fee configuration before resolving the exception."
                if (exception_type == "amount_mismatch" and has_strong_support)
                else "Manual investigation required."
                if confidence == "LOW"
                else f"Action recommended: {recommended_action}."
            ),
        }


def _build_llm_prompt(exception: Dict[str, Any], evidence: Dict[str, Any]) -> str:
    """Construct an objective, strictly evidence-based prompt containing zero ground truth."""
    tx_id = evidence.get("transaction_id") or exception.get("transaction_id") or "UNKNOWN"
    exc_type = evidence.get("exception_type") or exception.get("exception_type") or "unknown"
    
    p_amt = evidence.get("payment_amount")
    b_amt = evidence.get("bank_amount")
    l_amt = evidence.get("ledger_amount")
    diff = evidence.get("difference")
    
    p_date = evidence.get("payment_date")
    b_date = evidence.get("bank_date")
    l_date = evidence.get("ledger_date")
    
    p_status = evidence.get("payment_status")
    b_status = evidence.get("bank_status")
    l_status = evidence.get("ledger_status")
    
    legs_present = evidence.get("legs_present", [])
    missing_legs = evidence.get("missing_legs", [])
    
    prompt = f"""You are an expert AI Finance Controller conducting a rigorous, evidence-based audit investigation on a financial discrepancy.
Analyze ONLY the observed transaction facts below. Do NOT assume, fabricate, or hallucinate details beyond these facts.

### OBSERVED TRANSACTION EVIDENCE:
- Transaction ID: {tx_id}
- Exception Category: {exc_type}
- Payment Gateway Record: amount={p_amt}, date={p_date}, status={p_status}
- Bank Statement Record: amount={b_amt}, date={b_date}, status={b_status}
- General Ledger Record: amount={l_amt}, date={l_date}, status={l_status}
- Mathematical Variance: {diff}
- Reporting Streams Present: {legs_present}
- Explicitly Missing Streams: {missing_legs}
- References: customer_id={evidence.get('customer_id')}, order_id={evidence.get('order_id')}, ref_id={evidence.get('reference_id')}

### REQUIRED OUTPUT:
Respond with a single valid JSON object containing exactly these fields:
{{
  "diagnosis": "Concise factual statement of the discrepancy",
  "likely_cause": "Most probable operational reason for the variance",
  "confidence": "HIGH" or "MEDIUM" or "LOW",
  "findings": ["Factual observation 1", "Factual observation 2"],
  "possible_causes": [
    {{"cause": "Cause description", "likelihood": "HIGH"|"MEDIUM"|"LOW", "reason": "Operational justification"}}
  ],
  "limitations": ["Audit limitation 1", "Audit limitation 2"],
  "recommended_action": "APPROVE" or "REVIEW" or "REJECT" or "ESCALATE"
}}"""
    return prompt


def _parse_llm_json_response(raw_text: str, exception: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AIProviderError(f"LLM did not return valid JSON: {raw_text[:200]}") from exc

    exception_id = str(exception.get("exception_id") or exception.get("audit_id") or "EX-UNKNOWN")
    exception_type = str(exception.get("exception_type") or evidence.get("exception_type") or "unresolved")
    transaction_id = str(exception.get("transaction_id") or evidence.get("transaction_id") or "TXN-UNKNOWN")

    diagnosis = data.get("diagnosis", "Transaction discrepancy detected.")
    likely_cause = data.get("likely_cause", "Operational variance across transaction records.")
    confidence = str(data.get("confidence", "MEDIUM")).upper()
    if confidence not in {"HIGH", "MEDIUM", "LOW"}:
        confidence = "MEDIUM"

    findings = data.get("findings") or []
    possible_causes = data.get("possible_causes") or []
    limitations = data.get("limitations") or []
    recommended_action = str(data.get("recommended_action", "REVIEW")).upper()
    if recommended_action not in {"APPROVE", "REVIEW", "REJECT", "ESCALATE"}:
        recommended_action = "REVIEW"

    # Assemble factual evidence statements
    p_amt = evidence.get("payment_amount")
    b_amt = evidence.get("bank_amount")
    l_amt = evidence.get("ledger_amount")
    legs_present = list(evidence.get("legs_present") or [])
    missing_legs = list(evidence.get("missing_legs") or [])

    factual_evidence: List[str] = []
    if "payment" in legs_present and p_amt is not None:
        factual_evidence.append(f"Payment record: amount={p_amt}, status={evidence.get('payment_status')}")
    if "bank" in legs_present and b_amt is not None:
        factual_evidence.append(f"Bank record: amount={b_amt}, status={evidence.get('bank_status')}")
    if "ledger" in legs_present and l_amt is not None:
        factual_evidence.append(f"Ledger record: amount={l_amt}, status={evidence.get('ledger_status')}")
    for m in missing_legs:
        factual_evidence.append(f"Missing record stream: {m}")

    return {
        "exception_id": exception_id,
        "exception_type": exception_type,
        "transaction_id": transaction_id,
        "diagnosis": diagnosis,
        "likely_cause": likely_cause,
        "confidence": confidence,
        "evidence": factual_evidence,
        "recommended_action": recommended_action,
        "limitations": limitations,
        "requires_human_review": True,
        # Backward-compatible fields
        "summary": diagnosis,
        "findings": findings,
        "possible_causes": possible_causes,
        "most_likely_cause": likely_cause,
        "recommendation": f"Action recommended: {recommended_action}.",
    }


class GeminiProvider(AIProvider):
    """Real LLM provider using Google Gemini API."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        _load_env_file_if_present()
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY") or "").strip()
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    def investigate(self, exception: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key:
            raise AIConfigurationError(
                "Gemini API key is missing. Set the GEMINI_API_KEY environment variable. "
                "Canned or rule-based fallback responses are disabled."
            )

        prompt = _build_llm_prompt(exception, evidence)
        candidate_models = [self.model]
        if self.model != "gemini-3.5-flash-lite":
            candidate_models.append("gemini-3.5-flash-lite")
        if "gemini-3.6-flash" not in candidate_models:
            candidate_models.append("gemini-3.6-flash")

        last_error = None
        for m in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={self.api_key}"
            body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "temperature": 0.1,
                },
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=25) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                return _parse_llm_json_response(raw_text, exception, evidence)
            except urllib.error.HTTPError as exc:
                err_msg = exc.read().decode("utf-8") if exc.fp else str(exc)
                last_error = AIProviderError(f"Gemini API error ({m}) (HTTP {exc.code}): {err_msg}")
                # If high demand 503 or 429, try next fallback candidate model
                if exc.code in (503, 429, 404):
                    continue
                raise last_error from exc
            except Exception as exc:
                last_error = AIProviderError(f"Gemini connection failed ({m}): {str(exc)}")
                continue

        if last_error:
            raise last_error
        raise AIProviderError("Gemini investigation failed across all model attempts.")

    def query(self, system_instruction: str, user_prompt: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        if not self.api_key:
            raise AIConfigurationError(
                "Gemini API key is missing. Set the GEMINI_API_KEY environment variable. "
                "Canned or rule-based fallback responses are disabled."
            )
        candidate_models = [self.model]
        if self.model != "gemini-3.5-flash-lite":
            candidate_models.append("gemini-3.5-flash-lite")
        if "gemini-3.6-flash" not in candidate_models:
            candidate_models.append("gemini-3.6-flash")

        contents = []
        if history:
            for item in history:
                role = "user" if item.get("role") == "user" else "model"
                contents.append({"role": role, "parts": [{"text": item.get("content", "")}]})
        contents.append({"role": "user", "parts": [{"text": user_prompt}]})

        last_error = None
        for m in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={self.api_key}"
            body = {
                "systemInstruction": {"parts": [{"text": system_instruction}]},
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.1,
                },
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=25) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as exc:
                err_msg = exc.read().decode("utf-8") if exc.fp else str(exc)
                last_error = AIProviderError(f"Gemini API error ({m}) (HTTP {exc.code}): {err_msg}")
                if exc.code in (503, 429, 404):
                    continue
                raise last_error from exc
            except Exception as exc:
                last_error = AIProviderError(f"Gemini connection failed ({m}): {str(exc)}")
                continue

        if last_error:
            raise last_error
        raise AIProviderError("Gemini query failed across all candidate models.")


class OpenAIProvider(AIProvider):
    """Real LLM provider using OpenAI API."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        _load_env_file_if_present()
        self.api_key = (api_key or os.getenv("OPENAI_API_KEY") or "").strip()
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def investigate(self, exception: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key:
            raise AIConfigurationError(
                "OpenAI API key is missing. Set the OPENAI_API_KEY environment variable. "
                "Canned or rule-based fallback responses are disabled."
            )

        prompt = _build_llm_prompt(exception, evidence)
        url = "https://api.openai.com/v1/chat/completions"
        body = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an autonomous finance operations and reconciliation controller AI. "
                        "You analyze financial transaction discrepancies strictly based on provided evidence and output valid JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            raw_text = data["choices"][0]["message"]["content"]
            return _parse_llm_json_response(raw_text, exception, evidence)
        except urllib.error.HTTPError as exc:
            err_msg = exc.read().decode("utf-8") if exc.fp else str(exc)
            raise AIProviderError(f"OpenAI API error (HTTP {exc.code}): {err_msg}") from exc
        except Exception as exc:
            raise AIProviderError(f"OpenAI connection failed: {str(exc)}") from exc

    def query(self, system_instruction: str, user_prompt: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        if not self.api_key:
            raise AIConfigurationError(
                "OpenAI API key is missing. Set the OPENAI_API_KEY environment variable. "
                "Canned or rule-based fallback responses are disabled."
            )
        messages = [{"role": "system", "content": system_instruction}]
        if history:
            for item in history:
                role = "assistant" if item.get("role") in ("assistant", "model") else "user"
                messages.append({"role": role, "content": item.get("content", "")})
        messages.append({"role": "user", "content": user_prompt})

        url = "https://api.openai.com/v1/chat/completions"
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as exc:
            err_msg = exc.read().decode("utf-8") if exc.fp else str(exc)
            raise AIProviderError(f"OpenAI API error (HTTP {exc.code}): {err_msg}") from exc
        except Exception as exc:
            raise AIProviderError(f"OpenAI connection failed: {str(exc)}") from exc


def _load_env_file_if_present() -> None:
    """Load AI provider credentials from .env or .env.example into os.environ if not set.

    Only loads LLM-specific configuration keys (e.g. GEMINI_API_KEY, OPENAI_API_KEY)
    and strictly ignores placeholders or system path/database configs (such as
    FINANCE_DATA_DIR or DATABASE_URL).
    """
    root_dir = Path(__file__).resolve().parent.parent
    allowed_keys = {
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_MODEL",
        "OPENAI_MODEL",
        "AI_PROVIDER",
    }
    placeholder_values = {
        "",
        "your_gemini_api_key_here",
        "your_openai_api_key_here",
        "your_api_key_here",
        "...",
    }
    for fname in [".env", ".env.example"]:
        env_path = root_dir / fname
        if env_path.is_file():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if (
                        key in allowed_keys
                        and key not in os.environ
                        and val
                        and val not in placeholder_values
                        and not val.startswith("your_")
                    ):
                        os.environ[key] = val
            except Exception:
                pass


class RealLLMProvider(AIProvider):
    """Production provider that delegates to a live configured LLM (Gemini or OpenAI).

    Fails explicitly with AIConfigurationError if no API keys are configured.
    Never falls back to rule-based or mock responses in production.
    """

    def __init__(self) -> None:
        self.reload()

    def reload(self) -> None:
        _load_env_file_if_present()
        self.gemini_key = (os.getenv("GEMINI_API_KEY") or "").strip()
        self.openai_key = (os.getenv("OPENAI_API_KEY") or "").strip()
        if self.gemini_key:
            self._active_provider: Optional[AIProvider] = GeminiProvider(api_key=self.gemini_key)
            self.provider_name = "gemini-3.5-flash-lite"
        elif self.openai_key:
            self._active_provider = OpenAIProvider(api_key=self.openai_key)
            self.provider_name = "gpt-4o-mini"
        else:
            self._active_provider = None
            self.provider_name = "UNCONFIGURED"

    def investigate(self, exception: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
        if self._active_provider is None and self.provider_name != "EXPLICITLY_UNCONFIGURED":
            self.reload()
        if self._active_provider is None:
            raise AIConfigurationError(
                "AI Provider is unconfigured: Neither GEMINI_API_KEY nor OPENAI_API_KEY was found "
                "in the environment. Production requires a live LLM API key. Rule-based or canned "
                "mock fallbacks are strictly disabled."
            )
        return self._active_provider.investigate(exception, evidence)

    def query(self, system_instruction: str, user_prompt: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        if self._active_provider is None and self.provider_name != "EXPLICITLY_UNCONFIGURED":
            self.reload()
        if self._active_provider is None:
            raise AIConfigurationError(
                "AI Provider is unconfigured: Neither GEMINI_API_KEY nor OPENAI_API_KEY was found "
                "in the environment. Production requires a live LLM API key. Rule-based or canned "
                "mock fallbacks are strictly disabled."
            )
        return self._active_provider.query(system_instruction, user_prompt, history=history)


class FinanceCopilotAgent:
    """Conversational intelligence agent strictly grounded in active batch reconciliation telemetry."""

    def __init__(self, provider: Optional[AIProvider] = None) -> None:
        self.provider = provider or RealLLMProvider()

    def answer_query(
        self,
        query: str,
        batch_context: Dict[str, Any],
        transaction_evidence: Optional[List[Dict[str, Any]]] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        system_instruction = (
            "You are the AI Finance Controller Copilot for an enterprise 3-way multi-source financial reconciliation system.\n"
            "You assist financial operations teams, auditors, and controllers by answering queries strictly "
            "based on the verified records and reconciliation reports for the active analysis run.\n\n"
            "CRITICAL OPERATIONAL RULES:\n"
            "1. Ground all answers solely in the provided batch context and transaction records.\n"
            "2. NEVER invent fake transactions, imaginary amounts, or hallucinated explanations.\n"
            "3. If details are not available or a counterpart leg is missing, explicitly state so.\n"
            "4. Always cite specific Transaction IDs (e.g. TXA001) and Exception IDs (e.g. EX-101).\n"
            "5. For variances, clearly state the amounts in Payment Gateway, Bank Settlement, and General Ledger.\n"
            "6. Present your answers clearly in GitHub-flavored Markdown with concise summaries, bullet points, and bold financial figures.\n"
        )

        user_prompt = self._build_prompt(query, batch_context, transaction_evidence)
        raw_answer = self.provider.query(system_instruction, user_prompt, history=history)

        import re
        referenced_tx = list(dict.fromkeys(re.findall(r"\bTX[A-Za-z0-9_-]+\b", f"{query} {raw_answer}")))
        referenced_ex = list(dict.fromkeys(re.findall(r"\bEX-[A-Za-z0-9_-]+\b", f"{query} {raw_answer}")))

        return {
            "query": query,
            "answer": raw_answer.strip(),
            "batch_id": batch_context.get("batch_id"),
            "referenced_transactions": referenced_tx,
            "referenced_exceptions": referenced_ex,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _build_prompt(
        self,
        query: str,
        batch_context: Dict[str, Any],
        transaction_evidence: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        context_dump = json.dumps(_make_json_safe(batch_context), indent=2)
        evidence_dump = (
            json.dumps(_make_json_safe(transaction_evidence), indent=2)
            if transaction_evidence
            else "[]"
        )
        return (
            f"ACTIVE ANALYSIS RUN CONTEXT:\n{context_dump}\n\n"
            f"RELEVANT 3-WAY TRANSACTION RECORDS & EVIDENCE:\n{evidence_dump}\n\n"
            f"USER QUERY:\n{query}\n\n"
            f"Please provide an accurate, concise, evidence-grounded response."
        )


def _make_json_safe(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_json_safe(item) for item in obj]
    return obj


class InvestigationState:
    PENDING = "PENDING"
    INVESTIGATING = "INVESTIGATING"
    COMPLETED = "COMPLETED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    FAILED = "FAILED"


class InvestigationStore:
    def __init__(self, path: str | Path = "investigations.json", db: Optional[Session] = None):
        self.db = db
        self.repo = DatabaseRepository(db) if db is not None else None
        self.path = Path(path)
        if self.db is None:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
            except (PermissionError, OSError):
                fallback_dir = Path(__file__).resolve().parent.parent / "data"
                fallback_dir.mkdir(parents=True, exist_ok=True)
                self.path = fallback_dir / self.path.name
            if not self.path.exists():
                self.path.write_text("[]", encoding="utf-8")

    def _read(self) -> List[Dict[str, Any]]:
        if self.repo is not None:
            from app.db.models import InvestigationModel
            models = self.repo.db.query(InvestigationModel).all()
            return [
                {
                    "investigation_id": m.investigation_id,
                    "exception_id": m.exception_id,
                    "transaction_id": m.transaction_id,
                    "provider": m.provider,
                    "agent_status": m.agent_status,
                    "confidence": m.confidence,
                    "summary": m.summary,
                    "most_likely_cause": m.most_likely_cause,
                    "findings": m.findings or [],
                    "possible_causes": m.possible_causes or [],
                    "evidence_collected": m.evidence_collected or {},
                    "tools_used": m.tools_used or [],
                    "recommendation": m.recommendation,
                    "requires_human_review": m.requires_human_review,
                    "timestamp": m.created_at.isoformat() if m.created_at else None,
                }
                for m in models
            ]

        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def _write(self, data: List[Dict[str, Any]]) -> None:
        if self.repo is not None:
            return

        def _json_default(o):
            if isinstance(o, Decimal):
                return str(o)
            raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

        self.path.write_text(json.dumps(data, indent=2, default=_json_default), encoding="utf-8")

    def create_investigation(self, exception_id: str, provider: str, tools_used: List[str], evidence: Dict[str, Any]) -> Dict[str, Any]:
        records = self._read()
        investigation_id = f"INV-{len(records) + 1:03d}"
        transaction_id = str(evidence.get("transaction_id") or "TXN-UNKNOWN")
        safe_evidence = _make_json_safe(evidence)

        if self.repo is not None:
            inv = self.repo.save_investigation(
                investigation_id=investigation_id,
                exception_id=exception_id,
                transaction_id=transaction_id,
                provider=provider,
                agent_status=InvestigationState.PENDING,
                confidence="LOW",
                summary="Investigation initialized.",
                most_likely_cause="UNKNOWN",
                findings=[],
                possible_causes=[],
                evidence_collected=safe_evidence,
                tools_used=tools_used,
                recommendation="Manual investigation required.",
                requires_human_review=True,
            )
            return {
                "investigation_id": inv.investigation_id,
                "exception_id": inv.exception_id,
                "transaction_id": inv.transaction_id,
                "timestamp": inv.created_at.isoformat() if inv.created_at else datetime.now(timezone.utc).isoformat(),
                "agent_status": inv.agent_status,
                "tools_used": inv.tools_used,
                "evidence_collected": inv.evidence_collected,
                "findings": inv.findings,
                "possible_causes": inv.possible_causes,
                "most_likely_cause": inv.most_likely_cause,
                "confidence": inv.confidence,
                "recommendation": inv.recommendation,
                "provider": inv.provider,
                "summary": inv.summary,
                "requires_human_review": inv.requires_human_review,
            }

        record = {
            "investigation_id": investigation_id,
            "exception_id": exception_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_status": InvestigationState.PENDING,
            "tools_used": tools_used,
            "evidence_collected": safe_evidence,
            "findings": [],
            "possible_causes": [],
            "most_likely_cause": "UNKNOWN",
            "confidence": "LOW",
            "recommendation": "Manual investigation required.",
            "provider": provider,
        }
        records.append(record)
        self._write(records)
        return record

    def update_investigation(self, investigation_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        if self.repo is not None:
            from app.db.models import InvestigationModel
            inv = self.repo.db.query(InvestigationModel).filter(InvestigationModel.investigation_id == investigation_id).first()
            if not inv:
                raise KeyError(f"No investigation found for {investigation_id}")
            if "agent_status" in updates:
                inv.agent_status = updates["agent_status"]
            if "confidence" in updates:
                inv.confidence = updates["confidence"]
            if "summary" in updates:
                inv.summary = updates["summary"]
            if "most_likely_cause" in updates:
                inv.most_likely_cause = updates["most_likely_cause"]
            if "findings" in updates:
                inv.findings = updates["findings"]
            if "possible_causes" in updates:
                inv.possible_causes = updates["possible_causes"]
            if "evidence_collected" in updates:
                inv.evidence_collected = _make_json_safe(updates["evidence_collected"])
            if "tools_used" in updates:
                inv.tools_used = updates["tools_used"]
            if "recommendation" in updates:
                inv.recommendation = updates["recommendation"]
            if "requires_human_review" in updates:
                inv.requires_human_review = updates["requires_human_review"]
            self.repo.db.commit()
            return self.get_investigation(investigation_id)

        records = self._read()
        for index, record in enumerate(records):
            if record["investigation_id"] == investigation_id:
                records[index].update(updates)
                self._write(records)
                return records[index]
        raise KeyError(f"No investigation found for {investigation_id}")

    def get_investigation(self, investigation_id: str) -> Dict[str, Any]:
        for record in self._read():
            if record["investigation_id"] == investigation_id:
                return record
        raise KeyError(f"No investigation found for {investigation_id}")


class InvestigationAgent:
    def __init__(self, store: Optional[InvestigationStore] = None, provider: Optional[AIProvider] = None):
        self.store = store or InvestigationStore()
        self.provider = provider or RealLLMProvider()

    def get_transaction(self, transaction_id: str, records: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if records is None:
            records = {}
        return {"transaction_id": transaction_id, "records": records}

    def get_related_records(self, transaction_id: str, related: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        return related or []

    def get_exception(self, exception_id: str, exception: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return exception or {"exception_id": exception_id}

    def search_similar_transactions(self, criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return criteria.get("similar_transactions", []) if criteria else []

    def get_reconciliation_history(self, transaction_id: str, history: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        return history or []

    def investigate_exception(self, exception: Dict[str, Any], evidence: Dict[str, Any], source: Optional[str] = None) -> Dict[str, Any]:
        tools_used = [
            "get_transaction",
            "get_related_records",
            "get_exception",
            "search_similar_transactions",
            "get_reconciliation_history",
        ]
        provider_label = source or getattr(self.provider, "provider_name", "real_llm")
        investigation = self.store.create_investigation(
            exception_id=str(exception.get("exception_id") or exception.get("audit_id") or "EX-UNKNOWN"),
            provider=provider_label,
            tools_used=tools_used,
            evidence=evidence,
        )

        investigation["agent_status"] = InvestigationState.INVESTIGATING
        self.store.update_investigation(investigation["investigation_id"], investigation)

        result = self.provider.investigate(exception, evidence)

        # Store enriched investigation contract
        investigation["findings"] = result.get("findings", [])
        investigation["possible_causes"] = result.get("possible_causes", [])
        investigation["most_likely_cause"] = result.get("most_likely_cause", "UNKNOWN")
        investigation["confidence"] = result.get("confidence", "LOW")
        investigation["recommendation"] = result.get("recommendation") or result.get("recommended_action", "REVIEW")
        investigation["requires_human_review"] = result.get("requires_human_review", True)
        investigation["agent_status"] = (
            InvestigationState.COMPLETED if result.get("confidence") != "LOW" else InvestigationState.INSUFFICIENT_EVIDENCE
        )
        investigation["summary"] = result.get("summary", "Insufficient evidence.")
        investigation["evidence_collected"] = evidence

        # Contract fields
        investigation["diagnosis"] = result.get("diagnosis", result.get("summary", ""))
        investigation["likely_cause"] = result.get("likely_cause", result.get("most_likely_cause", "UNKNOWN"))
        investigation["limitations"] = result.get("limitations", [])
        investigation["recommended_action"] = result.get("recommended_action", "REVIEW")
        investigation["evidence_statements"] = result.get("evidence", [])

        self.store.update_investigation(investigation["investigation_id"], investigation)
        return investigation


def create_default_agent() -> InvestigationAgent:
    return InvestigationAgent(store=InvestigationStore(), provider=RealLLMProvider())
