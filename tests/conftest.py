import pathlib
import pytest
from src.app.db.database import Database, apply_schema, load_schema_text


@pytest.fixture
def db_session():
    """Provides a fresh in-memory SQLite database connection initialized with schema."""
    schema_path = pathlib.Path(__file__).parent.parent / "src" / "app" / "db" / "schema.sql"
    db = Database(":memory:")
    conn = db.connect()
    schema_text = load_schema_text(schema_path)
    apply_schema(conn, schema_text)
    yield conn
    conn.close()
