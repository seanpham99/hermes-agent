"""Test the embeddings utility module."""
import pytest

from plugins.memory.holographic.embeddings import (
    cosine_similarity,
    embedding_dim,
    get_embedder,
    pack_vector,
    unpack_vector,
)


class TestEmbeddingsModule:
    """Test the embeddings utility module (no model required)."""

    def test_pack_unpack_roundtrip(self):
        """Vector survives pack -> unpack roundtrip."""
        vec = [0.1, -0.2, 0.3, 0.0]
        blob = pack_vector(vec)
        restored = unpack_vector(blob)
        assert restored == pytest.approx(vec)

    def test_cosine_identical(self):
        """Cosine of identical normalized vectors is 1.0."""
        v = [0.5, 0.5]
        assert abs(cosine_similarity(v, v) - 1.0) < 0.001

    def test_cosine_orthogonal(self):
        """Cosine of orthogonal unit vectors is 0.0."""
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(cosine_similarity(a, b)) < 0.001

    def test_embedding_dim(self):
        """Embedding dimension is 384."""
        assert embedding_dim() == 384

    def test_get_embedder_returns_callable_or_none(self):
        """get_embedder returns either None (no deps) or a callable."""
        result = get_embedder()
        assert result is None or callable(result)
