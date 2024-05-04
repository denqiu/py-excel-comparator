import os
import dotenv

import utils.comparator

dotenv.load_dotenv()

files_directory = os.path.join(os.path.dirname(__file__), 'files')
if not os.path.exists(files_directory):
    os.mkdir(files_directory)

json_directory = os.path.join(os.path.dirname(__file__), *os.getenv("JSON_FOLDER").split(","))
if not os.path.exists(json_directory):
    os.mkdir(json_directory)

# or os.getenv("GITLAB_CI") is not None
is_remote = os.getenv(os.getenv("IS_REMOTE")) is not None


def load_excel(excel_path: str, sheet_name: str, start_row: int, na_filter=False):
    return utils.comparator.from_excel(excel_path, sheet_name, start_row, na_filter)


def load_prod():
    return load_excel(
        excel_path=os.path.join(files_directory, os.getenv("PROD_EXCELPATH")),
        sheet_name=os.getenv("PROD_SHEETNAME"),
        start_row=int(os.getenv("PROD_STARTROW"))
    )


def load_staging_1():
    return load_excel(
        excel_path=os.path.join(files_directory, os.getenv("STAGING_1_EXCELPATH")),
        sheet_name=os.getenv("STAGING_1_SHEETNAME"),
        start_row=int(os.getenv("STAGING_1_STARTROW"))
    )


def load_staging_2():
    return load_excel(
        excel_path=os.path.join(files_directory, os.getenv("STAGING_2_EXCELPATH")),
        sheet_name=os.getenv("STAGING_2_SHEETNAME"),
        start_row=int(os.getenv("STAGING_2_STARTROW"))
    )
