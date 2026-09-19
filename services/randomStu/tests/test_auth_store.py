import tempfile
import unittest
from pathlib import Path

from services.randomStu.auth import hash_password, verify_password
from services.randomStu.store import RandomStuStore, RevisionConflictError


def sample_data(name="一班"):
    return {
        "version": 1,
        "activeClassroomId": "class-1",
        "classrooms": [
            {
                "id": "class-1",
                "name": name,
                "students": [
                    {"id": "student-1", "number": "001", "name": "张三", "enabled": True}
                ],
                "locked": False,
                "createdAt": "2026-01-01T00:00:00Z",
                "updatedAt": "2026-01-01T00:00:00Z",
            }
        ],
    }


class AuthAndStoreTests(unittest.TestCase):
    def test_password_hash_verifies_without_storing_plaintext(self):
        encoded = hash_password("correct password", iterations=1_000)
        self.assertNotIn("correct password", encoded)
        self.assertTrue(verify_password("correct password", encoded))
        self.assertFalse(verify_password("wrong password", encoded))

    def test_state_round_trip_and_revision_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RandomStuStore(Path(directory) / "state.sqlite3")
            empty = store.get_state()
            self.assertIsNone(empty.data)
            self.assertEqual(empty.revision, 0)

            saved = store.save_state(sample_data(), 0)
            self.assertEqual(saved.revision, 1)
            self.assertEqual(store.get_state().data["classrooms"][0]["name"], "一班")

            with self.assertRaises(RevisionConflictError):
                store.save_state(sample_data("二班"), 0)

    def test_session_can_be_created_and_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RandomStuStore(Path(directory) / "state.sqlite3")
            token = store.create_session()
            self.assertTrue(store.has_session(token))
            store.delete_session(token)
            self.assertFalse(store.has_session(token))


if __name__ == "__main__":
    unittest.main()
