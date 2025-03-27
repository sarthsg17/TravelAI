from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic
revision = 'c7d092871895'
down_revision = '6a4dc7679ab5'
branch_labels = None
depends_on = None

def upgrade():
    # Add a UNIQUE constraint to the username column
    op.create_unique_constraint("uq_user_preference_username", "user_preferences", ["username"])

def downgrade():
    # Remove the UNIQUE constraint if we roll back
    op.drop_constraint("uq_user_preference_username", "user_preferences", type_="unique")
