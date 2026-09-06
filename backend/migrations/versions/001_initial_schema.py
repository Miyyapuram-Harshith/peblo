"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('editor', 'admin', name='userrole'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Shows
    op.create_table(
        'shows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('slug', sa.String(500), unique=True, nullable=False, index=True),
        sa.Column('synopsis', sa.Text, nullable=True),
        sa.Column('section', sa.String(100), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('status', sa.Enum('draft', 'published', 'archived', name='contentstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_shows_status', 'shows', ['status'])
    op.create_index('ix_shows_section', 'shows', ['section'])
    op.create_index('ix_shows_category', 'shows', ['category'])

    # Seasons
    op.create_table(
        'seasons',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('show_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shows.id', ondelete='CASCADE'), nullable=False),
        sa.Column('season_number', sa.Integer, nullable=False),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_seasons_show_id', 'seasons', ['show_id'])
    op.create_unique_constraint('uq_season_show_number', 'seasons', ['show_id', 'season_number'])

    # Episodes
    op.create_table(
        'episodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('season_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('seasons.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('synopsis', sa.Text, nullable=True),
        sa.Column('duration_seconds', sa.Integer, nullable=True),
        sa.Column('language', sa.String(50), nullable=False),
        sa.Column('content_group', sa.String(255), nullable=False),
        sa.Column('video_url', sa.String(2000), nullable=True),
        sa.Column('status', sa.Enum('draft', 'published', 'archived', name='contentstatus', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_episodes_season_id', 'episodes', ['season_id'])
    op.create_index('ix_episodes_content_group', 'episodes', ['content_group'])
    op.create_index('ix_episodes_language', 'episodes', ['language'])
    op.create_index('ix_episodes_status', 'episodes', ['status'])
    op.create_unique_constraint('uq_episode_content_group_language', 'episodes', ['content_group', 'language'])

    # Artwork
    op.create_table(
        'artwork',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('owner_type', sa.Enum('show', 'episode', name='ownertype'), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('artwork_type', sa.Enum('poster', 'banner', 'thumbnail', name='artworktype'), nullable=False),
        sa.Column('storage_key', sa.String(500), unique=True, nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('width', sa.Integer, nullable=False),
        sa.Column('height', sa.Integer, nullable=False),
        sa.Column('size_bytes', sa.Integer, nullable=False),
        sa.Column('sha256', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_artwork_owner', 'artwork', ['owner_type', 'owner_id'])
    op.create_unique_constraint('uq_artwork_owner_type', 'artwork', ['owner_type', 'owner_id', 'artwork_type'])

    # Publish Runs
    op.create_table(
        'publish_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('triggered_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('idempotency_key', sa.String(255), unique=True, nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.Enum('pending', 'validating', 'building', 'storing', 'activating', 'success',
                                     'failed_validation', 'failed_build', 'failed_storage', 'failed_activation',
                                     name='publishstatus'), nullable=False),
        sa.Column('catalogue_key', sa.String(500), nullable=True),
        sa.Column('catalogue_hash', sa.String(64), nullable=True),
        sa.Column('shows_count', sa.Integer, nullable=True),
        sa.Column('episodes_count', sa.Integer, nullable=True),
        sa.Column('language_group_count', sa.Integer, nullable=True),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('error_code', sa.String(100), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_publish_runs_status', 'publish_runs', ['status'])
    op.create_index('ix_publish_runs_created_at', 'publish_runs', ['created_at'])

    # Active Catalogue
    op.create_table(
        'active_catalogue',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('active_catalogue_key', sa.String(500), nullable=False),
        sa.Column('active_catalogue_hash', sa.String(64), nullable=False),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('active_catalogue')
    op.drop_table('publish_runs')
    op.drop_table('artwork')
    op.drop_table('episodes')
    op.drop_table('seasons')
    op.drop_table('shows')
    op.drop_table('users')
