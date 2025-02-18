"""Update art show special requests field

Revision ID: 116504357512
Revises: ddd4a1d727a6
Create Date: 2025-02-18 02:06:33.649112

"""


# revision identifiers, used by Alembic.
revision = '116504357512'
down_revision = 'ddd4a1d727a6'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa



try:
    is_sqlite = op.get_context().dialect.name == 'sqlite'
except Exception:
    is_sqlite = False

if is_sqlite:
    op.get_context().connection.execute('PRAGMA foreign_keys=ON;')
    utcnow_server_default = "(datetime('now', 'utc'))"
else:
    utcnow_server_default = "timezone('utc', current_timestamp)"

def sqlite_column_reflect_listener(inspector, table, column_info):
    """Adds parenthesis around SQLite datetime defaults for utcnow."""
    if column_info['default'] == "datetime('now', 'utc')":
        column_info['default'] = utcnow_server_default

sqlite_reflect_kwargs = {
    'listeners': [('column_reflect', sqlite_column_reflect_listener)]
}

# ===========================================================================
# HOWTO: Handle alter statements in SQLite
#
# def upgrade():
#     if is_sqlite:
#         with op.batch_alter_table('table_name', reflect_kwargs=sqlite_reflect_kwargs) as batch_op:
#             batch_op.alter_column('column_name', type_=sa.Unicode(), server_default='', nullable=False)
#     else:
#         op.alter_column('table_name', 'column_name', type_=sa.Unicode(), server_default='', nullable=False)
#
# ===========================================================================


def upgrade():
    op.add_column('art_show_application', sa.Column('special_requests', sa.Unicode(), server_default='', nullable=False))
    op.add_column('art_show_application', sa.Column('special_requests_text', sa.Unicode(), server_default='', nullable=False))
    op.drop_column('art_show_application', 'special_needs')


def downgrade():
    op.add_column('art_show_application', sa.Column('special_needs', sa.VARCHAR(), server_default=sa.text("''::character varying"), autoincrement=False, nullable=False))
    op.drop_column('art_show_application', 'special_requests_text')
    op.drop_column('art_show_application', 'special_requests')
