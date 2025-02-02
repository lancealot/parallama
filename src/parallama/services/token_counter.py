"""Token counting service for OpenAI compatibility."""

import asyncio
from functools import lru_cache
from typing import AsyncGenerator, Dict, List, Optional, Union
import tiktoken
from cachetools import TTLCache

from ..gateway.config import TokenCounterConfig

class TokenCounter:
    """Service for counting tokens in text using tiktoken."""

    def __init__(self, config: TokenCounterConfig):
        """Initialize token counter.
        
        Args:
            config: Token counter configuration
        """
        self.config = config
        self._cache = TTLCache(
            maxsize=config.cache_size,
            ttl=config.cache_ttl
        )
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    @lru_cache(maxsize=10)
    def _get_encoder(self, model: str) -> tiktoken.Encoding:
        """Get the appropriate encoder for a model.
        
        Args:
            model: Model name (e.g., 'gpt-3.5-turbo')
            
        Returns:
            tiktoken.Encoding: The encoder for the model
        """
        try:
            # Try to get model-specific encoding
            return tiktoken.encoding_for_model(model)
        except KeyError:
            # Fall back to cl100k_base for unknown models
            return tiktoken.get_encoding("cl100k_base")

    async def count_tokens(
        self,
        text: Union[str, List[Dict[str, str]]],
        model: str
    ) -> int:
        """Count tokens in text.
        
        Args:
            text: Text to count tokens in, or list of chat messages
            model: Model name to use for counting
            
        Returns:
            int: Number of tokens
        """
        # Check cache first
        cache_key = (str(text), model)
        if cache_key in self._cache:
            self._hits += 1
            return self._cache[cache_key]
        
        self._misses += 1

        async with self._lock:
            encoder = self._get_encoder(model)
            
            if isinstance(text, str):
                # Count tokens in plain text
                token_count = len(encoder.encode(text))
            else:
                # Count tokens in chat messages
                token_count = 0
                for message in text:
                    # Count message role
                    token_count += len(encoder.encode(message.get("role", "")))
                    # Count message content
                    token_count += len(encoder.encode(message.get("content", "")))
                    # Add overhead for message formatting
                    token_count += 4  # Format tokens: <im_start>, role, content, <im_end>

                # Add chat overhead
                token_count += 2  # <|start|> and <|end|> tokens

            # Cache the result
            self._cache[cache_key] = token_count
            return token_count

    async def estimate_streaming_tokens(
        self,
        stream: AsyncGenerator[Dict[str, str], None],
        model: str
    ) -> int:
        """Estimate tokens in a streaming response.
        
        Args:
            stream: Async generator of response chunks
            model: Model name to use for counting
            
        Returns:
            int: Estimated number of tokens
        """
        total_tokens = 0
        encoder = self._get_encoder(model)

        async for chunk in stream:
            content = chunk.get("content", "")
            if content:
                total_tokens += len(encoder.encode(content))

        return total_tokens

    def clear_cache(self) -> None:
        """Clear the token count cache."""
        self._cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics.
        
        Returns:
            Dict[str, int]: Cache statistics including size and hits/misses
        """
        return {
            "size": len(self._cache),
            "maxsize": self._cache.maxsize,
            "currsize": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
        }
