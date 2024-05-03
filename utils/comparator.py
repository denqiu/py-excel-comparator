import json
import os
import numpy
import pandas

match_column_prefix = "(Matches)"
match_value = "Match"
not_found_value = "Doesn't exist"


def fill_na_data_frame(data_frame: pandas.DataFrame):
    """
    Pre-process Step 1: Fill in NA values before comparing data frames.

    1: NaN values are expected to be empty. Replace NaN values with empty string.

    2: Note: NA values that are not filled in caused working masks to return an empty data frame.
    They don't trigger any errors.
    """
    data_frame.fillna("", inplace=True)


def check_columns(data_frame: pandas.DataFrame, columns: list[str]):
    """
    Pre-process Step 2: Return columns if they exist otherwise throw error.
    """
    data_frame_columns = data_frame.columns.tolist()
    columns_not_found = [col for col in columns if col not in data_frame_columns]
    if len(columns_not_found) == 0:
        return columns
    raise Exception(f"Columns not found: {columns_not_found}.")


def add_matches(data_frame: pandas.DataFrame, column: str, matches):
    """
    Post-process Step: Insert matches after original column or update match column if exists.
    """
    match_col = f"{match_column_prefix} {column}"
    if match_col in data_frame.columns:
        data_frame[match_col] = matches
    else:
        data_frame.insert(loc=data_frame.columns.get_loc(column) + 1, column=match_col, value=matches)


def analyze_columns(data_frame: pandas.DataFrame, columns: list[str], lookup_columns: list[str]):
    """
    Process Step: Examine columns at lookup level
    """
    # TODO: self.data_frame[[lookup_columns, columns]].groupby(lookup_columns)[columns].apply(lambda c: c.unique()).reset_index()
    pass


def compare_columns(data_frame: pandas.DataFrame, matcher_data_frame: pandas.DataFrame):
    """
    Process Step
    TODO: Simply compare column values and comments.
    """
    pass


def fastest_sql_vectorized(data_frame: pandas.DataFrame, matcher_data_frame: pandas.DataFrame,
                           column: str, matcher_column: str, lookup_columns: list[str]):
    """
    Process Step

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
    columns = check_columns(data_frame, [column, *lookup_columns])
    matcher_columns = check_columns(matcher_data_frame, [matcher_column, *lookup_columns])
    has_duplicates = [False]

    def add_occurrences(df: pandas.DataFrame):
        """
        1: Label duplicated value by appearance count. First instance of duplicated value is 0, the second is 1,
        and so on.
        2: Messes up merge operation if columns combined do not contain duplicate values. In this scenario,
        we don't need to count occurrences.
        """
        if df.duplicated().any():
            has_duplicates[0] = True
            for col in lookup_columns:
                df[f"{col} Occurrences"] = df.groupby(col).cumcount()
        return df

    def get_lookup_columns():
        """
        If duplicates are found, generate occurrence column next to each lookup column.
        Otherwise, return lookup columns as is.
        """
        if has_duplicates[0]:
            return numpy.array(list(zip(
                lookup_columns, numpy.char.mod("%s Occurrences", lookup_columns)))).flatten().tolist()
        return lookup_columns

    merged_df = add_occurrences(data_frame[columns].copy()).merge(
        add_occurrences(matcher_data_frame[matcher_columns].copy()), how="left", on=get_lookup_columns()
    ).fillna(not_found_value)
    if column == matcher_column:
        column = f"{column}_x"
        matcher_column = f"{matcher_column}_y"
    matches = numpy.where(
        merged_df[column] == merged_df[matcher_column],
        match_value,
        merged_df[matcher_column]
    )
    return matches


def fast_manual_vectorized(data_frame: pandas.DataFrame, matcher_data_frame: pandas.DataFrame,
                           column: str, matcher_column: str, lookup_columns: list[str],
                           lookup_indices: dict, matcher_lookup_indices: dict):
    """
    Process Step

    From Gemini after providing info about BSOD. Turns out implementation is similar to the pandas version.

    This function utilizes numpy arrays to implement vectorization.

    'self' has 42,000 rows and 'matcher' has 47,000 rows. Columns tested:
        One lookup column (with duplicate values): 1 minute and 48 seconds.

        Multiple lookup columns (w/o duplicate values combined): 8 minutes and 36 seconds.
    """
    check_columns(data_frame, [column, *lookup_columns])
    check_columns(matcher_data_frame, [matcher_column, *lookup_columns])

    numpy_rows = data_frame.to_numpy()
    matcher_numpy_rows = data_frame.to_numpy()

    column_index = data_frame.columns.get_loc(column)
    matcher_column_index = matcher_data_frame.columns.get_loc(matcher_column)

    matches = []
    for row in numpy_rows:
        masks = [matcher_numpy_rows[:, matcher_lookup_indices[col]] == row[lookup_indices[col]] for col in
                 lookup_columns]
        result = matcher_numpy_rows[numpy.logical_and.reduce(masks)]
        value = not_found_value if result.shape[0] == 0 else result[0, matcher_column_index]
        matches.append(match_value if row[column_index] == value else value)
    return matches


def slow_pandas(data_frame: pandas.DataFrame, matcher_data_frame: pandas.DataFrame,
                column: str, matcher_column: str, lookup_columns: list[str]):
    """
    See https://pythoninoffice.com/replicate-excel-vlookup-hlookup-xlookup-in-python/.

    This function utilizes the masking concept and applies a boolean numpy array for each lookup
    column per row to find matches.

    'self' has 42,000 rows and 'matcher' has 47,000 rows. Columns tested:
        One lookup column (with duplicate values): 4 minutes and 40 seconds.

        Multiple lookup columns (w/o duplicate values combined): 30 minutes.
    """
    columns = check_columns(data_frame, [column, *lookup_columns])
    matcher_columns = check_columns(matcher_data_frame, [matcher_column, *lookup_columns])

    def match_cell(row, matcher_df):
        masks = [matcher_df[col] == row[col] for col in lookup_columns]
        result_series = matcher_df[matcher_column].loc[numpy.logical_and.reduce(masks)]
        value = not_found_value if result_series.empty else result_series.tolist()[0]
        return match_value if row[column] == value else value

    # Comma must be appended to last argument provided otherwise value error appears:
    # The truth value of a DataFrame is ambiguous. Use a.empty, a.bool(), a.item(), a.any() or a.all().
    matches = data_frame[columns].copy().apply(axis=1, func=match_cell,
                                               args=(matcher_data_frame[matcher_columns].copy(),))
    return matches


def slow_json(data_frame: pandas.DataFrame, matcher_data_frame: pandas.DataFrame,
              column: str, matcher_column: str, lookup_columns: list[str]):
    """
    This function uses Python dictionaries, which comes from the dataframe being converted to json.
    Then looks up columns on each row to find matches.

    'self' has 42,000 rows and 'matcher' has 47,000 rows. Columns tested:
        One lookup column (with duplicate values): 19 minutes and 20 seconds.

        Multiple lookup columns (w/o duplicate values combined): 20 minutes.
    """
    check_columns(data_frame, [column, *lookup_columns])
    check_columns(matcher_data_frame, [matcher_column, *lookup_columns])

    # Dictionary of columns. Each column is a dictionary mapping row index (as string, 0-based) to cell value.
    json_columns = json.loads(data_frame.to_json())
    # Array of rows. Each row is a dictionary mapping column name to cell value.
    matcher_json_rows = json.loads(matcher_data_frame.to_json(orient='records'))

    matches = []
    for row_index in range(data_frame.index.stop):
        lookup_values = {col: json_columns[col][f"{row_index}"] for col in lookup_columns}
        find_index = next((index for index, matcher_row in enumerate(matcher_json_rows) if
                           lookup_values.items() <= matcher_row.items()), -1)
        find_value = matcher_json_rows[find_index][matcher_column] if find_index != -1 else not_found_value
        cell_value = json_columns[column][f"{row_index}"]
        matches.append(match_value if cell_value == find_value else find_value)
    return matches


def from_excel(excel_path: str, sheet_name="Sheet1", start_row=0, na_filter=False):
    """
    If csv file exists, read csv file. Otherwise, read Excel file into a data frame. Then write to csv file.

    :param start_row: 0-based index number.
    :param na_filter: False by default to prevent replacement of NA-like values (None, N/A) with NaN.
    """
    csv_path = excel_path.replace(".xlsx", ".csv")
    if os.path.exists(csv_path):
        print("\nReading .csv file...")
        data_frame = pandas.read_csv(filepath_or_buffer=csv_path, header=0, na_filter=na_filter)
        print("Done.")
    else:
        print("\nReading .xlsx file...")
        data_frame = pandas.read_excel(io=excel_path, sheet_name=sheet_name, header=start_row, na_filter=na_filter)
        print("Writing .csv file...")
        data_frame.to_csv(index=False, path_or_buf=csv_path)
        print("Done. From now on, .csv file will be read instead of .xlsx file. To update, delete .csv file.")
    fill_na_data_frame(data_frame)
    return data_frame


def from_json(json_path: str):
    """
    Ref: remote_comparator.json.example
    """
    json_df = pandas.read_json(json_path)

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
    json_df.drop("counts", inplace=True)

    # numpy.char.mod where "prefix" is specified.
    mask = create_mask(level_1_term="values", level_2_term="prefix")
    json_df.loc["values", mask].map(lambda d: d.update({
        "list": numpy.char.mod(f"{d.pop("prefix")}%s", d["list"])
    }))

    # Inherit "values" where "column" is specified.
    mask = json_df.loc["column"].notnull().to_numpy()
    json_df.loc["values", mask] = json_df.loc["column", mask].map(lambda col: json_df.loc["values", col])
    json_df.drop("column", inplace=True)

    # All done. Now convert to proper data frame.
    df = pandas.DataFrame({
        col: json_df.loc["values", col]["list"] for col in json_df.columns
    })
    fill_na_data_frame(df)
    return df
