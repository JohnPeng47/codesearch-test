"""Changed CowboyUsers table

Revision ID: 50c4f4a1bd1a
Revises: e63f0f3ddd8b
Create Date: 2024-04-19 22:33:56.432302

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '50c4f4a1bd1a'
down_revision: Union[str, None] = 'e63f0f3ddd8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
