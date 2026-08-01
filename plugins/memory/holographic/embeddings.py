"""Optional SBERT embeddings for semantic similarity.

Falls back gracefully when sentence-transformers is not installed.
No hard dependency — import this module safely in any environment.
"""

import logging
import math
import struct
from typing import Callable, Optional, Sequence

logger = logging.getLogger(__name__)

_EMBED_DIM = 384
_EMBED_MODEL = "all-MiniLM-L6-v2"
_cache = None  # SentenceTransformer | None


def _load_model():
    """Lazy-load the SBERT model. Cached after first call."""
    global _cache
    if _cache is not None:
        return _cache
    try:
        from sentence_transformers import SentenceTransformer

        _cache = SentenceTransformer(_EMBED_MODEL)
        logger.info("Loaded SBERT model: %s", _EMBED_MODEL)
    except ImportError:
        logger.debug(
            "sentence-transformers not installed — semantic features disabled"
        )
    except Exception as exc:
        logger.warning("Failed to load SBERT model: %s", exc)
    return _cache


def get_embedder():
    # type: () -> Optional[Callable[[Sequence[str]], list]]
    """Return a callable that embeds a batch of texts, or None."""
    model = _load_model()
    if model is None:
        return None

    import numpy as np

    def embed(texts):
        # type: (Sequence[str]) -> list
        if isinstance(texts, str):
            texts = [texts]
        embeddings = model.encode(
            list(texts), normalize_embeddings=True, show_progress_bar=False
        )
        return [np.asarray(e, dtype=np.float32) for e in embeddings]

    return embed


def embedding_dim():
    # type: () -> int
    return _EMBED_DIM


def pack_vector(vec):
    # type: (...) -> bytes
    """Pack a float32 vector into a BLOB without requiring NumPy."""
    values = [float(value) for value in vec]
    return struct.pack(f"{len(values)}f", *values)


def unpack_vector(blob):
    # type: (bytes) -> ...
    """Unpack a BLOB into a list of float32 values."""
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


def cosine_similarity(a, b):
    # type: (...) -> float
    """Cosine similarity between vectors. Both assumed normalized."""
    if len(a) != len(b):
        raise ValueError("vectors must have equal dimensions")
    a_values = [float(value) for value in a]
    b_values = [float(value) for value in b]
    a_norm = math.sqrt(math.fsum(value * value for value in a_values))
    b_norm = math.sqrt(math.fsum(value * value for value in b_values))
    if not a_norm or not b_norm:
        return 0.0
    dot = math.fsum(x * y for x, y in zip(a_values, b_values))
    return dot / (a_norm * b_norm)
