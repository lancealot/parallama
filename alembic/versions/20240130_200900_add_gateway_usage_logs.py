"""add gateway usage logs

Revision ID: 20240130_200900
Revises: 20240130_121300
Create Date: 2024-01-30 20:09:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '20240130_200900'
down_revision = '20240130_121300'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create gateway_usage_logs table
    op.create_table(
        'gateway_usage_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('gateway_type', sa.String(50), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('endpoint', sa.String(255), nullable=False),
        sa.Column('model_name', sa.String(255)),
        sa.Column('tokens_used', sa.Integer()),
        sa.Column('request_duration', sa.Integer()),  # Duration in milliseconds
        sa.Column('status_code', sa.Integer()),
        sa.Column('error_message', sa.String()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Create indexes for common query patterns
    op.create_index('ix_gateway_usage_logs_user_id', 'gateway_usage_logs', ['user_id'])
    op.create_index('ix_gateway_usage_logs_gateway_type', 'gateway_usage_logs', ['gateway_type'])
    op.create_index('ix_gateway_usage_logs_timestamp', 'gateway_usage_logs', ['timestamp'])
    op.create_index('ix_gateway_usage_logs_model_name', 'gateway_usage_logs', ['model_name'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_gateway_usage_logs_model_name')
    op.drop_index('ix_gateway_usage_logs_timestamp')
    op.drop_index('ix_gateway_usage_logs_gateway_type')
    op.drop_index('ix_gateway_usage_logs_user_id')
    
    # Drop the table
    op.drop_table('gateway_usage_logs')
