"""
SalesPromptBuilder — builds the final LLM prompt from query + retrieved context.

Design choices:
- XML-tagged context blocks: <source title="...">...</source>
  This format makes it easy for the LLM to cite sources by title.
- System message instructs the LLM to ONLY answer from provided context,
  avoiding hallucination of specs or prices.
- Conversion nudge is in the system prompt, not per-turn, so it applies
  consistently without inflating the user-visible prompt.
"""

from .interfaces.prompt_builder import IPromptBuilder
from .interfaces.retriever import RetrievedChunk

_SYSTEM_PROMPT = """\
You are ContainerBot, a knowledgeable sales assistant for Pacific Container Co.

RULES:
1. Answer ONLY using the provided <context> below. Do not invent specs, prices, or policies.
2. Cite your sources inline using [Source: <title>] after any fact you state.
3. Be helpful, specific, and conversational — like a knowledgeable sales rep.
4. If the context does not contain enough information, say: "I don't have that detail handy — \
let me connect you with our sales team."
5. When appropriate, guide the prospect toward the next step: getting a quote, \
placing an order, or speaking with a sales rep.

<custom_instructions>
{custom_instructions_block}
</custom_instructions>

<context>
{context_block}
</context>
"""


class SalesPromptBuilder(IPromptBuilder):
    def build(
        self,
        query: str,
        context: list[RetrievedChunk],
        custom_instructions: str | None = None,
    ) -> str:
        context_block = self._format_context(context)
        custom_block = custom_instructions.strip() if custom_instructions else "(none)"
        system = _SYSTEM_PROMPT.format(
            context_block=context_block,
            custom_instructions_block=custom_block,
        )
        return f"{system}\nUser: {query}\nContainerBot:"

    @staticmethod
    def _format_context(chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return "(no relevant context found)"
        parts = []
        for chunk in chunks:
            parts.append(f'<source title="{chunk.document_title}">\n{chunk.content}\n</source>')
        return "\n\n".join(parts)
