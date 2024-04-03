import os

from dotenv import load_dotenv
from utils.comparator import ExcelComparator

load_dotenv()

files_directory = os.path.join(os.path.dirname(__file__), 'files')
if not os.path.exists(files_directory):
    os.mkdir(files_directory)


def load(excel_path: str, sheet_name: str, start_row: int, na_filter=False):
    return ExcelComparator(excel_path, sheet_name, start_row, na_filter)


def prod():
    return load(
        excel_path=os.path.join(files_directory, os.getenv("PROD_EXCELPATH")),
        sheet_name=os.getenv("PROD_SHEETNAME"),
        start_row=int(os.getenv("PROD_STARTROW"))
    )


def staging_1():
    return load(
        excel_path=os.path.join(files_directory, os.getenv("STAGING_1_EXCELPATH")),
        sheet_name=os.getenv("STAGING_1_SHEETNAME"),
        start_row=int(os.getenv("STAGING_1_STARTROW"))
    )


def staging_2():
    return load(
        excel_path=os.path.join(files_directory, os.getenv("STAGING_2_EXCELPATH")),
        sheet_name=os.getenv("STAGING_2_SHEETNAME"),
        start_row=int(os.getenv("STAGING_2_STARTROW"))
    )