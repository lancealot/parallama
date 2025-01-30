from datetime import datetime, timedelta
import pytest
from uuid import UUID, uuid4

from parallama.core.permissions import Permission, DefaultRoles
from parallama.models.role import Role
from parallama.models.user_role import UserRole
from parallama.services.role import RoleService
from parallama.core.exceptions import ResourceNotFoundError, DuplicateResourceError

@pytest.fixture
def role_service(db_session):
    """Create a role service instance with a database session."""
    return RoleService(db_session)

@pytest.fixture
def admin_role(role_service):
    """Create an admin role for testing."""
    return role_service.create_role(
        name="admin",
        permissions=DefaultRoles.ADMIN["permissions"],
        description="Admin role for testing"
    )

@pytest.fixture
def basic_role(role_service):
    """Create a basic role for testing."""
    return role_service.create_role(
        name="basic",
        permissions=DefaultRoles.BASIC["permissions"],
        description="Basic role for testing"
    )

class TestRoleService:
    def test_create_role(self, role_service):
        """Test creating a new role."""
        permissions = [Permission.USE_OLLAMA, Permission.BASIC_RATE_LIMITS]
        role = role_service.create_role(
            name="test_role",
            permissions=permissions,
            description="Test role"
        )

        assert role.name == "test_role"
        assert role.description == "Test role"
        assert set(role.get_permissions()) == set(permissions)

    def test_create_duplicate_role(self, role_service, admin_role):
        """Test that creating a duplicate role raises an error."""
        with pytest.raises(DuplicateResourceError):
            role_service.create_role(
                name="admin",
                permissions=DefaultRoles.ADMIN["permissions"]
            )

    def test_get_role(self, role_service, admin_role):
        """Test retrieving a role by ID."""
        retrieved_role = role_service.get_role(admin_role.id)
        assert retrieved_role.id == admin_role.id
        assert retrieved_role.name == admin_role.name

    def test_get_nonexistent_role(self, role_service):
        """Test retrieving a nonexistent role returns None."""
        nonexistent_id = uuid4()
        assert role_service.get_role(nonexistent_id) is None

    def test_get_role_by_name(self, role_service, admin_role):
        """Test retrieving a role by name."""
        retrieved_role = role_service.get_role_by_name("admin")
        assert retrieved_role.id == admin_role.id
        assert retrieved_role.name == "admin"

    def test_assign_role_to_user(self, role_service, admin_role):
        """Test assigning a role to a user."""
        user_id = uuid4()
        user_role = role_service.assign_role_to_user(user_id, admin_role.id)
        
        assert user_role.user_id == user_id
        assert user_role.role_id == admin_role.id
        assert user_role.assigned_by is None
        assert user_role.expires_at is None

    def test_assign_role_with_expiry(self, role_service, admin_role):
        """Test assigning a role with an expiration date."""
        user_id = uuid4()
        expires_at = datetime.utcnow() + timedelta(days=30)
        
        user_role = role_service.assign_role_to_user(
            user_id, 
            admin_role.id,
            expires_at=expires_at
        )
        
        assert user_role.expires_at == expires_at
        assert not user_role.is_expired()

    def test_assign_nonexistent_role(self, role_service):
        """Test that assigning a nonexistent role raises an error."""
        with pytest.raises(ResourceNotFoundError):
            role_service.assign_role_to_user(uuid4(), uuid4())

    def test_assign_duplicate_role(self, role_service, admin_role):
        """Test that assigning a duplicate role raises an error."""
        user_id = uuid4()
        role_service.assign_role_to_user(user_id, admin_role.id)
        
        with pytest.raises(DuplicateResourceError):
            role_service.assign_role_to_user(user_id, admin_role.id)

    def test_remove_role_from_user(self, role_service, admin_role):
        """Test removing a role from a user."""
        user_id = uuid4()
        role_service.assign_role_to_user(user_id, admin_role.id)
        
        # Remove the role
        role_service.remove_role_from_user(user_id, admin_role.id)
        
        # Check that user's roles are empty
        assert role_service.get_user_roles(user_id) == []

    def test_get_user_roles(self, role_service, admin_role, basic_role):
        """Test getting all roles for a user."""
        user_id = uuid4()
        role_service.assign_role_to_user(user_id, admin_role.id)
        role_service.assign_role_to_user(user_id, basic_role.id)
        
        roles = role_service.get_user_roles(user_id)
        role_names = {role.name for role in roles}
        
        assert len(roles) == 2
        assert role_names == {"admin", "basic"}

    def test_get_user_roles_with_expired(self, role_service, admin_role):
        """Test that expired roles are not returned."""
        user_id = uuid4()
        expires_at = datetime.utcnow() - timedelta(days=1)  # Expired yesterday
        
        role_service.assign_role_to_user(
            user_id,
            admin_role.id,
            expires_at=expires_at
        )
        
        assert role_service.get_user_roles(user_id) == []

    def test_check_permission(self, role_service, admin_role):
        """Test checking permissions for a user."""
        user_id = uuid4()
        role_service.assign_role_to_user(user_id, admin_role.id)
        
        # Admin should have MANAGE_USERS permission
        assert role_service.check_permission(user_id, Permission.MANAGE_USERS)
        # Admin should not have a non-existent permission
        assert not role_service.check_permission(user_id, "nonexistent_permission")

    def test_initialize_default_roles(self, role_service):
        """Test initializing default roles."""
        role_service.initialize_default_roles()
        
        # Check that all default roles exist
        for role_name in DefaultRoles.get_all_roles():
            role = role_service.get_role_by_name(role_name)
            assert role is not None
            assert role.name == role_name

        # Check that initializing again doesn't create duplicates
        role_service.initialize_default_roles()
        assert len(role_service.db.query(Role).all()) == len(DefaultRoles.get_all_roles())
