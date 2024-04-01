import logging
import unittest

logging.basicConfig(level=logging.INFO)


class LoadImport(unittest.TestCase):
    def test_load_import(self):
        import load_files
        logging.info("Files loaded successfully!")


if __name__ == '__main__':
    unittest.main()
