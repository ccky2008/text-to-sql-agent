"""Azure OpenAI embedding service using LangChain."""

from langchain_openai import AzureOpenAIEmbeddings

from text_to_sql.config import get_settings
from text_to_sql.core.exceptions import EmbeddingError


class EmbeddingService:
    """Service for generating embeddings using Azure OpenAI (MSFT Foundry)."""

    def __init__(self) -> None:
        settings = get_settings()
        self._embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=settings.azure_embedding_endpoint,
            api_key=settings.azure_embedding_api_key.get_secret_value(),
            api_version=settings.azure_embedding_api_version,
            azure_deployment=settings.azure_embedding_deployment_name,
        )

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        try:
            return self._embeddings.embed_query(text)
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embedding: {e}") from e

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        try:
            return self._embeddings.embed_documents(texts)
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embeddings: {e}") from e

    @property
    def langchain_embeddings(self) -> AzureOpenAIEmbeddings:
        """Get the underlying LangChain embeddings instance."""
        return self._embeddings


_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get singleton embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
