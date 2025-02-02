"""Tests for the token counter service."""

import pytest
from typing import AsyncGenerator, Dict

from parallama.gateway.config import TokenCounterConfig
from parallama.services.token_counter import TokenCounter

@pytest.fixture
def token_counter():
    """Create a test token counter instance."""
    config = TokenCounterConfig(
        enabled=True,
        cache_size=100,
        cache_ttl=60
    )
    return TokenCounter(config)

@pytest.mark.asyncio
async def test_count_text_tokens(token_counter):
    """Test counting tokens in plain text."""
    text = "Hello, world!"
    tokens = await token_counter.count_tokens(text, "gpt-3.5-turbo")
    assert tokens > 0
    assert isinstance(tokens, int)

@pytest.mark.asyncio
async def test_count_chat_tokens(token_counter):
    """Test counting tokens in chat messages."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi! How can I help you today?"}
    ]
    tokens = await token_counter.count_tokens(messages, "gpt-3.5-turbo")
    assert tokens > 0
    assert isinstance(tokens, int)

@pytest.mark.asyncio
async def test_token_cache(token_counter):
    """Test token count caching."""
    text = "This is a test message."
    
    # First count should cache
    count1 = await token_counter.count_tokens(text, "gpt-3.5-turbo")
    stats1 = token_counter.get_cache_stats()
    
    # Second count should hit cache
    count2 = await token_counter.count_tokens(text, "gpt-3.5-turbo")
    stats2 = token_counter.get_cache_stats()
    
    assert count1 == count2
    assert stats2["hits"] > stats1["hits"]

@pytest.mark.asyncio
async def test_different_models(token_counter):
    """Test token counting with different models."""
    text = "Test message"
    
    # Count with different models
    gpt35_tokens = await token_counter.count_tokens(text, "gpt-3.5-turbo")
    gpt4_tokens = await token_counter.count_tokens(text, "gpt-4")
    
    # Should use same base tokenizer, so counts should match
    assert gpt35_tokens == gpt4_tokens

@pytest.mark.asyncio
async def test_unknown_model_fallback(token_counter):
    """Test fallback behavior for unknown models."""
    text = "Test message"
    
    # Should not raise error for unknown model
    tokens = await token_counter.count_tokens(text, "unknown-model")
    assert tokens > 0

@pytest.mark.asyncio
async def test_streaming_token_count(token_counter):
    """Test counting tokens in streaming response."""
    async def mock_stream() -> AsyncGenerator[Dict[str, str], None]:
        chunks = [
            {"content": "Hello"},
            {"content": " world"},
            {"content": "!"}
        ]
        for chunk in chunks:
            yield chunk

    tokens = await token_counter.estimate_streaming_tokens(
        mock_stream(),
        "gpt-3.5-turbo"
    )
    assert tokens > 0
    assert isinstance(tokens, int)

@pytest.mark.asyncio
async def test_empty_text(token_counter):
    """Test counting tokens in empty text."""
    # Empty string
    text_tokens = await token_counter.count_tokens("", "gpt-3.5-turbo")
    assert text_tokens == 0
    
    # Empty messages list
    chat_tokens = await token_counter.count_tokens([], "gpt-3.5-turbo")
    assert chat_tokens == 2  # Just the chat overhead tokens

@pytest.mark.asyncio
async def test_cache_clear(token_counter):
    """Test cache clearing."""
    text = "Test message"
    
    # Count once to cache
    await token_counter.count_tokens(text, "gpt-3.5-turbo")
    stats1 = token_counter.get_cache_stats()
    assert stats1["size"] > 0
    
    # Clear cache
    token_counter.clear_cache()
    stats2 = token_counter.get_cache_stats()
    assert stats2["size"] == 0

@pytest.mark.asyncio
async def test_concurrent_counting(token_counter):
    """Test concurrent token counting."""
    import asyncio
    
    text = "Test message"
    
    # Make concurrent requests
    tasks = [
        token_counter.count_tokens(text, "gpt-3.5-turbo")
        for _ in range(5)
    ]
    
    # Should not raise errors
    results = await asyncio.gather(*tasks)
    assert all(r == results[0] for r in results)

@pytest.mark.asyncio
async def test_cache_ttl(token_counter):
    """Test cache TTL expiration."""
    import asyncio
    
    # Create counter with short TTL
    config = TokenCounterConfig(
        enabled=True,
        cache_size=100,
        cache_ttl=1  # 1 second TTL
    )
    counter = TokenCounter(config)
    
    text = "Test message"
    
    # First count
    count1 = await counter.count_tokens(text, "gpt-3.5-turbo")
    stats1 = counter.get_cache_stats()
    
    # Wait for TTL to expire
    await asyncio.sleep(1.1)
    
    # Second count should miss cache
    count2 = await counter.count_tokens(text, "gpt-3.5-turbo")
    stats2 = counter.get_cache_stats()
    
    assert count1 == count2
    assert stats2["misses"] > stats1["misses"]
