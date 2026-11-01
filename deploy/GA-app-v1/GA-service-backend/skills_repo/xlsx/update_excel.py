def update_excel(worksheet, data, start_row=1, start_col=1):
    """
    更新工作表中的数据
    
    Args:
        worksheet: 要更新的工作表对象
        data: 二维列表，包含要写入的数据
        start_row: 开始写入的行号（默认为1）
        start_col: 开始写入的列号（默认为1）
    
    Returns:
        dict: 操作结果
    """
    try:
        for row_idx, row_data in enumerate(data, start=start_row):
            for col_idx, cell_value in enumerate(row_data, start=start_col):
                worksheet.cell(row=row_idx, column=col_idx, value=cell_value)
        return {"success": True, "message": "数据已成功更新"}
    except Exception as e:
        return {"success": False, "error": str(e)}