"""даление категории

Revision ID: 746ff35f6342
Revises: 
Create Date: 2024-12-11 06:09:57.509280

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '746ff35f6342'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('category')
    with op.batch_alter_table('entry', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('category_id')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('entry', schema=None) as batch_op:
        batch_op.add_column(sa.Column('category_id', sa.INTEGER(), nullable=True))
        batch_op.create_foreign_key(None, 'category', ['category_id'], ['id'])

    op.create_table('category',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('name', sa.VARCHAR(length=100), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    # ### end Alembic commands ###
