import tempfile
from pathlib import Path

import pytest

from db import delete_user_memory, get_user_memory, init_db, save_user_memory


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_memory.db"
        init_db(db_path)
        yield db_path


def test_save_and_get_user_memory(temp_db):
    user_id = "ramesh"
    name = "Ramesh"
    facts = {
        "current_level": "Class 10 Math",
        "topics_covered": ["Quadratic Equations", "Photosynthesis"],
        "mistakes_made": ["Minus sign error"],
    }

    saved = save_user_memory(
        user_id=user_id,
        name=name,
        language_preference="Tenglish",
        facts=facts,
        db_path=temp_db,
    )

    assert saved["user_id"] == "ramesh"
    assert saved["name"] == "Ramesh"
    assert saved["facts"]["current_level"] == "Class 10 Math"

    retrieved = get_user_memory(user_id="ramesh", db_path=temp_db)
    assert retrieved is not None
    assert retrieved["name"] == "Ramesh"
    assert retrieved["facts"]["topics_covered"] == [
        "Quadratic Equations",
        "Photosynthesis",
    ]


def test_update_user_memory(temp_db):
    save_user_memory(
        user_id="priya",
        name="Priya",
        facts={
            "current_level": "Class 9 Science",
            "topics_covered": ["Cell structure"],
        },
        db_path=temp_db,
    )

    updated = save_user_memory(
        user_id="priya",
        name="Priya",
        facts={
            "current_level": "Class 9 Science",
            "topics_covered": ["Cell structure", "Tissue"],
        },
        db_path=temp_db,
    )

    assert updated["facts"]["topics_covered"] == ["Cell structure", "Tissue"]


def test_delete_user_memory(temp_db):
    save_user_memory(
        user_id="suresh",
        name="Suresh",
        facts={"current_level": "Class 8"},
        db_path=temp_db,
    )

    deleted = delete_user_memory(user_id="suresh", db_path=temp_db)
    assert deleted is True

    retrieved = get_user_memory(user_id="suresh", db_path=temp_db)
    assert retrieved is None


def test_get_nonexistent_user(temp_db):
    retrieved = get_user_memory(user_id="unknown_user", db_path=temp_db)
    assert retrieved is None
