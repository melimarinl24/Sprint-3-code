"""Add unique constraints to Users table"""

from alembic import op
import sqlalchemy as sa


revision = '3e2f1c1b89da'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Define each unique constraint safely
    constraints = [
        ('uq_users_email', 'Users', 'email'),
        ('uq_users_nshe', 'Users', 'nshe_id'),
        ('uq_users_employee', 'Users', 'employee_id')
    ]

    for name, table, column in constraints:
        try:
            conn.execute(sa.text(f"ALTER TABLE `{table}` ADD CONSTRAINT {name} UNIQUE ({column})"))
        except Exception as e:
            # Skip if it already exists
            if "Duplicate key name" in str(e) or "already exists" in str(e):
                print(f"Skipping {name}, already exists.")
            else:
                raise e


def downgrade():
    conn = op.get_bind()

    for name in ['uq_users_email', 'uq_users_nshe', 'uq_users_employee']:
        try:
            conn.execute(sa.text(f"ALTER TABLE `Users` DROP INDEX {name}"))
        except Exception as e:
            if "check that column/key exists" in str(e):
                print(f"Skipping drop for {name}, not found.")
            else:
                raise e
