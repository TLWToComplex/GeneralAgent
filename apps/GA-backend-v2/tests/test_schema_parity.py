"""DDL 与 ORM 模型一致性测试。

生产库用 ``sql/`` 下的建表脚本建表，测试用 ORM 元数据建表；两者一旦漂移，
就会出现「测试通过、上线报 Unknown column」这类问题。这里直接解析 DDL 做比对。

比对范围是 ``sql/*_init_*.sql``（001 初次建表、003 dsh 映射表）；
``002_drop_unrelated_tables.sql`` 是清理脚本，不含建表语句，不参与比对。
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from app.db import Base
import app.models  # noqa: F401  确保模型已注册

SQL_DIR = Path(__file__).resolve().parents[1] / "sql"
#: 参与比对的所有建表脚本（按文件名排序，保证解析顺序稳定）
SQL_FILES = sorted(SQL_DIR.glob("*_init_*.sql"))


def read_ddl_text() -> str:
    """把全部建表脚本拼成一份文本（唯一索引/主键等断言跨文件统一计数）。"""
    return "\n".join(path.read_text(encoding="utf-8") for path in SQL_FILES)


_TABLE_RE = re.compile(
    r"CREATE TABLE IF NOT EXISTS `(?P<name>[^`]+)`\s*\((?P<body>.*?)\n\)\s*ENGINE",
    re.DOTALL,
)
_COLUMN_RE = re.compile(r"^\s*`(?P<name>[^`]+)`\s+(?P<type>[a-z]+(?:\(\d+\))?)", re.MULTILINE)


def parse_ddl() -> dict[str, dict[str, dict]]:
    """解析 DDL，返回 ``{表名: {列名: {"type": str, "not_null": bool}}}``。"""
    text = read_ddl_text()
    tables: dict[str, dict[str, dict]] = {}
    for table_match in _TABLE_RE.finditer(text):
        table_name = table_match.group("name")
        columns: dict[str, dict] = {}
        for line in table_match.group("body").splitlines():
            column_match = _COLUMN_RE.match(line)
            if not column_match:
                continue  # PRIMARY KEY / UNIQUE INDEX / INDEX 等约束行
            columns[column_match.group("name")] = {
                "type": column_match.group("type"),
                "not_null": " NOT NULL" in line,
            }
        tables[table_name] = columns
    return tables


class SchemaParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ddl = parse_ddl()

    def test_ddl_files_found(self) -> None:
        """建表脚本必须被找到（改了命名规则要同步改这里的 glob）。"""
        self.assertTrue(SQL_FILES, f"未在 {SQL_DIR} 下找到任何 *_init_*.sql 建表脚本")
        self.assertIn("001_init_auth.sql", [path.name for path in SQL_FILES])

    def test_ddl_covers_all_orm_tables(self) -> None:
        self.assertEqual(
            sorted(self.ddl),
            sorted(Base.metadata.tables),
            "DDL 里的表必须与 ORM 模型一一对应",
        )

    def _normalize_type(self, sqlalchemy_type: str) -> str:
        # SQLAlchemy 的 Integer 生成 "INTEGER"，MySQL DDL 习惯写 "int"
        return {"integer": "int"}.get(sqlalchemy_type, sqlalchemy_type)

    def test_columns_types_and_nullability_match(self) -> None:
        for table_name, orm_table in Base.metadata.tables.items():
            ddl_columns = self.ddl[table_name]
            with self.subTest(table=table_name):
                self.assertEqual(
                    sorted(ddl_columns), sorted(orm_table.columns.keys()), "列集合不一致"
                )
            for column in orm_table.columns:
                with self.subTest(table=table_name, column=column.name):
                    ddl_column = ddl_columns[column.name]
                    expected_type = self._normalize_type(str(column.type).lower())
                    self.assertEqual(
                        ddl_column["type"], expected_type, f"{column.name} 类型不一致"
                    )
                    self.assertEqual(
                        ddl_column["not_null"],
                        not column.nullable,
                        f"{column.name} 可空性不一致（DDL not_null={ddl_column['not_null']}）",
                    )

    def test_primary_keys_declared(self) -> None:
        text = read_ddl_text()
        self.assertEqual(text.count("PRIMARY KEY (`id`)"), len(Base.metadata.tables))

    def test_user_unique_indexes_declared(self) -> None:
        text = read_ddl_text()
        self.assertIn("UNIQUE INDEX `uk_uuid`", text)
        self.assertIn("UNIQUE INDEX `uk_username`", text)

    def test_password_history_index_declared(self) -> None:
        text = read_ddl_text()
        self.assertIn("INDEX `idx_user_uuid`", text)

    def test_dsh_instance_indexes_declared(self) -> None:
        """映射表的唯一索引是防「一用户多实例 / 端口被抢占」的最后一道闸。"""
        text = read_ddl_text()
        self.assertIn("UNIQUE INDEX `uk_user_uuid`", text)
        self.assertIn("UNIQUE INDEX `uk_container_name`", text)
        self.assertIn("UNIQUE INDEX `uk_proxy_user`", text)
        self.assertIn("UNIQUE INDEX `uk_host_port`", text)