from openpyxl import Workbook

def save_excel(workbook, file_path):
    """
    保存工作簿到指定路径
    
    Args:
        workbook: 要保存的工作簿对象
        file_path: 保存路径
    """
    try:
        workbook.save(file_path)
        return {"success": True, "message": f"文件已成功保存到 {file_path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}