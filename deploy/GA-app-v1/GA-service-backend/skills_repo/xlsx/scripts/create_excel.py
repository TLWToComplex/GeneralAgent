#!/usr/bin/env python3
"""
创建公司员工年龄分布Excel报表
"""
import pandas as pd
import sys

def create_age_distribution_excel(data, filename):
    """
    创建包含公司各年龄段人数的Excel文件
    
    Args:
        data: 包含年龄和人数的列表，如[(25, 3), (30, 5)]
        filename: 输出文件名
    
    Returns:
        str: 生成的文件路径
    """
    # 创建DataFrame
    df = pd.DataFrame(data, columns=['年龄', '人数'])
    
    # 按年龄排序
    df = df.sort_values('年龄')
    
    # 保存为Excel文件
    df.to_excel(filename, index=False)
    
    return filename

def main():
    if len(sys.argv) != 3:
        print("Usage: python create_excel.py <data_str> <filename>")
        sys.exit(1)
    
    # 解析输入数据
    data_str = sys.argv[1]
    filename = sys.argv[2]
    
    # 将字符串数据转换为列表
    # 数据格式: "[(25,3),(30,5)]"
    try:
        data = eval(data_str)
    except Exception as e:
        print(f"Error parsing data: {e}")
        sys.exit(1)
    
    # 创建Excel文件
    try:
        result = create_age_distribution_excel(data, filename)
        print(f"Successfully created Excel file: {result}")
        return result
    except Exception as e:
        print(f"Error creating Excel file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()