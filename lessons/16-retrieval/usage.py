"""Keeping track of what a run costs.

The numbers here come from the provider rather than from a local estimate,
because a local estimate is wrong by enough to matter. A tokeniser built for
one company does not count another company's tokens, so a harness that talks
to more than one service and uses a single counter for both is making its
trimming decisions on the wrong number.
"""
from dataclasses import dataclass, field


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    calls: int = 0
    per_call: list = field(default_factory=list)

    def add(self, reported: dict) -> None:
        """Record what one request actually cost, as the provider reported it."""
        if not reported:
            return
        self.calls += 1
        self.prompt_tokens += reported.get("prompt_tokens", 0)
        self.completion_tokens += reported.get("completion_tokens", 0)
        self.per_call.append(reported)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def cost(self, prompt_price_per_million=0.0, completion_price_per_million=0.0) -> float:
        """Turn tokens into money, given the prices you are actually paying.

        Prices are an argument rather than a table baked into the code
        because they change, and a stale price table is worse than no price
        table since it looks authoritative while being wrong.
        """
        return (
            self.prompt_tokens * prompt_price_per_million
            + self.completion_tokens * completion_price_per_million
        ) / 1_000_000

    def summary(self) -> str:
        return (
            f"{self.calls} calls, {self.prompt_tokens} prompt tokens, "
            f"{self.completion_tokens} completion tokens"
        )
