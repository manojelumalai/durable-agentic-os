"""Unit tests for Two-Tier Semantic Vector Cache."""

from durable_agent.llm.semantic_cache import TwoTierSemanticCache


def test_exact_cache_hit() -> None:
    cache = TwoTierSemanticCache(similarity_threshold=0.90)
    prompt = "What is the 24h trading volume of NVDA?"
    answer = '{"volume": 15000000}'

    cache.set(prompt, answer)
    res, hit_type = cache.get(prompt)

    assert res == answer
    assert hit_type == "exact"


def test_semantic_vector_cache_hit() -> None:
    cache = TwoTierSemanticCache(similarity_threshold=0.85)
    prompt_stored = "Analyze NVDA market trend and sentiment"
    answer = '{"sentiment": "bullish"}'

    cache.set(prompt_stored, answer)

    # Similar prompt with same key vocabulary
    similar_prompt = "Analyze NVDA market trend sentiment"
    res, hit_type = cache.get(similar_prompt)

    assert res == answer
    assert hit_type is not None and "semantic" in hit_type


def test_cache_miss() -> None:
    cache = TwoTierSemanticCache(similarity_threshold=0.90)
    cache.set("apple stock forecast", "bullish")

    res, hit_type = cache.get("crude oil commodity inventory")
    assert res is None
    assert hit_type is None
