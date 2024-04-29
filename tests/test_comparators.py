import os
import logging
import unittest

import numpy
import pandas

from load_comparators import files_directory, json_directory, is_remote, load_prod, load_staging_1, load_staging_2
from utils.comparator import DataFrameComparator

logging.basicConfig(level=logging.INFO)


class TestComparators(unittest.TestCase):
    """
    See "adjacent.count_adjacent_elements" to re-create test data via arrays instead of excel files (for remote).

    Arrays are then placed inside JSON files.
    """

    def __init__(self, methodName="test"):
        super().__init__(methodName=methodName)
        self.prod = DataFrameComparator(pandas.DataFrame())
        self.staging_1 = DataFrameComparator(pandas.DataFrame())
        self.staging_2 = DataFrameComparator(pandas.DataFrame())

    def _create_comparator(self, json_path: str):
        """
        Ref: remote_comparator.json.example
        """
        json_df = pandas.read_json(os.path.join(json_directory, json_path))

        def create_mask(level_1_term: str, level_2_term: str = None) -> numpy.ndarray:
            return json_df.loc[level_1_term].map(
                lambda d: type(d) is dict and (level_2_term in d if level_2_term else True)).to_numpy()

        # numpy.arange on range
        mask = create_mask(level_1_term="values", level_2_term="range")
        json_df.loc["values", mask].map(lambda d: d.update({
            "range": numpy.arange(*d["range"].values())
        }))

        # numpy.concatenate on order
        mask = create_mask(level_1_term="values", level_2_term="order")
        json_df.loc["values", mask].map(lambda d: d.update({
            "list": numpy.concatenate([d.pop(key) for key in d.pop("order")])
        }))

        # Every key except prefix should be a list. Concatenate them.
        mask = create_mask(level_1_term="values")

        def updater(d: dict):
            keys = [key for key in d.keys() if key != "prefix"]
            d.update({"list": numpy.concatenate([d.pop(key) for key in keys])})

        json_df.loc["values", mask].map(updater)

        # numpy.repeat where "counts" at Level 1 has "values" and "counts".
        mask = create_mask(level_1_term="counts", level_2_term="counts")
        json_df.loc["counts", mask].map(lambda d: d.update({
            "list": numpy.repeat(d.pop("values")["list"], d.pop("counts")["list"])
        }))

        # Now, "counts" at Level 1 should be ready. numpy.repeat can take in Level 1 values and counts.
        mask = create_mask(level_1_term="counts")
        lists = numpy.frompyfunc(numpy.repeat, nin=2, nout=1)(
            json_df.loc["values", mask].map(lambda d: d["list"]).to_numpy(),
            json_df.loc["counts", mask].map(lambda d: d["list"]).to_numpy()
        )
        numpy.frompyfunc(lambda d, lst: d.update({"list": lst}), nin=2, nout=1)(
            json_df.loc["values", mask].to_numpy(),
            lists
        )
        json_df = json_df.drop("counts")

        # numpy.char.mod where "prefix" is specified.
        mask = create_mask(level_1_term="values", level_2_term="prefix")
        json_df.loc["values", mask].map(lambda d: d.update({
            "list": numpy.char.mod(f"{d.pop("prefix")}%s", d["list"])
        }))

        # Inherit "values" where "column" is specified.
        mask = json_df.loc["column"].notnull().to_numpy()
        json_df.loc["values", mask] = json_df.loc["column", mask].map(lambda col: json_df.loc["values", col])
        json_df = json_df.drop("column")

        # All done. Now convert to comparator.
        return DataFrameComparator(pandas.DataFrame({
            col: json_df.loc["values", col]["list"] for col in json_df.columns
        }))

    def test_load_data(self):
        if is_remote:
            self.prod = self._create_comparator(json_path="remote_prod.json")
            self.staging_1 = self._create_comparator(json_path="remote_staging_1.json")
            self.staging_2 = self._create_comparator(json_path="remote_staging_2.json")
            logging.info("JSON files loaded successfully for testing purposes.")
        else:
            self.prod = load_prod()
            self.staging_1 = load_staging_1()
            self.staging_2 = load_staging_2()
            logging.info("Excel files loaded successfully for testing purposes!")

    def test_comparison_functions(self):
        if os.path.exists(files_directory):
            pass


if __name__ == '__main__':
    unittest.main()
