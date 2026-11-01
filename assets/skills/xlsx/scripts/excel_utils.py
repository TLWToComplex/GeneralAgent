"""
Excel工具函数库
提供创建、读取、修改Excel文件的功能
"""

import pandas as pd
import openpyxl
from typing import Dict, List, Any
import os

def create_excel(filename: str) -> bool:
    """
    创建一个新的Excel文件
    
    Args:
        filename (str): 要创建的Excel文件名
    
    Returns:
        bool: 创建成功返回True，失败返回False
    """
    try:
        # 确保目录存在
        directory = os.path.dirname(filename)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        # 创建空的DataFrame并保存为Excel
        df = pd.DataFrame()
        df.to_excel(filename, index=False)
        return True
    except Exception as e:
        print(f"创建Excel文件时出错: {e}")
        return False

def read_excel(filename: str) -> pd.DataFrame:
    """
    读取Excel文件内容
    
    Args:
        filename (str): 要读取的Excel文件名
    
    Returns:
        pd.DataFrame: Excel文件的数据内容
    """
    try:
        return pd.read_excel(filename)
    except Exception as e:
        print(f"读取Excel文件时出错: {e}")
        return pd.DataFrame()

def edit_excel(filename: str, sheet_name: str, data: List[List[Any]]) -> bool:
    """
    编辑Excel文件的指定工作表
    
    Args:
        filename (str): 要编辑的Excel文件名
        sheet_name (str): 要编辑的工作表名称
        data (List[List[Any]]): 要写入的数据，二维列表
    
    Returns:
        bool: 编辑成功返回True，失败返回False
    """
    try:
        # 读取现有工作簿
        workbook = openpyxl.load_workbook(filename)
        
        # 如果工作表已存在则删除
        if sheet_name in workbook.sheetnames:
            del workbook[sheet_name]
        
        # 创建新的工作表
        worksheet = workbook.create_sheet(title=sheet_name)
        
        # 写入数据
        for row_idx, row_data in enumerate(data, 1):
            for col_idx, cell_data in enumerate(row_data, 1):
                worksheet.cell(row=row_idx, column=col_idx, value=cell_data)
        
        # 保存工作簿
        workbook.save(filename)
        return True
    except Exception as e:
        print(f"编辑Excel文件时出错: {e}")
        return False

def save_to_excel(data: pd.DataFrame, filename: str, sheet_name: str = "Sheet1") -> bool:
    """
    将数据保存到Excel文件
    
    Args:
        data (pd.DataFrame): 要保存的数据
        filename (str): 目标Excel文件名
        sheet_name (str): 工作表名称，默认为"Sheet1"
    
    Returns:
        bool: 保存成功返回True，失败返回False
    """
    try:
        # 确保目录存在
        directory = os.path.dirname(filename)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        data.to_excel(filename, sheet_name=sheet_name, index=False)
        return True
    except Exception as e:
        print(f"保存数据到Excel时出错: {e}")
        return False