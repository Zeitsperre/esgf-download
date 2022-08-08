"""init tables

Revision ID: 4.0.0
Revises:
Create Date: 2022-08-08 16:12:36.535701

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4.0.0"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "file",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Text(), nullable=False),
        sa.Column("dataset_id", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("version", sa.String(length=16), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("local_path", sa.String(length=255), nullable=True),
        sa.Column("data_node", sa.String(length=40), nullable=True),
        sa.Column("checksum", sa.String(length=64), nullable=True),
        sa.Column("checksum_type", sa.String(length=16), nullable=True),
        sa.Column("size", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "deleted",
                "done",
                "error",
                "new",
                "paused",
                "running",
                "waiting",
                name="status",
            ),
            nullable=True,
        ),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_id"),
    )
    op.create_table(
        "param",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "value"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("param")
    op.drop_table("file")
    # ### end Alembic commands ###
