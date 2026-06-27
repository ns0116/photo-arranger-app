import os
import shutil
import unittest
import tempfile
import hashlib
from app import safe_copy, safe_move, calculate_sha256, process_file_task, cancel_event

class TestPhotoArranger(unittest.TestCase):
    def setUp(self):
        self.src_dir = tempfile.TemporaryDirectory()
        self.dst_dir = tempfile.TemporaryDirectory()
        cancel_event.clear()

    def tearDown(self):
        self.src_dir.cleanup()
        self.dst_dir.cleanup()

    def create_dummy_file(self, dir_path, filename, content=b"dummy content"):
        filepath = os.path.join(dir_path, filename)
        with open(filepath, 'wb') as f:
            f.write(content)
        return filepath

    def test_calculate_sha256(self):
        content = b"test content for sha256"
        filepath = self.create_dummy_file(self.src_dir.name, "test.txt", content)
        expected_hash = hashlib.sha256(content).hexdigest()
        self.assertEqual(calculate_sha256(filepath), expected_hash)

    def test_safe_copy_success(self):
        src_file = self.create_dummy_file(self.src_dir.name, "test.jpg", b"jpeg_content")
        dst_file = os.path.join(self.dst_dir.name, "test.jpg")
        
        safe_copy(src_file, dst_file)
        
        self.assertTrue(os.path.exists(src_file))
        self.assertTrue(os.path.exists(dst_file))
        self.assertEqual(calculate_sha256(src_file), calculate_sha256(dst_file))
        # .tmpファイルが残っていないこと
        self.assertFalse(os.path.exists(dst_file + '.tmp'))

    def test_safe_move_success(self):
        src_file = self.create_dummy_file(self.src_dir.name, "test.jpg", b"jpeg_content")
        dst_file = os.path.join(self.dst_dir.name, "test.jpg")
        
        safe_move(src_file, dst_file)
        
        self.assertFalse(os.path.exists(src_file))
        self.assertTrue(os.path.exists(dst_file))
        self.assertFalse(os.path.exists(dst_file + '.tmp'))

    def test_safe_move_rollback_on_hash_mismatch(self):
        # ハッシュ不一致をシミュレートするため、コピー中に元ファイルが書き換えられた状況を再現
        src_file = self.create_dummy_file(self.src_dir.name, "test.jpg", b"initial_content")
        dst_file = os.path.join(self.dst_dir.name, "test.jpg")
        
        # shutil.copy2をモックして、コピーした後にソースファイルを書き換えることでハッシュ不一致を起こす
        original_copy2 = shutil.copy2
        def mock_copy2(src, dst):
            original_copy2(src, dst)
            with open(src, 'wb') as f:
                f.write(b"modified_content")
                
        shutil.copy2 = mock_copy2
        try:
            with self.assertRaises(IOError):
                safe_move(src_file, dst_file)
            
            # ロールバックにより、コピー先ファイルや一時ファイルは削除されているはず
            self.assertFalse(os.path.exists(dst_file))
            self.assertFalse(os.path.exists(dst_file + '.tmp'))
            # ソースファイルは（変更されてはいるが）削除されずに残っているはず
            self.assertTrue(os.path.exists(src_file))
        finally:
            shutil.copy2 = original_copy2

    def test_process_file_task_dry_run(self):
        src_file = self.create_dummy_file(self.src_dir.name, "test.jpg", b"content")
        res = process_file_task(
            s_dir=self.src_dir.name,
            filename="test.jpg",
            dst_dir=self.dst_dir.name,
            date_format="%Y-%m-%d",
            mode="move",
            dry_run=True
        )
        self.assertEqual(res['status'], 'success')
        self.assertEqual(res['action'], 'move')
        # ドライランなのでファイル移動は発生していないこと
        self.assertTrue(os.path.exists(src_file))
        # 宛先には何も作成されていないこと
        dst_folder = os.path.join(self.dst_dir.name, res['folder'])
        self.assertFalse(os.path.exists(os.path.join(dst_folder, "test.jpg")))

    def test_process_file_task_execution(self):
        src_file = self.create_dummy_file(self.src_dir.name, "test.jpg", b"content")
        res = process_file_task(
            s_dir=self.src_dir.name,
            filename="test.jpg",
            dst_dir=self.dst_dir.name,
            date_format="%Y-%m-%d",
            mode="move",
            dry_run=False
        )
        self.assertEqual(res['status'], 'success')
        self.assertTrue(res['copied'])
        
        # 実際に移動されていること
        self.assertFalse(os.path.exists(src_file))
        dst_folder = os.path.join(self.dst_dir.name, res['folder'])
        self.assertTrue(os.path.exists(os.path.join(dst_folder, "test.jpg")))

if __name__ == '__main__':
    unittest.main()
