import logging
import os
import time
import traceback
import unittest
import pandas

import utils.comparator
import load_comparators

logging.basicConfig(level=logging.INFO)


class TestComparators(unittest.TestCase):
    """
    See "adjacent.count_adjacent_elements" to re-create test data via arrays instead of excel files (for remote).

    Arrays are then placed inside JSON files.
    """

    def setUp(self):
        self.prod = pandas.DataFrame()
        self.staging_1 = pandas.DataFrame()
        self.staging_2 = pandas.DataFrame()
        self.timer = time.perf_counter()

    def _load_data(self):
        if load_comparators.is_remote:
            self.prod = utils.comparator.from_json(os.path.join(
                load_comparators.json_directory, "remote_prod.json"))
            self.staging_1 = utils.comparator.from_json(os.path.join(
                load_comparators.json_directory, "remote_staging_1.json"))
            self.staging_2 = utils.comparator.from_json(os.path.join(
                load_comparators.json_directory, "remote_staging_2.json"))
            logging.info("JSON files loaded successfully for testing purposes.")
        else:
            self.prod = load_comparators.load_prod()
            self.staging_1 = load_comparators.load_staging_1()
            self.staging_2 = load_comparators.load_staging_2()
            logging.info("Excel files loaded successfully for testing purposes!")

    def _run_comparison(self, func, title: str, matcher_data_frame: pandas.DataFrame, kwargs: dict):
        start = time.perf_counter()
        func(self.prod, matcher_data_frame, **kwargs)
        end = time.perf_counter() - start
        print(f"Timer: {time.perf_counter() - self.timer}")
        print(f"{title}: '{func.__name__}' compared '{kwargs["column"]}' in {end} seconds.")

    def _loop_args(self, func, func_args, matchers):
        """
        Loop over function arguments and matchers to run comparisons.

        Return if argument triggers an error.
        Assumes that error would be the same for other arguments provided to function, like asyncio.TaskGroup.
        """
        for args in func_args:
            for title, matcher_df in matchers.items():
                kwargs = args.copy()
                if "fast_" in func.__name__:
                    kwargs = {
                        **kwargs,
                        "lookup_indices": {col: i for i, col in enumerate(self.prod.columns) if
                                           col in kwargs["lookup_columns"]},
                        "matcher_lookup_indices": {col: i for i, col in enumerate(matcher_df.columns) if
                                                   col in kwargs["lookup_columns"]}
                    }
                try:
                    self._run_comparison(func, title, matcher_df, kwargs)
                except:
                    traceback.print_exc()
                    return

    def _gather_comparisons(self):
        """
        On remote pipeline, run only fastest function.

        On local, run through all functions.

        1: Compare on one lookup column (Supplier Id).

        2: Compare on multiple lookup columns with duplicates combined (Test Group).

        3: Compare on multiple lookup columns without duplicates combined (Parameter Id).

        ASYNCIO NOTES
        "async/await" keywords behave the same in Javascript.
        "gather" and "wait" functions behave similarly to Javascript's Promise.all and Promise.race.

        PYTHON/JAVASCRIPT DIFFERENCES
        Calling async function synchronously returns a coroutine object.
        It does not execute code however it does execute code in Javascript.

        async def func():
        # In Javascript, this would've executed function.
        # However, in Python, this doesn't execute the function. It simply returns coroutine.
        func()

        PSEUDOCODE
        # See video in wiki: https://github.com/denqiu/py-excel-comparator/wiki/Asyncio-Behaviors
        async def test(group_id, test_id, delay):
            await asyncio.sleep(delay)
            print(f"Group: {group_id}, Test: {test_id}, Delay: {delay}")

        async def run_group(group_id):
            n = random_number()
            data = [(1, 5), (2, 10)]
            await asyncio.gather, await asyncio.wait, asyncio.create_task, asyncio.ensure_future, or TaskGroup
            -> test(group_id, test_id, delay + n) for test_id, delay in data

        async def main():
            await asyncio.gather or asyncio.wait -> run_group(group_id - range 1 to 4)

        asyncio.run(main())
        """
        comp_utils = utils.comparator
        funcs = [
            comp_utils.fastest_sql_vectorized
        ]
        if not load_comparators.is_remote:
            funcs = [
                *funcs,
                comp_utils.fast_manual_vectorized,
                comp_utils.slow_pandas,
                comp_utils.slow_json
            ]
        matchers = {
            "Staging Export 1": self.staging_1,
            "Staging Export 2": self.staging_2
        }
        func_args = [
            {"column": "Supplier Conclusion", "matcher_column": "Supplier Conclusion",
             "lookup_columns": ["Supplier Id"]},
            {"column": "Parameter Conclusion", "matcher_column": "Parameter Conclusion",
             "lookup_columns": ["Supplier Id", "Test Request Id", "Test Group Id", "Test Group", "Parameter Id"]},
            {"column": "Test Group Conclusion", "matcher_column": "Test Group Conclusion",
             "lookup_columns": ["Supplier Id", "Test Request Id", "Test Group Id", "Test Group"]}
        ]
        # Decided to remove async functionality for now.
        # Re-ordered args to predict time completion: Suppliers, Parameters, Test Groups.
        for func in funcs:
            self._loop_args(func, func_args, matchers)

    def test_comparisons(self):
        self._load_data()
        self._gather_comparisons()


if __name__ == '__main__':
    unittest.main()
