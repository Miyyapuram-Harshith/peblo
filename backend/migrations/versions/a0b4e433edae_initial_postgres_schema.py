"""initial_postgres_schema

Revision ID: a0b4e433edae
Revises: 
Create Date: 2026-09-07 00:25:38.998361
"""
from __future__ import annotations
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'a0b4e433edae'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enums
    user_role = sa.Enum('EDITOR', 'ADMIN', name='userrole')
    content_status = sa.Enum('DRAFT', 'PUBLISHED', 'ARCHIVED', name='contentstatus')
    artwork_type = sa.Enum('POSTER', 'BANNER', 'THUMBNAIL', name='artworktype')
    owner_type = sa.Enum('SHOW', 'EPISODE', name='ownertype')
    publish_status = sa.Enum('PENDING', 'VALIDATING', 'BUILDING', 'STORING', 'ACTIVATING', 'SUCCESS', 'FAILED_VALIDATION', 'FAILED_BUILD', 'FAILED_STORAGE', 'FAILED_ACTIVATION', name='publishstatus')



    # active_catalogue
    op.create_table('active_catalogue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('active_catalogue_key', sa.String(length=500), nullable=False),
        sa.Column('active_catalogue_hash', sa.String(length=64), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # users
    op.create_table('users',
        sa.Column('id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', user_role, nullable=False, create_type=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # shows
    op.create_table('shows',
        sa.Column('id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('slug', sa.String(length=500), nullable=False),
        sa.Column('synopsis', sa.Text(), nullable=True),
        sa.Column('section', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('status', content_status, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_shows_category'), 'shows', ['category'], unique=False)
    op.create_index(op.f('ix_shows_section'), 'shows', ['section'], unique=False)
    op.create_index(op.f('ix_shows_slug'), 'shows', ['slug'], unique=True)
    op.create_index(op.f('ix_shows_status'), 'shows', ['status'], unique=False)

    # artwork
    op.create_table('artwork',
        sa.Column('id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('owner_type', owner_type, nullable=False),
        sa.Column('owner_id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('artwork_type', artwork_type, nullable=False),
        sa.Column('storage_key', sa.String(length=500), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('width', sa.Integer(), nullable=False),
        sa.Column('height', sa.Integer(), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('owner_type', 'owner_id', 'artwork_type', name='uq_artwork_owner_type'),
        sa.UniqueConstraint('storage_key')
    )
    op.create_index(op.f('ix_artwork_owner'), 'artwork', ['owner_type', 'owner_id'], unique=False)

    # publish_runs
    op.create_table('publish_runs',
        sa.Column('id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('triggered_by', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', publish_status, nullable=False),
        sa.Column('catalogue_key', sa.String(length=500), nullable=True),
        sa.Column('catalogue_hash', sa.String(length=64), nullable=True),
        sa.Column('shows_count', sa.Integer(), nullable=True),
        sa.Column('episodes_count', sa.Integer(), nullable=True),
        sa.Column('language_group_count', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('error_code', sa.String(length=100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['triggered_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key')
    )
    op.create_index(op.f('ix_publish_runs_created_at'), 'publish_runs', ['created_at'], unique=False)
    op.create_index(op.f('ix_publish_runs_status'), 'publish_runs', ['status'], unique=False)

    # seasons
    op.create_table('seasons',
        sa.Column('id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('show_id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('season_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['show_id'], ['shows.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('show_id', 'season_number', name='uq_season_show_number')
    )
    op.create_index(op.f('ix_seasons_show_id'), 'seasons', ['show_id'], unique=False)

    # episodes
    op.create_table('episodes',
        sa.Column('id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('season_id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('synopsis', sa.Text(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('language', sa.String(length=50), nullable=False),
        sa.Column('content_group', sa.String(length=255), nullable=False),
        sa.Column('video_url', sa.String(length=2000), nullable=True),
        sa.Column('status', content_status, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['season_id'], ['seasons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('content_group', 'language', name='uq_episode_content_group_language')
    )
    op.create_index(op.f('ix_episodes_content_group'), 'episodes', ['content_group'], unique=False)
    op.create_index(op.f('ix_episodes_language'), 'episodes', ['language'], unique=False)
    op.create_index(op.f('ix_episodes_season_id'), 'episodes', ['season_id'], unique=False)
    op.create_index(op.f('ix_episodes_status'), 'episodes', ['status'], unique=False)


def downgrade() -> None:
    op.drop_table('episodes')
    op.drop_table('seasons')
    op.drop_table('publish_runs')
    op.drop_table('artwork')
    op.drop_table('shows')
    op.drop_table('users')
    op.drop_table('active_catalogue')

    sa.Enum(name='userrole').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='contentstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='artworktype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='ownertype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='publishstatus').drop(op.get_bind(), checkfirst=True)
