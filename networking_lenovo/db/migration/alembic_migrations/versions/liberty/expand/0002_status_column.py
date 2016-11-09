"""Synchronization data between pre and post commit port update

Revision ID: 0002
Revises: None
Create Date: 2016-11-03 12:40:55.209525

"""

from neutron.db.migration import cli


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column(
        'lenovo_ml2_nosport_bindings',
        sa.Column('processed', sa.Boolean(), nullable=False)
    )
