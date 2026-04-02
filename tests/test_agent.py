"""
Tests for intent classification and agent message handling.

All AI services use mocks (no LLM, no embeddings loaded) — fast and offline.
"""
import pytest

from services.agent import AgentHandler
from services.intent import KeywordIntentClassifier
from services.interfaces.intent_classifier import INTENT_SCORES, Intent
from services.mocks import MockEmbedder, MockLLMClient, MockRetriever
from services.prompt_builder import SalesPromptBuilder


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------


def classify_intent(message: str) -> str:
    return str(KeywordIntentClassifier().classify(message))


def test_intent_classification_pricing():
    assert classify_intent("How much is a 40ft container?") == "pricing"


def test_intent_classification_availability():
    assert classify_intent("Do you deliver to Texas?") == "availability"


def test_intent_classification_conversion():
    assert classify_intent("I want to place an order") == "conversion"


def test_intent_classification_general():
    assert classify_intent("Tell me about your company") == "general"


def test_intent_classification_buy_variant():
    assert classify_intent("I want to buy a container") == "conversion"


def test_intent_classification_pricing_cost():
    assert classify_intent("What is the cost of a 20ft?") == "pricing"


def test_intent_classification_availability_ship():
    assert classify_intent("Can you ship to California?") == "availability"


def test_intent_classification_case_insensitive():
    assert classify_intent("HOW MUCH IS A 40FT CONTAINER?") == "pricing"


# ---------------------------------------------------------------------------
# Intent scoring
# ---------------------------------------------------------------------------


def test_intent_scores_ordering():
    """Conversion should score higher than pricing, which scores higher than availability."""
    assert INTENT_SCORES[Intent.CONVERSION] > INTENT_SCORES[Intent.PRICING]
    assert INTENT_SCORES[Intent.PRICING] > INTENT_SCORES[Intent.AVAILABILITY]
    assert INTENT_SCORES[Intent.AVAILABILITY] > INTENT_SCORES[Intent.GENERAL]


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


def test_prompt_builder_includes_query():
    from services.interfaces.retriever import RetrievedChunk

    builder = SalesPromptBuilder()
    context = [
        RetrievedChunk(
            content="40ft: $3,850",
            document_title="Pricing Sheet",
            chunk_index=0,
            score=0.9,
        )
    ]
    prompt = builder.build("How much is a 40ft container?", context)
    assert "How much is a 40ft container?" in prompt
    assert "Pricing Sheet" in prompt
    assert "3,850" in prompt


def test_prompt_builder_empty_context():
    builder = SalesPromptBuilder()
    prompt = builder.build("What is your return policy?", [])
    assert "no relevant context found" in prompt


def test_prompt_builder_cites_source_title():
    from services.interfaces.retriever import RetrievedChunk

    builder = SalesPromptBuilder()
    context = [RetrievedChunk(content="...", document_title="Delivery Policy", chunk_index=0, score=0.8)]
    prompt = builder.build("How fast is delivery?", context)
    assert "Delivery Policy" in prompt


# ---------------------------------------------------------------------------
# AgentHandler (fully mocked)
# ---------------------------------------------------------------------------


@pytest.fixture
def agent():
    return AgentHandler(
        retriever=MockRetriever(),
        llm_client=MockLLMClient(),
        prompt_builder=SalesPromptBuilder(),
        intent_classifier=KeywordIntentClassifier(),
    )


def test_agent_handle_message_returns_response(agent):
    response = agent.handle_message("How much is a 40ft container?")
    assert response.content != ""
    assert response.intent == "pricing"
    assert len(response.sources) > 0


def test_agent_pricing_returns_product_comparison_component(agent):
    response = agent.handle_message("How much is a 40ft container?")
    types = [c["type"] for c in response.components]
    assert "product_comparison" in types


def test_agent_conversion_triggers_handoff(agent):
    response = agent.handle_message("I want to place an order")
    assert response.handoff_triggered is True
    types = [c["type"] for c in response.components]
    assert "cta" in types


def test_agent_general_no_handoff(agent):
    response = agent.handle_message("Tell me about your company")
    assert response.handoff_triggered is False


def test_agent_response_has_message_id(agent):
    response = agent.handle_message("What sizes do you have?")
    assert response.message_id is not None
    assert len(response.message_id) == 36  # UUID format


def test_agent_lead_score_delta_matches_intent(agent):
    pricing_response = agent.handle_message("What does a 40ft cost?")
    assert pricing_response.lead_score_delta == INTENT_SCORES[Intent.PRICING]

    conversion_response = agent.handle_message("I want to buy a container")
    assert conversion_response.lead_score_delta == INTENT_SCORES[Intent.CONVERSION]


def test_agent_stream_yields_tokens_then_response(agent):
    items = list(agent.stream_message("How much does a 40ft cost?"))
    assert len(items) > 1, "Should yield at least one token and a final response"

    from services.agent import AgentResponse

    # Last item should be AgentResponse
    assert isinstance(items[-1], AgentResponse)
    # All items before last should be strings (tokens)
    for item in items[:-1]:
        assert isinstance(item, str)
