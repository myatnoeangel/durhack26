import os
from pathlib import Path
import psycopg
from dotenv import load_dotenv

# Load .env from the database directory
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)


def get_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL is missing from .env")

    return psycopg.connect(database_url)