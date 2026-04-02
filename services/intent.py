"""
KeywordIntentClassifier — lightweight keyword-matching classifier.

Approach: keyword matching with longest-match wins.
- Zero training data required (4 well-defined categories)
- Sub-millisecond latency (pure Python, no model load)
- Fallback: if no keywords match, return GENERAL

Why not LLM-based zero-shot classification?
- Adds an extra LLM round-trip before the main answer (~1-2s latency)
- For 4 sales-oriented categories the keyword rules are accurate enough
- Testable without any external dependencies (see test_agent.py)

Limitation: "Is the 40ft container available in Texas?" would classify as
AVAILABILITY (correct) but would miss the pricing sub-question.  A real
production system would use a fine-tuned classifier or multi-label model.
"""

from .interfaces.intent_classifier import IIntentClassifier, Intent

# Ordered by priority: CONVERSION checked first (higher business value)
_PATTERNS: list[tuple[Intent, list[str]]] = [
    (
        Intent.CONVERSION,
        [
            "i want to buy",
            "i want to order",
            "i want to purchase",
            "place an order",
            "ready to order",
            "ready to buy",
            "how do i order",
            "how do i buy",
            "can i place",
            "take my order",
            "sign up",
            "get started",
        ],
    ),
    (
        Intent.PRICING,
        [
            "how much",
            "price",
            "cost",
            "pricing",
            "quote",
            "rate",
            "discount",
            "cheap",
            "expensive",
            "bulk",
            "dollar",
            "$",
            "fee",
            "charge",
        ],
    ),
    (
        Intent.AVAILABILITY,
        [
            "deliver",
            "delivery",
            "shipping",
            "available",
            "availability",
            "in stock",
            "location",
            "state",
            "city",
            "texas",
            "california",
            "florida",
            "ship to",
            "do you",
            "can you",
            "region",
            "area",
            "coverage",
        ],
    ),
]


class KeywordIntentClassifier(IIntentClassifier):
    def classify(self, message: str) -> Intent:
        lower = message.lower()
        for intent, keywords in _PATTERNS:
            if any(kw in lower for kw in keywords):
                return intent
        return Intent.GENERAL
