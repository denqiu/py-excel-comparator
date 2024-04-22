import os
import logging
import unittest

import pandas

import load_comparators
from utils.comparator import DataFrameComparator

logging.basicConfig(level=logging.INFO)


class TestComparators(unittest.TestCase):
    def __init__(self):
        super().__init__()
        self.prod = pandas.DataFrame()
        self.staging_1 = pandas.DataFrame()
        self.staging_2 = pandas.DataFrame()

    def test_load_data(self):
        if os.path.exists(load_comparators.files_directory):
            self.prod = load_comparators.prod()
            self.staging_1 = load_comparators.staging_1()
            self.staging_2 = load_comparators.staging_2()
            logging.info("Files loaded successfully for testing purposes!")
        else:
            self.prod = DataFrameComparator(pandas.DataFrame({""}))
            logging.info("Cannot access files directory. Loaded data frames for testing purposes.")

    def test_comparison_functions(self):
        if os.path.exists(load_comparators.files_directory):



if __name__ == '__main__':
    unittest.main()
