import itertools
import json
import os
import typing

import numpy
import pandas


class ExcelComparator:
    match_column_prefix = "(Matches)"
    match_value = "Match"
    not_found_value = "Doesn't exist"

    def __init__(self, filename: str, sheet_name="Sheet1", start_row=0, na_filter=False):
        """
        1: If csv file exists, read csv file. Otherwise, read Excel file into a data frame. Then write to csv file.

        2: Any NaN values are expected to be empty. Replace NaN values with empty string.

        Note: NA values that are not filled in caused working masks to return an empty data frame.
        They don't trigger any errors.
        :param start_row: 0-based index number.
        :param na_filter: False by default to prevent replacement of NA-like values (None, N/A) with NaN.
        """
        self.filename = filename
        self.csv_path = filename.replace(".xlsx", ".csv")
        if os.path.exists(self.csv_path):
            print("\nReading .csv file...")
            self.data_frame = pandas.read_csv(filepath_or_buffer=self.csv_path, header=0,
                                              na_filter=na_filter).fillna("")
            print("Done.")
        else:
            print("\nReading .xlsx file...")
            self.data_frame = pandas.read_excel(io=filename, sheet_name=sheet_name, header=start_row,
                                                na_filter=na_filter).fillna("")
            print("Writing .csv file...")
            self.data_frame.to_csv(index=False, path_or_buf=self.csv_path)
            print("Done. From now on, .csv file will be read instead of .xlsx file. To update, delete .csv file.")
        self.lookup_indices = {}
        self.json_data = {}
        self.numpy_rows = numpy.array([])
        self.has_duplicates = False

    def create_json(self, orient=False):
        """
        :param orient: If True create array of rows otherwise dictionary of columns.
        Each row is a dictionary mapping column names to values.
        Each column is a dictionary mapping row indices (as strings, 0-based) to values.
        """
        if orient:
            self.json_data = json.loads(self.data_frame.to_json(orient='records'))
        else:
            self.json_data = json.loads(self.data_frame.to_json())

    def create_numpy(self):
        self.numpy_rows = self.data_frame.to_numpy()

    def check_columns(self, columns: list[str]):
        data_frame_columns = self.data_frame.columns.tolist()
        columns_not_found = [col for col in columns if col not in data_frame_columns]
        if len(columns_not_found) == 0:
            return
        raise Exception(f"Columns not found: {columns_not_found}.")

    def add_matches(self, column: str, matches):
        """
        Insert matches after original column or update match column if exists.
        """
        match_col = f"{ExcelComparator.match_column_prefix} {column}"
        if match_col in self.data_frame.columns:
            self.data_frame[match_col] = matches
        else:
            self.data_frame.insert(loc=self.data_frame.columns.get_loc(column) + 1, column=match_col, value=matches)

    def compare_columns(self, matcher: typing.Self):
        """
        TODO: Simply compare column values and comments.
        """

    def fastest_auto_vectorized(self, matcher: typing.Self, column: str, matcher_column: str,
                                lookup_columns: list[str]):
        """
        From Gemini after taking in the pandas version.

        Occurrence query translated by ChatGPT.

        This function utilizes numpy's vectorization concept (column-wise), leveraging C operations under the hood,
        and pandas to merge data on lookup columns. Pandas' merge function behaves like SQL.
        This is the SQL solution (where GroupName has duplicate values and Item doesn't have duplicates):

        SELECT t1.GroupName, t1.Item AS Item_x, t2.Item AS Item_y
        FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY GroupName) AS Occurrence FROM table1) AS t1
        LEFT JOIN (SELECT *, ROW_NUMBER() OVER (PARTITION BY GroupName) AS Occurrence FROM table2) AS t2
        ON t1.GroupName = t2.GroupName AND t1.Occurrence = t2.Occurrence;

        Resolves Cartesian product (and avoids Blue Screen of Death) during merge/left join on GroupName.

        'self' has 42,000 rows and 'matcher' has 47,000 rows. Columns tested (to be updated later):
            One lookup column (with duplicate values): 10 seconds/Blue screen of death.

            Multiple lookup columns (w/o duplicate values combined): 300 milliseconds/800 milliseconds.
        """
        columns = [column, *lookup_columns]
        self.check_columns(columns)
        matcher_columns = [matcher_column, *lookup_columns]
        matcher.check_columns(matcher_columns)

        self.has_duplicates = False

        def add_occurrences(data_frame: pandas.DataFrame):
            """
            1: Label duplicated value by appearance count. First instance of duplicated value is 0, the second is 1,
            and so on.
            2: Messes up merge operation if columns combined do not contain duplicate values. In this scenario,
            we don't need to count occurrences.
            """
            if data_frame.duplicated().any():
                self.has_duplicates = True
                for col in lookup_columns:
                    data_frame[f"{col} Occurrences"] = data_frame.groupby(col).cumcount()
            return data_frame

        def get_lookup_columns():
            """
            If duplicates are found, generate occurrence column next to each lookup column.
            Otherwise, return lookup columns as is.
            """
            if self.has_duplicates:
                return list(
                    itertools.chain(*zip(lookup_columns, [f"{col} Occurrences" for col in lookup_columns])))
            return lookup_columns

        merged_df = add_occurrences(self.data_frame[columns].copy()).merge(
            add_occurrences(matcher.data_frame[matcher_columns].copy()), how="left", on=get_lookup_columns()
        ).fillna(ExcelComparator.not_found_value)
        if column == matcher_column:
            column = f"{column}_x"
            matcher_column = f"{matcher_column}_y"
        matches = numpy.where(
            merged_df[column] == merged_df[matcher_column], ExcelComparator.match_value, merged_df[matcher_column]
        )
        return matches

    def fast_manual_vectorized(self, matcher: typing.Self, column: str, matcher_column: str,
                                  lookup_columns: list[str]):
        """
        From Gemini after providing info about BSOD. Turns out implementation is similar to the pandas version.

        This function utilizes numpy arrays to implement vectorization.

        'self' has 42,000 rows and 'matcher' has 47,000 rows. Columns tested:
            One lookup column (with duplicate values): 1 minute and 48 seconds.

            Multiple lookup columns (w/o duplicate values combined): 8 minutes and 36 seconds.
        """
        columns = [column, *lookup_columns]
        self.check_columns(columns)
        matcher_columns = [matcher_column, *lookup_columns]
        matcher.check_columns(matcher_columns)

        def numpy_not_found(comparator: typing.Self):
            return len(comparator.numpy_rows) != len(comparator.data_frame)

        if numpy_not_found(self):
            self.create_numpy()
        if numpy_not_found(matcher):
            matcher.create_numpy()

        if self.lookup_indices.keys() != lookup_columns:
            self.lookup_indices = {col: i for i, col in enumerate(self.data_frame.columns) if col in lookup_columns}
        if matcher.lookup_indices.keys() != lookup_columns:
            matcher.lookup_indices = {col: i for i, col in enumerate(matcher.data_frame.columns) if col in
                                      lookup_columns}
        column_index = self.data_frame.columns.get_loc(column)
        matcher_column_index = matcher.data_frame.columns.get_loc(matcher_column)

        matches = []
        for row in self.numpy_rows:
            masks = [matcher.numpy_rows[:, matcher.lookup_indices[col]] == row[self.lookup_indices[col]] for col in
                     lookup_columns]
            result = matcher.numpy_rows[numpy.logical_and.reduce(masks)]
            value = ExcelComparator.not_found_value if len(result) == 0 else result[0, matcher_column_index]
            matches.append(ExcelComparator.match_value if row[column_index] == value else value)
        return matches

    def slow_pandas(self, matcher: typing.Self, column: str, matcher_column: str, lookup_columns: list[str]):
        """
        See https://pythoninoffice.com/replicate-excel-vlookup-hlookup-xlookup-in-python/.

        This function utilizes the masking concept and applies a boolean numpy array for each lookup
        column per row to find matches.

        'self' has 42,000 rows and 'matcher' has 47,000 rows. Columns tested:
            One lookup column (with duplicate values): 4 minutes and 40 seconds.

            Multiple lookup columns (w/o duplicate values combined): 30 minutes.
        """
        columns = [column, *lookup_columns]
        self.check_columns(columns)
        matcher_columns = [matcher_column, *lookup_columns]
        matcher.check_columns(matcher_columns)

        def match_cell(row, matcher_data_frame):
            masks = [matcher_data_frame[col] == row[col] for col in lookup_columns]
            result_series = matcher_data_frame[matcher_column].loc[numpy.logical_and.reduce(masks)]
            value = ExcelComparator.not_found_value if result_series.empty else result_series.tolist()[0]
            return ExcelComparator.match_value if row[column] == value else value

        matches = self.data_frame[columns].copy().apply(axis=1, func=match_cell,
                                                        args=(matcher.data_frame[matcher_columns].copy()))
        return matches

    def slow_json(self, matcher: typing.Self, column: str, matcher_column: str, lookup_columns: list[str]):
        """
        This function uses Python dictionaries, which comes from the dataframe being converted to json.
        Then looks up columns on each row to find matches.

        'self' has 42,000 rows and 'matcher' has 47,000 rows. Columns tested:
            One lookup column (with duplicate values): 19 minutes and 20 seconds.

            Multiple lookup columns (w/o duplicate values combined): 20 minutes.
        """
        columns = [column, *lookup_columns]
        self.check_columns(columns)
        matcher_columns = [matcher_column, *lookup_columns]
        matcher.check_columns(matcher_columns)

        if len(self.json_data) != len(self.data_frame.columns):
            self.create_json()
        if len(matcher.json_data) != len(matcher.data_frame):
            self.create_json(orient=True)

        matches = []
        for row_index in range(self.data_frame.index.stop):
            lookup_values = {col: self.json_data[col][f"{row_index}"] for col in lookup_columns}
            find_index = next((index for index, matcher_row in enumerate(matcher.json_data) if
                               lookup_values.items() <= matcher_row.items()),
                              -1)
            find_value = matcher.json_data[find_index][
                matcher_column] if find_index != -1 else ExcelComparator.not_found_value
            cell_value = self.json_data[column][f"{row_index}"]
            matches.append(ExcelComparator.match_value if cell_value == find_value else find_value)
        return matches
