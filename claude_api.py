import asyncio
import logging

from anthropic import AsyncAnthropic
from config import CLAUDE_API_KEY, MODEL_NAME

logger = logging.getLogger(__name__)
client = AsyncAnthropic(api_key=CLAUDE_API_KEY)


async def generate_with_claude(prompt: str) -> str:
    response = await asyncio.wait_for(
        client.messages.create(
            model=MODEL_NAME,
            max_tokens=2200,
            messages=[{"role": "user", "content": prompt}],
        ),
        timeout=60,
    )
    reply = "".join(
        block.text for block in response.content
        if getattr(block, "type", "") == "text" and getattr(block, "text", "")
    ).strip()

    return reply or "Не вдалося отримати відповідь від моделі."
