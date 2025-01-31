"""Tests for CLI commands."""
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from uuid import uuid4, UUID
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from parallama.cli import cli
from parallama.models.user import User
from parallama.models.api_key import APIKey
from parallama.models.base import Base

@pytest.fixture(scope="function")
def test_db():
    """Create a test database."""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Initialize default roles
    from parallama.services.role import RoleService
    role_service = RoleService(session)
    role_service.initialize_default_roles()
    session.commit()
    
    return session

@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner(mix_stderr=False)

@pytest.fixture
def mock_db_session(test_db):
    """Mock the CLI's database session."""
    with patch('parallama.cli.core.db._db_session', test_db), \
         patch('parallama.cli.core.db.get_db', return_value=test_db):
        yield test_db

@pytest.fixture
def mock_redis_client():
    """Mock the CLI's Redis client."""
    mock_redis = MagicMock()
    with patch('parallama.cli.core.db._redis_client', mock_redis), \
         patch('parallama.cli.core.db.get_redis', return_value=mock_redis):
        yield mock_redis

class TestUserCommands:
    """Tests for user management commands."""

    def test_create_user(self, cli_runner, mock_db_session, mock_redis_client):
        """Test creating a new user."""
        result = cli_runner.invoke(cli, ['user', 'create', 'testuser'], input='password\npassword\n')
        assert result.exit_code == 0
        assert "User 'testuser' created successfully" in result.output

        # Verify user was created
        user = mock_db_session.query(User).filter_by(username='testuser').first()
        assert user is not None
        assert user.username == 'testuser'
        assert user.role == 'basic'
        assert not user.is_admin

    def test_create_admin_user(self, cli_runner, mock_db_session, mock_redis_client):
        """Test creating an admin user."""
        result = cli_runner.invoke(
            cli,
            ['user', 'create', 'adminuser', '--admin', '--role', 'premium'],
            input='password\npassword\n'
        )
        assert result.exit_code == 0
        assert "User 'adminuser' created successfully" in result.output

        user = mock_db_session.query(User).filter_by(username='adminuser').first()
        assert user is not None
        assert user.username == 'adminuser'
        assert user.role == 'premium'
        assert user.is_admin

    def test_list_users(self, cli_runner, mock_db_session, mock_redis_client):
        """Test listing users."""
        # Create test users
        user1 = User(username='user1', role='basic')
        user1.set_password('password')
        user2 = User(username='user2', role='premium')
        user2.set_password('password')
        mock_db_session.add_all([user1, user2])
        mock_db_session.commit()

        result = cli_runner.invoke(cli, ['user', 'list'])
        assert result.exit_code == 0
        assert 'user1' in result.output
        assert 'user2' in result.output
        assert 'basic' in result.output
        assert 'premium' in result.output

    def test_get_user_info(self, cli_runner, mock_db_session, mock_redis_client):
        """Test getting user information."""
        user = User(username='testuser', role='basic')
        user.set_password('password')
        mock_db_session.add(user)
        mock_db_session.commit()

        result = cli_runner.invoke(cli, ['user', 'info', 'testuser'])
        assert result.exit_code == 0
        assert 'testuser' in result.output
        assert 'basic' in result.output

    def test_update_user(self, cli_runner, mock_db_session, mock_redis_client):
        """Test updating user details."""
        user = User(username='testuser', role='basic')
        user.set_password('password')
        mock_db_session.add(user)
        mock_db_session.commit()

        result = cli_runner.invoke(
            cli,
            ['user', 'update', 'testuser', '--role', 'premium', '--admin'],
            input='y\n'  # Confirm the action
        )
        assert result.exit_code == 0
        assert "User 'testuser' updated successfully" in result.output

        user = mock_db_session.query(User).filter_by(username='testuser').first()
        assert user.role == 'premium'
        assert user.is_admin

    def test_delete_user(self, cli_runner, mock_db_session, mock_redis_client):
        """Test deleting a user."""
        user = User(username='testuser', role='basic')
        user.set_password('password')
        mock_db_session.add(user)
        mock_db_session.commit()

        result = cli_runner.invoke(
            cli,
            ['user', 'delete', 'testuser'],
            input='y\n'  # Confirm the action
        )
        assert result.exit_code == 0
        assert "User 'testuser' deleted successfully" in result.output

        user = mock_db_session.query(User).filter_by(username='testuser').first()
        assert user is None

class TestKeyCommands:
    """Tests for API key management commands."""

    @pytest.fixture
    def test_user(self, mock_db_session):
        """Create a test user."""
        user = User(username='testuser', role='basic')
        user.set_password('password')
        mock_db_session.add(user)
        mock_db_session.commit()
        
        # Refresh the user to ensure it's attached to the session
        mock_db_session.refresh(user)
        return user

    def test_generate_key(self, cli_runner, mock_db_session, mock_redis_client, test_user):
        """Test generating an API key."""
        # Get user ID before test
        user_id = str(test_user.id)
        mock_db_session.refresh(test_user)
        
        result = cli_runner.invoke(
            cli,
            ['key', 'generate', 'testuser', '--description', 'Test key']
        )
        assert result.exit_code == 0
        assert "API key generated for user 'testuser'" in result.output
        assert "pk_live_" in result.output

        # Verify key was created
        key = mock_db_session.query(APIKey).filter_by(user_id=user_id).first()
        assert key is not None
        assert key.description == 'Test key'

    def test_list_keys(self, cli_runner, mock_db_session, mock_redis_client, test_user):
        """Test listing API keys."""
        # Create test keys
        key1 = APIKey(user_id=str(test_user.id), description='Key 1')
        key1.set_key(APIKey.generate_key())
        key2 = APIKey(user_id=str(test_user.id), description='Key 2')
        key2.set_key(APIKey.generate_key())
        mock_db_session.add_all([key1, key2])
        mock_db_session.commit()

        result = cli_runner.invoke(cli, ['key', 'list', '--username', 'testuser'])
        assert result.exit_code == 0
        assert 'Key 1' in result.output
        assert 'Key 2' in result.output
        assert 'Active' in result.output

    def test_revoke_key(self, cli_runner, mock_db_session, mock_redis_client, test_user):
        """Test revoking an API key."""
        key = APIKey(user_id=str(test_user.id), description='Test key')
        key.set_key(APIKey.generate_key())
        mock_db_session.add(key)
        mock_db_session.commit()

        result = cli_runner.invoke(
            cli,
            ['key', 'revoke', str(key.id)],
            input='y\n'  # Confirm the action
        )
        assert result.exit_code == 0
        assert "API key revoked successfully" in result.output

        # Verify key was revoked
        key = mock_db_session.query(APIKey).filter_by(id=key.id).first()
        assert key.revoked_at is not None

    def test_generate_key_nonexistent_user(self, cli_runner, mock_db_session, mock_redis_client):
        """Test generating a key for a nonexistent user."""
        result = cli_runner.invoke(cli, ['key', 'generate', 'nonexistent'], catch_exceptions=False)
        assert result.exit_code != 0
        assert "User 'nonexistent' not found" in result.stderr

    def test_list_keys_nonexistent_user(self, cli_runner, mock_db_session, mock_redis_client):
        """Test listing keys for a nonexistent user."""
        result = cli_runner.invoke(cli, ['key', 'list', '--username', 'nonexistent'], catch_exceptions=False)
        assert result.exit_code != 0
        assert "User 'nonexistent' not found" in result.stderr

    def test_revoke_nonexistent_key(self, cli_runner, mock_db_session, mock_redis_client):
        """Test revoking a nonexistent key."""
        result = cli_runner.invoke(cli, ['key', 'revoke', str(UUID(int=0))], catch_exceptions=False)
        assert result.exit_code != 0
        assert "API key" in result.stderr
        assert "not found" in result.stderr
