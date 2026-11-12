import json
import os
import time
from datetime import datetime, timezone
from agent.understand import understand
from agent.fetch import fetch
from agent.answer import build_answer

_SESSIONS = {}
_RUN_COUNTER = 0


def reset_sessions():
    """Clear in-memory session state and reset the run counter."""
    global _SESSIONS, _RUN_COUNTER
    _SESSIONS = {}
    _RUN_COUNTER = 0


def handle(question, session_id, user_id="u1"):
    """Run the full 8-step agent pipeline, append one JSON line to AGENT_LOG_PATH, and return the record."""
    global _RUN_COUNTER
    t0 = time.perf_counter()
    _RUN_COUNTER += 1
    run_id = f"run_{_RUN_COUNTER:04d}"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = {}
    session_ctx = _SESSIONS[session_id]

    # Step 1: Interpret
    parsed = understand(question, session_ctx)

    # Step 2 & 3: Route & Pre-Query Validate
    needs_query = (
        parsed["intent"] not in {"unsupported_metric", "out_of_scope", "diagnostic"}
        and not parsed["missing_entities"]
        and not parsed.get("ambiguous")
        and not parsed.get("unresolved_store")
        and not parsed.get("unresolved_date")
        and parsed["confidence"] >= 0.7
    )

    if needs_query:
        # Step 4 & 5: Query & Calculate
        fetched = fetch(parsed)
        route = fetched["route"]
        executed = fetched["executed"]
        attempts = fetched["attempts"]
        tools_called = fetched["tools_called"]
        tool_calls = fetched["tool_calls"]
    else:
        fetched = None
        route = "none"
        executed = None
        attempts = 0
        tools_called = []
        tool_calls = 0

    # Step 6 & 7: Synthesize & Ground
    ans = build_answer(parsed, fetched)

    latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    tokens_est = len(question.split()) + len(ans["answer_text"].split())
    budget_exceeded = bool(tokens_est > 150)

    record = {
        "run_id": run_id,
        "user_id": user_id,
        "session_id": session_id,
        "timestamp": timestamp,
        "question": question,
        "intent": parsed["intent"],
        "confidence": parsed["confidence"],
        "route": route,
        "executed": executed,
        "attempts": attempts,
        "tools_called": tools_called,
        "status": ans["status"],
        "answer_text": ans["answer_text"],
        "evidence": ans["evidence"],
        "grounded_values": ans["grounded_values"],
        "latency_ms": latency_ms,
        "tokens_est": tokens_est,
        "tool_calls": tool_calls,
        "ungrounded_numbers": ans["ungrounded_numbers"],
        "budget_exceeded": budget_exceeded,
    }

    # Step 8: Record to AGENT_LOG_PATH on every call
    log_path = os.environ.get("AGENT_LOG_PATH", "logs/runs.jsonl")
    log_dir = os.path.dirname(log_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    return record
