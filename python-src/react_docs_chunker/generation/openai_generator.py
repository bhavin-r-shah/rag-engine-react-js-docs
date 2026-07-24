"""Grounded answer generation using an OpenAI chat model."""
from __future__ import annotations

import os

from react_docs_chunker.generation.provider import GenerationProvider


class OpenAIGenerator(GenerationProvider):
    def __init__(self, model_name: str | None = None) -> None:
        from openai import OpenAI

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY environment variable is not set")
        self._model = model_name or os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        self._client = OpenAI(api_key=api_key)

    @property
    def model_id(self) -> str:
        return self._model

    def generate(self, question: str, context: list[dict]) -> str:
        evidence = "\n\n".join(
            f"[{item['citationId']}] {item['title']} — {' > '.join(item['headingPath'])}\n"
            f"URL: {item['citationUrl']}\n{item['text']}"
            for item in context
        )
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Answer only from the supplied React documentation evidence. "
                        "Cite supporting claims with labels such as [S1]. If the evidence "
                        "is insufficient, say so. Never invent a citation label."
                    ),
                },
                {"role": "user", "content": f"Question: {question}\n\nEvidence:\n{evidence}"},
            ],
        )
        return response.choices[0].message.content or ""
