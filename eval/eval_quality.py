"""
Answer Quality Evaluation Script.

Tests the full RAG pipeline against a golden Q&A dataset and scores
each answer using embedding cosine similarity.

Scoring:
- Semantic similarity ≥ 0.70 → PASS (answer is on-topic and factual)
- Semantic similarity 0.50–0.69 → WARN (answer is vague or partially relevant)
- Semantic similarity < 0.50 → FAIL (answer is off-topic or hallucinated)

Usage:
    uv run python eval/eval_quality.py [--verbose] [--env development|test]

Requires a running PostgreSQL DB with ingested documents.
For a quick smoke test without the DB, use --mock flag to use MockRetriever.
"""

import argparse
import math
import os
import sys
import time

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django

django.setup()

# ---------------------------------------------------------------------------
# Golden test cases
# Format: (question, expected_keywords_in_answer, intent_tag)
# ---------------------------------------------------------------------------

TEST_CASES = [
    (
        "How much is a 40ft container?",
        ["3,850", "40ft", "standard", "price"],
        "pricing",
    ),
    (
        "Do you deliver to Texas?",
        ["Texas", "deliver", "Dallas", "days"],
        "availability",
    ),
    (
        "What is the difference between a new and a one-trip container?",
        ["one-trip", "used", "condition", "asia"],
        "general",
    ),
    (
        "What customization options do you offer?",
        ["door", "window", "insulation", "paint"],
        "general",
    ),
    (
        "How long does delivery take to California?",
        ["California", "days", "Los Angeles", "business"],
        "availability",
    ),
    (
        "Do you offer bulk discounts?",
        ["discount", "units", "5%", "10%"],
        "pricing",
    ),
    (
        "What warranty do you provide?",
        ["warranty", "structural", "year", "surface"],
        "general",
    ),
    (
        "How do I place an order?",
        ["deposit", "quote", "delivery", "step"],
        "general",
    ),
    (
        "What is the capacity of a 40ft high cube?",
        ["2,660", "high cube", "cubic", "9.5ft"],
        "general",
    ),
    (
        "Can you match a competitor's price?",
        ["match", "quote", "competitor", "written"],
        "pricing",
    ),
]

# ---------------------------------------------------------------------------
# Cosine similarity
# ---------------------------------------------------------------------------


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------


def evaluate(use_mock: bool = False, verbose: bool = False) -> None:
    from services.factory import reset_cache

    if use_mock:
        from django.test.utils import override_settings

        mock_settings = {
            "SERVICE_CLASSES": {
                "EMBEDDER": "services.mocks.MockEmbedder",
                "RETRIEVER": "services.mocks.MockRetriever",
                "LLM_CLIENT": "services.mocks.MockLLMClient",
                "CHUNKER": "services.chunking.SemanticChunker",
                "INTENT_CLASSIFIER": "services.intent.KeywordIntentClassifier",
            }
        }
        ctx = override_settings(**mock_settings)
        ctx.__enter__()
        reset_cache()

    from services.factory import get_agent, get_embedder
    from services.intent import KeywordIntentClassifier

    agent = get_agent()
    embedder = get_embedder()
    classifier = KeywordIntentClassifier()

    print("\n" + "=" * 70)
    print("  Memox RAG Evaluation — Pacific Container Co.")
    print("=" * 70)
    print(f"{'Q':<55} {'Sim':>6}  {'Intent':>12}  Result")
    print("-" * 70)

    scores: list[float] = []
    intent_correct = 0

    for question, expected_keywords, expected_intent in TEST_CASES:
        t0 = time.perf_counter()

        response = agent.handle_message(question)

        # Semantic similarity: compare answer embedding to expected keyword string
        answer_emb = embedder.embed(response.content)
        expected_emb = embedder.embed(" ".join(expected_keywords))
        sim = cosine_similarity(answer_emb, expected_emb)

        # Intent accuracy
        predicted_intent = str(classifier.classify(question))
        intent_ok = predicted_intent == expected_intent
        if intent_ok:
            intent_correct += 1

        elapsed = time.perf_counter() - t0
        scores.append(sim)

        label = "PASS" if sim >= 0.70 else ("WARN" if sim >= 0.50 else "FAIL")
        color = "\033[92m" if label == "PASS" else ("\033[93m" if label == "WARN" else "\033[91m")
        reset = "\033[0m"

        q_short = question[:53] + ".." if len(question) > 55 else question
        print(f"{q_short:<55} {sim:>6.3f}  {predicted_intent:>12}  {color}{label}{reset}  ({elapsed:.1f}s)")

        if verbose:
            print(f"  → {response.content[:120]}...")
            print()

    # Summary
    avg = sum(scores) / len(scores)
    passed = sum(1 for s in scores if s >= 0.70)
    warned = sum(1 for s in scores if 0.50 <= s < 0.70)
    failed = sum(1 for s in scores if s < 0.50)

    print("=" * 70)
    print(f"  Results: {passed} PASS / {warned} WARN / {failed} FAIL  (avg sim: {avg:.3f})")
    print(f"  Intent accuracy: {intent_correct}/{len(TEST_CASES)} ({100*intent_correct//len(TEST_CASES)}%)")
    print("=" * 70 + "\n")

    if use_mock:
        ctx.__exit__(None, None, None)
        reset_cache()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate RAG answer quality")
    parser.add_argument("--mock", action="store_true", help="Use mock services (no DB required)")
    parser.add_argument("--verbose", action="store_true", help="Print answer excerpts")
    args = parser.parse_args()
    evaluate(use_mock=args.mock, verbose=args.verbose)
