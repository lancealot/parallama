"""Initial database schema."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20240130_121200'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Create initial tables."""
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False, server_default='basic'),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('username', name='uq_users_username')
    )
    op.create_index('ix_users_username', 'users', ['username'])

    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key_hash', sa.String(), nullable=False),
        sa.Column('description', sa.String()),
        sa.Column('revoked_at', sa.DateTime(timezone=True)),
        sa.Column('last_used_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'])
    op.create_index('ix_api_keys_user_id', 'api_keys', ['user_id'])

    # Create refresh_tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.String(), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True)),
        sa.Column('replaced_by_id', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['replaced_by_id'], ['refresh_tokens.id'])
    )
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'])
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])

    # Create gateway_rate_limits table
    op.create_table(
        'gateway_rate_limits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('gateway_type', sa.String(), nullable=False),
        sa.Column('token_limit_hourly', sa.Integer()),
        sa.Column('token_limit_daily', sa.Integer()),
        sa.Column('request_limit_hourly', sa.Integer()),
        sa.Column('request_limit_daily', sa.Integer()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'gateway_type', name='uq_user_gateway_limit')
    )
    op.create_index('ix_gateway_rate_limits_user_id', 'gateway_rate_limits', ['user_id'])
    op.create_index('ix_gateway_rate_limits_gateway_type', 'gateway_rate_limits', ['gateway_type'])

def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('gateway_rate_limits')
    op.drop_table('refresh_tokens')
    op.drop_table('api_keys')
    op.drop_table('users')
