"""Test the filesystem utils of VaRA-TS."""
import errno
import os
import unittest
import uuid
from fcntl import flock, LOCK_EX, LOCK_NB, LOCK_UN

from varats.utils.filesystem_util import lock_file


class TestFileLock(unittest.TestCase):
    """Tests whether the lock context manager works correctly."""

    def test_file_locking(self):
        """Test that the file is locked when in a context manager."""
        tmp_lock_file = "/tmp/lock-test.lock"

        with lock_file(tmp_lock_file):
            # File should automatically be created
            self.assertTrue(os.path.exists(tmp_lock_file))

            f = os.open(tmp_lock_file, os.O_RDONLY)

            with self.assertRaises(OSError) as context:
                # A non-blocking attempt to lock the file again should fail immediately
                flock(f, LOCK_EX | LOCK_NB)
            os.close(f)
            self.assertEqual(context.exception.errno, errno.EWOULDBLOCK)

        # Attempting to lock the file and immediately unlocking should now work
        f = os.open(tmp_lock_file, os.O_RDONLY)
        flock(f, LOCK_EX | LOCK_NB)
        flock(f, LOCK_UN)
        os.close(f)

    def test_lock_file_new_folder(self):
        """Test that the lock context manager works correctly when the lock file
        is in a new folder."""
        tmp_lock_file = f"/tmp/{uuid.uuid4()}"

        while os.path.isdir(tmp_lock_file):
            tmp_lock_file = f"/tmp/{uuid.uuid4()}"

        tmp_lock_file += "/lock-test.lock"

        with lock_file(tmp_lock_file):
            # File should automatically be created
            self.assertTrue(os.path.exists(tmp_lock_file))
