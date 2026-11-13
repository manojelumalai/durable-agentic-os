"""Two-tier semantic vector cache combining exact SHA-256 hashing and cosine vector similarity."""

import hashlib
import math
import time
from typing import Any


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Calculate cosine similarity between two float vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=False))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _pseudo_embedding(text: str, dim: int = 16) -> list[float]:
    """Deterministic token hash vector for testing/local embedding representation."""
    vec = [0.0] * dim
    words = text.lower().split()
    for word in words:
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        vec[idx] += 1.0
    # Normalize vector
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0.0:
        vec = [x / norm for x in vec]
    return vec


class TwoTierSemanticCache:
    """Fast L1 exact cache with L2 semantic vector similarity lookup."""

    def __init__(self, similarity_threshold: float = 0.92, ttl_seconds: int = 3600) -> None:
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_seconds
        self.exact_cache: dict[str, tuple[Any, float]] = {}
        self.vector_cache: list[dict[str, Any]] = []

    def get(self, query: str) -> tuple[Any | None, str | None]:
        """Lookup cached result. Returns (result, hit_type) where hit_type is 'exact' or 'semantic'."""
        now = time.time()
        # Tier 1: Exact Hash Match
        query_hash = hashlib.sha256(query.strip().encode("utf-8")).hexdigest()
        if query_hash in self.exact_cache:
            val, expiry = self.exact_cache[query_hash]
            if now < expiry:
                return val, "exact"
            del self.exact_cache[query_hash]

        # Tier 2: Semantic Vector Similarity Match
        query_vec = _pseudo_embedding(query)
        best_match = None
        best_score = -1.0

        for item in self.vector_cache:
            if now > item["expiry"]:
                continue
            sim = _cosine_similarity(query_vec, item["embedding"])
            if sim > best_score:
                best_score = sim
                best_match = item["value"]

        if best_match is not None and best_score >= self.similarity_threshold:
            return best_match, f"semantic_{best_score:.3f}"

        return None, None

    def set(self, query: str, value: Any) -> None:
        """Store item in both exact hash cache and semantic vector index."""
        now = time.time()
        expiry = now + self.ttl_seconds
        query_hash = hashlib.sha256(query.strip().encode("utf-8")).hexdigest()
        self.exact_cache[query_hash] = (value, expiry)

        query_vec = _pseudo_embedding(query)
        self.vector_cache.append(
            {
                "query": query,
                "embedding": query_vec,
                "value": value,
                "expiry": expiry,
            }
        )
