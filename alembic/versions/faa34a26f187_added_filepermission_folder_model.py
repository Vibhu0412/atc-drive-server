"""Added filepermission folder model

Revision ID: faa34a26f187
Revises: 657479dc8d8a
Create Date: 2025-02-15 14:08:52.804426

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'faa34a26f187'
down_revision: Union[str, None] = '657479dc8d8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_file_permissions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('file_id', sa.UUID(), nullable=False),
    sa.Column('can_view', sa.Boolean(), nullable=True),
    sa.Column('can_edit', sa.Boolean(), nullable=True),
    sa.Column('can_delete', sa.Boolean(), nullable=True),
    sa.Column('can_share', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['file_id'], ['files.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('user_file_permissions')
    # ### end Alembic commands ###
