import pandas as pd
from datetime import datetime
import os

def generate_age_distribution_excel(data, output_path):
    """
    生成公司各年龄段人数统计的Excel文件
    
    Args:
        data: 包含年龄和人数的列表，每个元素为{'age': int, 'count': int}
        output_path: 输出Excel文件的路径
    """
    # 创建DataFrame
    df = pd.DataFrame(data)
    
    # 添加年龄段分组
    def get_age_group(age):
        if age < 25:
            return '20-24'
        elif age < 30:
            return '25-29'
        elif age < 35:
            return '30-34'
        elif age < 40:
            return '35-39'
        elif age < 45:
            return '40-44'
        elif age < 50:
            return '45-49'
        elif age < 55:
            return '50-54'
        elif age < 60:
            return '55-59'
        else:
            return '60+'
    
    df['年龄段'] = df['age'].apply(get_age_group)
    
    # 按年龄段分组统计
    age_group_summary = df.groupby('年龄段').agg({
        'count': 'sum'
    }).reset_index()
    age_group_summary.columns = ['年龄段', '人数']
    
    # 按年龄段排序
    age_order = ['20-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54', '55-59', '60+']
    age_group_summary['年龄段'] = pd.Categorical(age_group_summary['年龄段'], categories=age_order, ordered=True)
    age_group_summary = age_group_summary.sort_values('年龄段')
    
    # 创建详细的年龄分布表
    detailed_df = df.copy()
    detailed_df.columns = ['年龄', '人数', '年龄段']
    detailed_df = detailed_df.sort_values('年龄')
    
    # 创建Excel文件
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # 写入详细数据表
        detailed_df.to_excel(writer, sheet_name='详细年龄分布', index=False)
        
        # 写入年龄段汇总表
        age_group_summary.to_excel(writer, sheet_name='年龄段汇总', index=False)
        
        # 添加统计信息
        total_people = df['count'].sum()
        avg_age = (df['age'] * df['count']).sum() / total_people
        
        stats_df = pd.DataFrame([
            {'统计项': '总人数', '值': total_people},
            {'统计项': '平均年龄', '值': round(avg_age, 1)},
            {'统计项': '最多年龄段', '值': age_group_summary.iloc[age_group_summary['人数'].idxmax()]['年龄段']},
            {'统计项': '最多人数', '值': age_group_summary['人数'].max()},
            {'统计项': '最少年龄段', '值': age_group_summary.iloc[age_group_summary['人数'].idxmin()]['年龄段']},
            {'统计项': '最少人数', '值': age_group_summary['人数'].min()}
        ])
        
        stats_df.to_excel(writer, sheet_name='统计信息', index=False)
    
    print(f"Excel文件已生成: {output_path}")
    return output_path