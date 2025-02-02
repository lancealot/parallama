"""OpenAI-compatible embeddings endpoint implementation."""

from typing import Dict, Any, List
import numpy as np
from fastapi import Request
from fastapi.responses import JSONResponse

from ..config import OpenAIConfig

class EmbeddingsHandler:
    """Handler for embeddings endpoint."""

    def __init__(self, config: OpenAIConfig):
        """Initialize embeddings handler.
        
        Args:
            config: Gateway configuration
        """
        self.config = config
        self.model_dimensions = {
            "text-embedding-ada-002": 1536,  # OpenAI's default embedding model
            "llama2": 4096,  # Llama 2's embedding dimension
        }

    async def handle_request(self, request: Request) -> JSONResponse:
        """Handle embeddings request.
        
        Args:
            request: The incoming FastAPI request
            
        Returns:
            JSONResponse: The embeddings response
        """
        if not self.config.endpoints.embeddings:
            return JSONResponse(
                status_code=404,
                content={"error": "Embeddings endpoint is not enabled"}
            )

        data = await request.json()
        model = data.get("model", "text-embedding-ada-002")
        input_texts = data.get("input", [])
        
        if isinstance(input_texts, str):
            input_texts = [input_texts]
        
        # Get embedding dimension for model
        # Use original model name for dimension lookup, not mapped name
        dimension = self.model_dimensions.get(model, 1536)  # Default to OpenAI's dimension if unknown

        # Generate embeddings
        embeddings = []
        total_tokens = 0
        
        for text in input_texts:
            # Count tokens if enabled
            if self.config.token_counter.enabled:
                try:
                    tokens = await request.app.state.token_counter.count_tokens(
                        text,
                        model
                    )
                    # Handle mock token counter in tests
                    total_tokens += int(tokens) if isinstance(tokens, (int, float)) else 0
                except (TypeError, ValueError):
                    # Handle any token counting errors
                    total_tokens += 0
            
            # Generate pseudo-random embedding (for demonstration)
            # In production, this would call the actual model
            embedding = self._generate_pseudo_embedding(text, dimension)
            embeddings.append({
                "object": "embedding",
                "embedding": embedding.tolist(),
                "index": len(embeddings)
            })

        response = {
            "object": "list",
            "data": embeddings,
            "model": model,
            "usage": {
                "prompt_tokens": total_tokens,
                "total_tokens": total_tokens
            }
        }

        return JSONResponse(content=response)

    def _generate_pseudo_embedding(self, text: str, dimension: int) -> np.ndarray:
        """Generate a pseudo-random embedding for demonstration.
        
        In production, this would be replaced with actual model calls.
        
        Args:
            text: Input text
            dimension: Embedding dimension
            
        Returns:
            np.ndarray: Normalized embedding vector
        """
        # Use text hash as random seed for reproducibility
        seed = hash(text) % (2**32)
        rng = np.random.RandomState(seed)
        
        # Generate random vector
        embedding = rng.randn(dimension)
        
        # Normalize to unit length (cosine similarity ready)
        embedding = embedding / np.linalg.norm(embedding)
        
        return embedding

    async def validate_request(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Validate embeddings request.
        
        Args:
            data: Request data
            
        Returns:
            Dict[str, str]: Error message if validation fails, empty dict if successful
        """
        if "input" not in data:
            return {"error": "input is required"}
        
        input_texts = data.get("input", [])
        if isinstance(input_texts, str):
            input_texts = [input_texts]
        
        if not input_texts:
            return {"error": "input must not be empty"}
        
        if not all(isinstance(text, str) for text in input_texts):
            return {"error": "all input items must be strings"}
        
        if len(input_texts) > 100:  # OpenAI's limit
            return {"error": "maximum of 100 items allowed for embeddings"}
        
        return {}
