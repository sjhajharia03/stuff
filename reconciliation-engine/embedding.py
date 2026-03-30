"""
Embedding generation and semantic similarity utilities.
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import config


class EmbeddingEngine:
    """
    Manages embedding generation and similarity computation.
    """

    def __init__(self):
        """Initialize the sentence transformer model."""
        print(f"Loading embedding model: {config.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(config.EMBEDDING_MODEL)
        print("Model loaded successfully")

    def generate_embeddings(self, texts: list[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings

        Returns:
            Numpy array of embeddings (shape: [n_texts, embedding_dim])
        """
        # Handle empty strings
        processed_texts = [text if text and text.strip() else "empty" for text in texts]

        embeddings = self.model.encode(processed_texts, show_progress_bar=False)
        return embeddings

    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score (0-1)
        """
        # Reshape for sklearn if needed
        if len(embedding1.shape) == 1:
            embedding1 = embedding1.reshape(1, -1)
        if len(embedding2.shape) == 1:
            embedding2 = embedding2.reshape(1, -1)

        similarity = cosine_similarity(embedding1, embedding2)[0][0]
        return float(similarity)

    def compute_similarity_matrix(self, embeddings1: np.ndarray, embeddings2: np.ndarray) -> np.ndarray:
        """
        Compute pairwise cosine similarity between two sets of embeddings.

        Args:
            embeddings1: First set of embeddings (shape: [n1, dim])
            embeddings2: Second set of embeddings (shape: [n2, dim])

        Returns:
            Similarity matrix (shape: [n1, n2])
        """
        similarity_matrix = cosine_similarity(embeddings1, embeddings2)
        return similarity_matrix
