"""Test configuration and fixtures."""

import pytest
from unittest.mock import MagicMock, patch
from redis import Redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

from parallama.models.base import Base

@pytest.fixture(scope="function")
def engine():
    """Create a test database engine."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture
def db_session(engine) -> Session:
    """Create a test database session."""
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

class RedisMock:
    """Mock Redis client that properly persists counters."""
    def __init__(self):
        self.counters = {}
        self.pipeline_operations = []

    def pipeline(self):
        """Create a new pipeline."""
        self.pipeline_operations.clear()
        pipeline = MagicMock()

        def mock_get(key):
            self.pipeline_operations.append(("get", key))
            return pipeline

        def mock_incr(key):
            self.pipeline_operations.append(("incr", key))
            return pipeline

        def mock_incrby(key, amount):
            self.pipeline_operations.append(("incrby", key, amount))
            return pipeline

        def mock_expire(key, ttl):
            self.pipeline_operations.append(("expire", key, ttl))
            return pipeline

        def mock_execute():
            results = []
            get_ops = []

            print("\nPipeline Operations:")
            for op in self.pipeline_operations:
                print(f"- {op}")
            print("Current Counters:", self.counters)

            # First collect all get operations and their values
            for op in self.pipeline_operations:
                if op[0] == "get":
                    get_ops.append(op[1])
                    # For token keys, accumulate all token usage for the current hour/day
                    if ":tokens:hour:" in op[1]:
                        hour = datetime.utcnow().strftime("%Y-%m-%d-%H")
                        base_key = op[1].split(hour)[0]
                        total = sum(int(v) for k, v in self.counters.items() if k.startswith(base_key) and ":tokens:hour:" in k)
                        results.append(str(total))
                        print(f"GET {op[1]} -> {total} (accumulated)")
                    elif ":tokens:day:" in op[1]:
                        day = datetime.utcnow().strftime("%Y-%m-%d")
                        base_key = op[1].split(day)[0]
                        total = sum(int(v) for k, v in self.counters.items() if k.startswith(base_key) and ":tokens:day:" in k)
                        results.append(str(total))
                        print(f"GET {op[1]} -> {total} (accumulated)")
                    else:
                        value = self.counters.get(op[1], "0")
                        results.append(value)
                        print(f"GET {op[1]} -> {value}")

            # Then process all mutations in order
            for op in self.pipeline_operations:
                if op[0] == "incr":
                    current = int(self.counters.get(op[1], "0"))
                    self.counters[op[1]] = str(current + 1)
                    print(f"INCR {op[1]} -> {self.counters[op[1]]}")
                elif op[0] == "incrby":
                    current = int(self.counters.get(op[1], "0"))
                    self.counters[op[1]] = str(current + op[2])
                    print(f"INCRBY {op[1]} {op[2]} -> {self.counters[op[1]]}")
                elif op[0] == "expire":
                    print(f"EXPIRE {op[1]} {op[2]}")
                    pass  # No-op for expire

            print("Results:", results)
            print("Updated Counters:", self.counters)
            return results

        pipeline.get.side_effect = mock_get
        pipeline.execute.side_effect = mock_execute
        pipeline.incr.side_effect = mock_incr
        pipeline.incrby.side_effect = mock_incrby
        pipeline.expire.side_effect = mock_expire
        return pipeline

    def get(self, key):
        """Get a value from Redis."""
        if ":tokens:hour:" in key:
            hour = datetime.utcnow().strftime("%Y-%m-%d-%H")
            base_key = key.split(hour)[0]
            total = sum(int(v) for k, v in self.counters.items() if k.startswith(base_key) and ":tokens:hour:" in k)
            print(f"Direct GET {key} -> {total} (accumulated)")
            return str(total)
        elif ":tokens:day:" in key:
            day = datetime.utcnow().strftime("%Y-%m-%d")
            base_key = key.split(day)[0]
            total = sum(int(v) for k, v in self.counters.items() if k.startswith(base_key) and ":tokens:day:" in k)
            print(f"Direct GET {key} -> {total} (accumulated)")
            return str(total)
        value = self.counters.get(key, "0")
        print(f"Direct GET {key} -> {value}")
        return value

    def ping(self):
        """Test Redis connection."""
        return True

    def close(self):
        """Close Redis connection."""
        pass

@pytest.fixture(scope="function")
def mock_redis():
    """Create a mock Redis client with dynamic counters."""
    redis_mock = RedisMock()
    # Wrap in MagicMock to provide Redis interface
    redis_client = MagicMock(wraps=redis_mock, spec=Redis)
    redis_client.pipeline.side_effect = redis_mock.pipeline
    redis_client.get.side_effect = redis_mock.get
    redis_client.ping.return_value = True
    redis_client.close.side_effect = redis_mock.close
    
    with patch('parallama.services.rate_limit.get_redis', return_value=iter([redis_client])):
        yield redis_client
