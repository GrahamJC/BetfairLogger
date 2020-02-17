"""Add back/lay prices

Revision ID: f3534373006c
Revises: 48e5cfc5a5c1
Create Date: 2020-02-12 08:37:09.760066

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3534373006c'
down_revision = '48e5cfc5a5c1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('market_runner_book', sa.Column('back_price', sa.Float(), nullable=True))
    op.add_column('market_runner_book', sa.Column('lay_price', sa.Float(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('market_runner_book', 'lay_price')
    op.drop_column('market_runner_book', 'back_price')
    # ### end Alembic commands ###
