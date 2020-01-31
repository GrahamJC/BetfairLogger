"""Add order matched date

Revision ID: e3d63109ee6d
Revises: 3bfc1f93128b
Create Date: 2020-01-28 21:41:53.845170

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3d63109ee6d'
down_revision = '3bfc1f93128b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('market_runner_order', sa.Column('matched_date', sa.DateTime(), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('market_runner_order', 'matched_date')
    # ### end Alembic commands ###
