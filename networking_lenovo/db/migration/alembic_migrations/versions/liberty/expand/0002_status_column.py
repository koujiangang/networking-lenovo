# Copyright (c) 2017, Lenovo. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
