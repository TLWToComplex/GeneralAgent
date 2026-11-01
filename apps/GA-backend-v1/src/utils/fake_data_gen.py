"""
Fake data generator module.
Provides functions for generating test data for development and testing.
"""
from faker import Faker
import random
import uuid
from datetime import datetime

fake = Faker()

sql_prefix = (
    "INSERT INTO PersonInfo "
    "(Guid, Code, Name, Sex, DateOfBirth, Company, Title, Introduction, AdditionalInfo, "
    "CreatedBy, CreatedAt, UpdatedBy, UpdatedAt) VALUES "
)

values_list = []
codes_set = set()

for _ in range(50):
    code = random.randint(1, 1000)
    while code in codes_set:
        code = random.randint(1, 1000)
    codes_set.add(code)

    values_str = (
        "('{Guid}', {Code}, '{Name}', {Sex}, '{DateOfBirth}', '{Company}', '{Title}', "
        "'{Introduction}', '{AdditionalInfo}', '{CreatedBy}', '{CreatedAt}', '{UpdatedBy}', "
        "'{UpdatedAt}')"
    ).format(
        Guid=uuid.uuid4(),
        Code=code,
        Name=fake.name().replace("'", "''"),
        Sex=random.randint(0, 1),
        DateOfBirth=fake.date_of_birth(minimum_age=18, maximum_age=90).strftime('%Y-%m-%d'),
        Company=fake.company().replace("'", "''"),  
        Title=fake.job().replace("'", "''"),  
        Introduction='Intro',  
        AdditionalInfo="{}",  
        CreatedBy="Admin",
        CreatedAt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        UpdatedBy="Admin",
        UpdatedAt=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    values_list.append(values_str)

sql_statement = sql_prefix + ",".join(values_list) + ";"

# 打开文件并写入SQL语句
with open('seed_test_data.sql', 'w', encoding='utf-8') as file:
    file.write(sql_statement)
