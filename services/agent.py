"""
AgentHandler — routes messages based on intent and builds structured responses.

handle_message() is the main entry point for both the REST endpoint and the
WebSocket consumer.  It returns an AgentResponse dataclass that callers
can serialise to JSON.

SOLID note: AgentHandler depends on IRetriever, ILLMClient, IPromptBuilder,
and IIntentClassifier — all interfaces.  Concrete classes are injected via
the factory, making the handler fully testable with mocks.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from collections.abc import Generator

from .factory import get_intent_classifier, get_llm_client, get_prompt_builder, get_retriever
from .interfaces.intent_classifier import INTENT_SCORES, Intent
from .interfaces.retriever import RetrievedChunk


# ---------------------------------------------------------------------------
# Response dataclass — the structured return value of handle_message()
# ---------------------------------------------------------------------------


@dataclass
class AgentResponse:
    message_id: str
    content: str
    intent: str
    sources: list[dict]
    components: list[dict]
    lead_score_delta: int
    handoff_triggered: bool

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "content": self.content,
            "intent": self.intent,
            "sources": self.sources,
            "components": self.components,
            "lead_score_delta": self.lead_score_delta,
            "handoff_triggered": self.handoff_triggered,
        }


# ---------------------------------------------------------------------------
# AgentHandler
# ---------------------------------------------------------------------------


class AgentHandler:
    """
    Orchestrates intent classification → retrieval → prompt building → LLM call
    → structured response assembly.

    Every dependency is injected (or resolved lazily from the factory) so that
    tests can swap in mocks without touching production code.
    """

    def __init__(
        self,
        retriever=None,
        llm_client=None,
        prompt_builder=None,
        intent_classifier=None,
    ) -> None:
        self._retriever = retriever or get_retriever()
        self._llm = llm_client or get_llm_client()
        self._prompt_builder = prompt_builder or get_prompt_builder()
        self._intent_classifier = intent_classifier or get_intent_classifier()

    def handle_message(self, message: str, llm_client=None, custom_instructions: str | None = None) -> AgentResponse:
        """
        Full pipeline: classify → retrieve → prompt → complete → structure.
        Use this for the REST endpoint where streaming is not required.
        """
        intent = self._intent_classifier.classify(message)
        context = self._retriever.retrieve(message)
        prompt = self._prompt_builder.build(
            message,
            context,
            custom_instructions=custom_instructions,
        )
        llm = llm_client or self._llm
        content = llm.complete(prompt)
        return self._build_response(content, intent, context)

    def stream_message(
        self,
        message: str,
        llm_client=None,
        custom_instructions: str | None = None,
    ) -> Generator[str | AgentResponse, None, None]:
        """
        Streaming pipeline for the WebSocket consumer.
        Yields:
          - str tokens as they arrive from the LLM
          - a final AgentResponse object signalling completion
        """
        intent = self._intent_classifier.classify(message)
        context = self._retriever.retrieve(message)
        prompt = self._prompt_builder.build(
            message,
            context,
            custom_instructions=custom_instructions,
        )

        full_content = ""
        llm = llm_client or self._llm
        for token in llm.stream(prompt):
            full_content += token
            yield token  # caller sends this over WebSocket immediately

        yield self._build_response(full_content, intent, context)  # final structured response

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_response(
        self, content: str, intent: Intent, context: list[RetrievedChunk]
    ) -> AgentResponse:
        sources = [
            {
                "title": chunk.document_title,
                "excerpt": chunk.content[:200],
                "score": chunk.score,
                "chunk_index": chunk.chunk_index,
            }
            for chunk in context
        ]
        components = self._build_components(intent, context)
        handoff = intent == Intent.CONVERSION

        return AgentResponse(
            message_id=str(uuid.uuid4()),
            content=content,
            intent=str(intent),
            sources=sources,
            components=components,
            lead_score_delta=INTENT_SCORES.get(intent, 1),
            handoff_triggered=handoff,
        )

    @staticmethod
    def _build_components(intent: Intent, context: list[RetrievedChunk]) -> list[dict]:
        components: list[dict] = []

        if intent == Intent.PRICING:
            # Emit a product comparison card — frontend renders this as a table
            products = _extract_product_comparison(context)
            if products:
                components.append({"type": "product_comparison", "data": {"products": products}})

        if intent == Intent.CONVERSION:
            components.append(
                {
                    "type": "cta",
                    "label": "Request a Quote",
                    "description": "Our sales team will reach out within 24 hours.",
                    "action": "open_quote_form",
                    "variant": "primary",
                }
            )

        return components


# ---------------------------------------------------------------------------
# Helper — parse product data from retrieved context for the comparison card
# ---------------------------------------------------------------------------

_PRICE_SIZES = [
    ("20ft Standard", "20ft"),
    ("40ft Standard", "40ft"),
    ("40ft High Cube", "HC"),
    ("10ft Mini", "10ft"),
]


def _extract_product_comparison(context: list[RetrievedChunk]) -> list[dict]:
    """
    Heuristic: look for price patterns in retrieved chunks and build product rows.
    Returns [] if no pricing data found (component is omitted in that case).
    """
    import re

    all_text = " ".join(chunk.content for chunk in context)
    price_pattern = re.compile(r"\$[\d,]+")
    if not price_pattern.search(all_text):
        return []

    # Return static comparison if pricing context exists (real impl would parse dynamically)
    return [
        {"name": "20ft Standard", "price": "from $2,100", "size": "20×8×8.5ft", "capacity": "1,172 cu ft"},
        {"name": "40ft Standard", "price": "from $3,850", "size": "40×8×8.5ft", "capacity": "2,385 cu ft"},
        {"name": "40ft High Cube", "price": "from $4,200", "size": "40×8×9.5ft", "capacity": "2,660 cu ft"},
    ]
