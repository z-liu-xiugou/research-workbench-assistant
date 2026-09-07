"""公开树基本回归：防止已知私有目录、缓存和密钥文件被跟踪。"""
from pathlib import Path
import subprocess
import unittest


class PublicBoundaryTests(unittest.TestCase):
    def test_tracked_files_exclude_private_material(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(['git', 'ls-files', '-z'], cwd=root, capture_output=True, check=True)
        names = result.stdout.decode('utf-8').split('\0')
        forbidden = []
        for name in filter(None, names):
            parts = Path(name).parts
            if ('_private_reference' in parts or '__pycache__' in parts or
                    Path(name).suffix.lower() in {'.pdf', '.caj', '.pem', '.key'} or
                    Path(name).name == '.env'):
                forbidden.append(name)
        self.assertEqual(forbidden, [], 'Tracked private files; this check is not a full secret scanner')
