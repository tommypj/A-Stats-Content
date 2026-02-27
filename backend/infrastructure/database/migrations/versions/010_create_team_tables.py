"""create team tables

Revision ID: 010_create_team_tables
Revises: 009
Create Date: 2026-02-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010_create_team_tables'
down_revision = '009'  # INFRA-06: points to 009 placeholder (was 008, gap fixed)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create team-related tables for multi-tenancy."""

    # Create teams table
    op.create_table(
        'teams',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False, primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False, unique=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('subscription_tier', sa.String(length=50), nullable=False, server_default='free'),
        sa.Column('subscription_status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('subscription_expires', sa.DateTime(timezone=True), nullable=True),
        sa.Column('lemonsqueezy_customer_id', sa.String(length=255), nullable=True, unique=True),
        sa.Column('lemonsqueezy_subscription_id', sa.String(length=255), nullable=True),
        sa.Column('max_members', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('articles_generated_this_month', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('outlines_generated_this_month', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('images_generated_this_month', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('usage_reset_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Create indexes for teams
    op.create_index('ix_teams_owner_id', 'teams', ['owner_id'])
    op.create_index('ix_teams_slug', 'teams', ['slug'])
    op.create_index('ix_teams_subscription', 'teams', ['subscription_tier', 'subscription_expires'])

    # Create team_members table
    op.create_table(
        'team_members',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False, primary_key=True),
        sa.Column('team_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='editor'),
        sa.Column('invited_by', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ondelete='SET NULL'),
    )

    # Create indexes for team_members
    op.create_index('ix_team_members_team_id', 'team_members', ['team_id'])
    op.create_index('ix_team_members_user_id', 'team_members', ['user_id'])
    op.create_index('ix_team_members_team_user', 'team_members', ['team_id', 'user_id'], unique=True)

    # Create team_invitations table
    op.create_table(
        'team_invitations',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False, primary_key=True),
        sa.Column('team_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('invited_by', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='editor'),
        sa.Column('token', sa.String(length=255), nullable=False, unique=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('accepted_by_user_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_by', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['accepted_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['revoked_by'], ['users.id'], ondelete='SET NULL'),
    )

    # Create indexes for team_invitations
    op.create_index('ix_team_invitations_team_id', 'team_invitations', ['team_id'])
    op.create_index('ix_team_invitations_email', 'team_invitations', ['email'])
    op.create_index('ix_team_invitations_token', 'team_invitations', ['token'])
    op.create_index('ix_team_invitations_status', 'team_invitations', ['status'])
    op.create_index('ix_team_invitations_expires_at', 'team_invitations', ['expires_at'])

    # Add current_team_id to users table
    op.add_column('users', sa.Column('current_team_id', postgresql.UUID(as_uuid=False), nullable=True))
    op.create_foreign_key(
        'fk_users_current_team_id',
        'users',
        'teams',
        ['current_team_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_users_current_team_id', 'users', ['current_team_id'])


def downgrade() -> None:
    """Drop team-related tables."""

    # Remove current_team_id from users
    op.drop_index('ix_users_current_team_id', table_name='users')
    op.drop_constraint('fk_users_current_team_id', 'users', type_='foreignkey')
    op.drop_column('users', 'current_team_id')

    # Drop team_invitations
    op.drop_index('ix_team_invitations_expires_at', table_name='team_invitations')
    op.drop_index('ix_team_invitations_status', table_name='team_invitations')
    op.drop_index('ix_team_invitations_token', table_name='team_invitations')
    op.drop_index('ix_team_invitations_email', table_name='team_invitations')
    op.drop_index('ix_team_invitations_team_id', table_name='team_invitations')
    op.drop_table('team_invitations')

    # Drop team_members
    op.drop_index('ix_team_members_team_user', table_name='team_members')
    op.drop_index('ix_team_members_user_id', table_name='team_members')
    op.drop_index('ix_team_members_team_id', table_name='team_members')
    op.drop_table('team_members')

    # Drop teams
    op.drop_index('ix_teams_subscription', table_name='teams')
    op.drop_index('ix_teams_slug', table_name='teams')
    op.drop_index('ix_teams_owner_id', table_name='teams')
    op.drop_table('teams')
