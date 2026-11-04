
import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

# Load environment variables from backend/.env
load_dotenv()

config = context.config

# Use DATABASE_URL from the backend environment
database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError(
        "DATABASE_URL is not set. Check your backend/.env file."
    )

config.set_main_option(
    "sqlalchemy.url",
    database_url.replace("%", "%%")
)

# Configure logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import the shared SQLAlchemy Base
from app.database import Base

# Import all models to register their tables in Base.metadata
from app.models.topic import Topic
from app.models.content_item import ContentItem
from app.models.approval import Approval
from app.models.job import Job
from app.models.topic_chat import TopicChat
from app.models.content_draft import ContentDraft
from app.models.template import Template
from app.models.media_asset import MediaAsset
from app.models.organisation import Organisation
from app.models.brand import Brand
from app.models.tone import Tone
from app.models.org_profile import OrgBusinessInfo
from app.models.template_segment import TemplateSegment

# Add all other current models here, including Organisation and Brand.
# Example:
# from app.models.organisation import Organisation
# from app.models.brand import Brand

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
