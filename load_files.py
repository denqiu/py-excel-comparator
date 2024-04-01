import os

from utils.comparator import ExcelComparator

files_directory = os.path.join(os.path.dirname(__file__), 'files')
if not os.path.exists(files_directory):
    os.mkdir(files_directory)

files = (
    ExcelComparator(excel_path=os.path.join(files_directory, 'prod.xlsx'), sheet_name='prod', start_row=1),
    ExcelComparator(excel_path=os.path.join(files_directory, 'staging_1.xlsx'), sheet_name='staging_1', start_row=1),
    ExcelComparator(excel_path=os.path.join(files_directory, 'staging_2.xlsx'), sheet_name='staging_2', start_row=1)
)