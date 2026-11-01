import pandas as pd
import numpy as np
from datetime import datetime

def create_age_distribution_excel():
    """
    创建公司人员年龄分布Excel表格
    """
    # 年龄分布数据（从数据库查询结果获取）
    age_data = [
        {'age_range': '20-24岁', 'count': 6, 'percentage': '3.68%'},
        {'age_range': '25-29岁', 'count': 29, 'percentage': '17.79%'},
        {'age_range': '30-34岁', 'count': 36, 'percentage': '22.09%'},
        {'age_range': '35-39岁', 'count': 33, 'percentage': '20.25%'},
        {'age_range': '40-44岁', 'count': 24, 'percentage': '14.73%'},
        {'age_range': '45-49岁', 'count': 16, 'percentage': '9.82%'},
        {'age_range': '50-54岁', 'count': 13, 'percentage': '7.98%'},
        {'age_range': '55-59岁', 'count': 4, 'percentage': '2.45%'},
        {'age_range': '60岁以上', 'count': 2, 'percentage': '1.23%'}
    ]
    
    # 创建DataFrame
    df = pd.DataFrame(age_data)
    
    # 计算总计
    total_count = df['count'].sum()
    total_percentage = sum([float(p.strip('%')) for p in df['percentage']])
    
    # 添加总计行
    total_row = {
        'age_range': '总计',
        'count': total_count,
        'percentage': f'{total_percentage:.2f}%'
    }
    
    # 将总计行添加到DataFrame
    total_df = pd.DataFrame([total_row])
    result_df = pd.concat([df, total_df], ignore_index=True)
    
    # 创建Excel文件
    output_file = '/workspace/公司人员年龄分布统计.xlsx'
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        result_df.to_excel(writer, sheet_name='年龄分布', index=False)
        
        # 获取工作表以进行格式化
        worksheet = writer.sheets['年龄分布']
        
        # 设置列宽
        worksheet.column_dimensions['A'].width = 12  # 年龄范围
        worksheet.column_dimensions['B'].width = 8   # 人数
        worksheet.column_dimensions['C'].width = 10  # 占比
        
        # 添加标题样式（稍后可以扩展）
        
    print(f'Excel文件已创建: {output_file}')
    return output_file

if __name__ == "__main__":
    create_age_distribution_excel()