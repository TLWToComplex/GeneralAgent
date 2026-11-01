from openpyxl import Workbook

def create_excel():
    """
    创建一个新的 Excel 工作簿
    
    Returns:
        Workbook: 新创建的工作簿对象
    """
    return Workbook()