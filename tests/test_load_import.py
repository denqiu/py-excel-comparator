import logging
import unittest

import load_comparators

logging.basicConfig(level=logging.INFO)


class LoadImport(unittest.TestCase):
    def test_load_import(self):
        load_comparators.prod()
        load_comparators.staging_1()
        load_comparators.staging_2()
        logging.info("Files loaded successfully!")


if __name__ == '__main__':
    unittest.main()
