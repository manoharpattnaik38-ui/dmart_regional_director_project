"""Run the 20 acceptance cases through handle() and write logs/runs.jsonl and outputs/acceptance_transcript.md."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.run_agent import handle, reset_sessions

ACCEPTANCE_CASES = [
    ("A01", "s1", "What was Pune's revenue on 15 May 2026?", 0),
    ("A02", "s1", "And the target?", 0),
    ("A03", "s1", "How about Mumbai?", 0),
    ("A04", "s2", "How is Hyderabad doing?", 0),
    ("A05", "s2", "revenue on 2026-05-15", 0),
    ("A06", "s3", "What was Hydrabad's turnover yesterday?", 0),
    ("A07", "s4", "Did Pune hit its target on 2026-05-16?", 0),
    ("A08", "s4", "Did Pune hit its target on 2026-05-20?", 0),
    ("A09", "s4", "Did Mumbai hit its target on 2026-05-21?", 0),
    ("A10", "s5", "Which store had the highest average revenue between 2026-05-01 and 2026-05-31?", 0),
    ("A11", "s5", "Which store had the lowest revenue on 2026-06-10?", 0),
    ("A12", "s6", "Which stores are below the reorder threshold for Amul Milk?", 0),
    ("A13", "s6", "What are customers saying about Hyderabad?", 0),
    ("A14", "s7", "What was Pune's profit margin on 2026-05-15?", 0),
    ("A15", "s8", "What is the capital of India?", 0),
    ("A16", "s9", "What was Mumbai's revenue on 2026-07-15?", 0),
    ("A17", "s10", "Why is Pune's revenue so low?", 0),
    ("A18", "s11", "What was Kolkata's revenue on 2026-05-15?", 0),
    ("A19", "s12", "What was Pune's revenue on 15 May 2026?", 2),
    ("A20", "s13", "What was Pune's revenue on 15 May 2026?", 3),
]


def main():
    os.environ["AGENT_LOG_PATH"] = "logs/runs.jsonl"
    os.environ["WEATHER_MODE"] = "stub"
    os.makedirs("logs", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)

    # Empty logs/runs.jsonl before running the 20 cases
    with open("logs/runs.jsonl", "w", encoding="utf-8") as f:
        pass

    reset_sessions()
    results = []

    for case_id, session_id, question, sim_fail in ACCEPTANCE_CASES:
        os.environ["SIMULATE_DB_FAILURES"] = str(sim_fail)
        rec = handle(question, session_id=session_id, user_id="u1")
        results.append((case_id, rec))

    os.environ["SIMULATE_DB_FAILURES"] = "0"

    # Write outputs/acceptance_transcript.md
    lines = [
        "# Acceptance Test Transcript (20 Cases)\n",
        "| Id | Session | Question | Status | Intent | Confidence | Route | Attempts | Answer Text |",
        "| :--- | :--- | :--- | :--- | :--- | :---: | :--- | :---: | :--- |",
    ]
    for case_id, rec in results:
        lines.append(
            f"| {case_id} | {rec['session_id']} | {rec['question']} | {rec['status']} | "
            f"{rec['intent']} | {rec['confidence']} | {rec['route']} | {rec['attempts']} | {rec['answer_text']} |"
        )

    with open("outputs/acceptance_transcript.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Completed {len(results)} acceptance cases. Wrote logs/runs.jsonl and outputs/acceptance_transcript.md.")


if __name__ == "__main__":
    main()