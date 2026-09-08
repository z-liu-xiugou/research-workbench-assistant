import hashlib
import unittest
import test_workbench
from unittest.mock import patch

wb = test_workbench.wb


class BackupTests(unittest.TestCase):
    setUp = test_workbench.WorkbenchTests.setUp

    def snapshot(self):
        archive = self.base / "snapshot.json"
        wb.backup(self.root, archive)
        return archive

    def test_roundtrip_preserves_history_and_manual_notes(self):
        first = wb.record(self.root, self.data)
        wb.record(self.root, dict(self.data, supersedes=first, body="新版"))
        (self.root / "PERSONAL_NOTES.md").write_bytes("手写\r\n中文".encode("utf-8"))
        target = self.base / "恢复 项目"
        wb.restore(self.snapshot(), target)
        self.assertEqual(wb.load(self.root), wb.load(target))
        self.assertEqual((self.root / "PERSONAL_NOTES.md").read_bytes(), (target / "PERSONAL_NOTES.md").read_bytes())
        self.assertEqual(wb.audit(target)["stale_views"], [])
        self.assertEqual((target / ".gitignore").read_text(), "*\n!.gitignore\n")

    def test_backup_never_overwrites(self):
        archive = self.snapshot()
        old = archive.read_bytes()
        with self.assertRaises(FileExistsError):
            wb.backup(self.root, archive)
        self.assertEqual(old, archive.read_bytes())

    def test_restore_never_overwrites(self):
        archive = self.snapshot()
        with self.assertRaises(ValueError):
            wb.restore(archive, self.root)

    def test_tampering_rejected_before_creating_target(self):
        archive = self.snapshot()
        payload = wb.read_json(archive)
        payload["files"]["config.json"]["text"] = "changed"
        archive.write_text(wb.encode(payload), encoding="utf-8")
        target = self.base / "restored"
        with self.assertRaises(ValueError):
            wb.restore(archive, target)
        self.assertFalse(target.exists())

    def test_path_traversal_and_unknown_files_rejected(self):
        archive = self.snapshot()
        original = wb.read_json(archive)
        for name in ("../escape", "/absolute", "events/../../bad", "events\\bad.json", ".env", "config.json/child"):
            payload = wb.json.loads(wb.encode(original))
            payload["files"][name] = {"text": "x", "sha256": hashlib.sha256(b"x").hexdigest()}
            archive.write_text(wb.encode(payload), encoding="utf-8")
            with self.subTest(name=name), self.assertRaises(ValueError):
                wb.restore(archive, self.base / "restored")
        self.assertFalse((self.base / "restored").exists())

    def test_does_not_include_extra_user_files(self):
        (self.root / ".env").write_text("secret", encoding="utf-8")
        (self.root / "paper.pdf").write_bytes(b"private")
        payload = wb.read_json(self.snapshot())
        self.assertNotIn(".env", payload["files"])
        self.assertNotIn("paper.pdf", payload["files"])
        self.assertNotIn("ACTIVE_CONTEXT.md", payload["files"])

    def test_corrupt_structure_with_valid_hash_rejected(self):
        archive = self.snapshot()
        payload = wb.read_json(archive)
        payload["files"]["config.json"] = {"text": "{}", "sha256": hashlib.sha256(b"{}").hexdigest()}
        archive.write_text(wb.encode(payload), encoding="utf-8")
        with self.assertRaises(ValueError):
            wb.restore(archive, self.base / "restored")
        self.assertFalse((self.base / "restored").exists())

    def test_backup_inside_root_and_lock_conflict_rejected(self):
        with self.assertRaises(ValueError):
            wb.backup(self.root, self.root / "snapshot.json")
        with wb.locked(self.root), self.assertRaises(ValueError):
            self.snapshot()

    def test_size_limit(self):
        archive = self.snapshot()
        with patch.object(wb, "BACKUP_LIMIT", 1), self.assertRaises(ValueError):
            wb.restore(archive, self.base / "restored")

    def test_missing_events_cannot_be_backed_up_as_empty(self):
        (self.root / "events").rmdir()
        with self.assertRaises(ValueError):
            self.snapshot()
        self.assertFalse((self.base / "snapshot.json").exists())
