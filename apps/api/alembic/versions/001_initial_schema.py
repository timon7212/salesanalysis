"""initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # KommoConnection
    op.create_table(
        'kommo_connections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('base_url', sa.String(), nullable=False),
        sa.Column('client_id', sa.String(), nullable=False),
        sa.Column('client_secret', sa.String(), nullable=False),
        sa.Column('redirect_uri', sa.String(), nullable=False),
        sa.Column('access_token_enc', sa.Text(), nullable=True),
        sa.Column('refresh_token_enc', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kommo_connections_id'), 'kommo_connections', ['id'], unique=False)
    
    # LeadCache
    op.create_table(
        'lead_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lead_id', sa.BigInteger(), nullable=False),
        sa.Column('payload_json', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lead_id')
    )
    op.create_index(op.f('ix_lead_cache_id'), 'lead_cache', ['id'], unique=False)
    op.create_index(op.f('ix_lead_cache_lead_id'), 'lead_cache', ['lead_id'], unique=True)
    
    # Upload
    op.create_table(
        'uploads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lead_id', sa.BigInteger(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('mime', sa.String(), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('storage_path', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_uploads_id'), 'uploads', ['id'], unique=False)
    op.create_index(op.f('ix_uploads_lead_id'), 'uploads', ['lead_id'], unique=False)
    
    # Job
    op.create_table(
        'jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lead_id', sa.BigInteger(), nullable=False),
        sa.Column('upload_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='queued'),
        sa.Column('progress_step', sa.String(), nullable=True),
        sa.Column('transcript_path', sa.String(), nullable=True),
        sa.Column('transcript_json', sa.Text(), nullable=True),
        sa.Column('extraction_json', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pushed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['upload_id'], ['uploads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_jobs_id'), 'jobs', ['id'], unique=False)
    op.create_index(op.f('ix_jobs_lead_id'), 'jobs', ['lead_id'], unique=False)
    
    # FieldMapping
    op.create_table(
        'field_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('mapping_json', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_field_mappings_id'), 'field_mappings', ['id'], unique=False)


def downgrade() -> None:
    op.drop_table('field_mappings')
    op.drop_table('jobs')
    op.drop_table('uploads')
    op.drop_table('lead_cache')
    op.drop_table('kommo_connections')








