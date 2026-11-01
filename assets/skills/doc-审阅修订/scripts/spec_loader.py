"""
spec_loader.py — 格式规范文件加载与校验

负责：
1. 从 JSON 文件加载格式规范
2. 基本结构校验（必填字段、值域）
3. 默认值填充
4. 返回规范化的 Spec 对象
"""

import json
from pathlib import Path
from copy import deepcopy
from utils import log


# ──────────────────────────────────────────────
# 默认值
# ──────────────────────────────────────────────

DEFAULT_SPEC = {
    "version": "1.0",
    "meta": {
        "name": "默认文档格式规范",
        "description": "",
        "author": ""
    },
    "page": {
        "size": "A4",
        "orientation": "portrait",
        "margin_top_cm": 2.54,
        "margin_bottom_cm": 2.54,
        "margin_left_cm": 1.91,
        "margin_right_cm": 1.91,
        "header_distance_cm": 1.5,
        "footer_distance_cm": 1.75
    },
    "fonts": {
        "_comment": "全文（含封面）中文字体为宋体，英文字体为 Times New Roman",
        "cover_title":     {"cjk": "宋体", "latin": "Times New Roman"},
        "cover_subtitle":  {"cjk": "宋体", "latin": "Times New Roman"},
        "cover_info":      {"cjk": "宋体", "latin": "Times New Roman"},
        "body":            {"cjk": "宋体", "latin": "Times New Roman"},
        "h1":              {"cjk": "宋体", "latin": "Times New Roman"},
        "h2":              {"cjk": "宋体", "latin": "Times New Roman"},
        "h3":              {"cjk": "宋体", "latin": "Times New Roman"},
        "h4":              {"cjk": "宋体", "latin": "Times New Roman"},
        "toc_title":       {"cjk": "宋体", "latin": "Times New Roman"},
        "toc_body":        {"cjk": "宋体", "latin": "Times New Roman"},
        "revision_title":  {"cjk": "宋体", "latin": "Times New Roman"},
        "revision_header": {"cjk": "宋体", "latin": "Times New Roman"},
        "revision_body":   {"cjk": "宋体", "latin": "Times New Roman"},
        "page_number":     {"cjk": "宋体", "latin": "Times New Roman"},
        "header":          {"cjk": "宋体", "latin": "Times New Roman"},
        "table_caption":   {"cjk": "宋体", "latin": "Times New Roman"},
        "figure_caption":  {"cjk": "宋体", "latin": "Times New Roman"}
    },
    "sizes": {
        "cover_title_pt":    22,
        "cover_subtitle_pt": 22,
        "cover_info_pt":     14,
        "body_pt":           12,
        "table_body_pt":     10.5,
        "header_pt":         10.5,
        "h1_pt":             12,
        "h2_pt":             12,
        "h3_pt":             12,
        "h4_pt":             12,
        "toc_title_pt":      12,
        "toc_body_pt":       12,
        "revision_title_pt": 12,
        "revision_header_pt":10.5,
        "revision_body_pt":  12,
        "page_number_pt":    9,
        "table_caption_pt":  10.5,
        "figure_caption_pt": 10.5
    },
    "spacing": {
        "body_line_spacing_pt":    1.5,
        "body_line_spacing_mode":  "multiple",
        "title_line_spacing_pt":   1.5,
        "title_line_spacing_mode": "multiple",
        "header_line_spacing_pt":  1.0,
        "header_line_spacing_mode":"multiple",
        "first_line_indent_chars": 2,
        "english_first_line_indent_chars": 4,
        "heading_indent_chars":    0,
        "paragraph_before_pt":     0,
        "paragraph_after_pt":      0,
        "snap_to_grid":            False,
        "contextual_spacing":      False
    },
    "heading": {
        "bold": False,
        "alignment": "left",
        "detection": {
            "h1": "^\\d+\\s+[\\u4e00-\\u9fff]",
            "h2": "^\\d+\\.\\d+\\s+[\\u4e00-\\u9fff]",
            "h3": "^\\d+\\.\\d+\\.\\d+\\s+[\\u4e00-\\u9fff]",
            "h4": "^\\d+\\.\\d+\\.\\d+\\.\\d+\\s+[\\u4e00-\\u9fff]"
        },
        "level_bold": {
            "h1": False,
            "h2": False,
            "h3": False,
            "h4": False
        },
        "fallback_detection": {
            "cn_numeral": "^[一二三四五六七八九十]+、",
            "cn_paren": "^（[一二三四五]）",
            "digit_dot": "^[1-9]\\.",
            "paren_digit": "^（[1-5]）"
        }
    },
    "figure_caption": {
        "detection_regex": "^(图\\s*\\d+(-\\d+)?|Figure\\s*\\d+|Fig\\.?\\s*\\d+)"
    },
    "table_caption": {
        "detection_regex": "^(表\\s*\\d+(-\\d+)?|Table\\s*\\d+)"
    },
    "numbering_reset": {
        "enabled": True,
        "triggers": {
            "after_heading": True,
            "after_body_text": True,
            "on_level_change": True
        },
        "levels": [1, 2]
    },
    "list": {
        "levels": [
            {"level":1,"type":"ordered","num_id":100,"left_twips":0,"hanging_twips":420,"desc":"L1"},
            {"level":2,"type":"ordered","num_id":101,"left_twips":420,"hanging_twips":420,"desc":"L2"},
            {"level":3,"type":"unordered","num_id":102,"left_twips":839,"hanging_twips":420,"desc":"L3"},
            {"level":4,"type":"unordered","num_id":103,"left_twips":1259,"hanging_twips":420,"desc":"L4"},
            {"level":5,"type":"unordered","num_id":104,"left_twips":1678,"hanging_twips":420,"desc":"L5"}
        ],
        "detection": {
            "L1": "^[a-zA-Z][)]\\s*",
            "L2": "^\\d+[)\\uff09]\\s*",
            "L3": "^[-\\u2013\\u2014]\\s+",
            "L4": "^[\\u25CF\\u25A0\\u25A1\\u25CB\\u25AA\\u25B8\\u25E2\\u2022\\u00B7]\\s*",
            "L5": "^[\\u25CB\\u25C7\\u25C6]\\s*"
        },
        "numbering_defs": {
            "100": {"numFmt":"lowerLetter","lvlText":"%1)","start":1},
            "101": {"numFmt":"decimal","lvlText":"%1)","start":1},
            "102": {"numFmt":"bullet","lvlText":"-","start":1},
            "103": {"numFmt":"bullet","lvlText":"\u25CF","bulletFont":"Times New Roman","start":1},
            "104": {"numFmt":"bullet","lvlText":"\u25CB","bulletFont":"Times New Roman","start":1}
        }
    },
    "alignment": {
        "cover_title":    "center",
        "cover_subtitle": "center",
        "cover_info":     "center",
        "body":           "both",
        "toc_title":      "center",
        "revision_title": "center",
        "revision_header":"center",
        "revision_body":  "center",
        "header":         "center",
        "page_number":    "center",
        "figure_caption":  "center",
        "table_caption":   "center"
    },
    "special_sections": {
        "revision_history": {
            "enabled": True,
            "detection_keywords": ["修订记录", "版本历史", "修订历史",
                                   "Revision History", "变更记录"],
            "table_columns": ["版本号", "修订日期", "修订内容", "修订人", "审核人"],
            "column_widths_cm": [2.0, 2.5, 8.0, 2.0, 2.0],
            "header_bold": True,
            "header_shading": "D9E2F3",
            "border_style": "single",
            "row_height_cm": 0.8
        },
        "toc": {
            "enabled": True,
            "detection_keywords": ["目录", "目  录", "Table of Contents"],
            "auto_generate": False
        },
        "cover": {
            "enabled": True,
            "detection_by": "first_section_titlePg",
            "max_pages": 2,
            "title_bold": True,
            "subtitle_bold": True,
            "detection_keywords": ["项目令号", "密级", "文件编号", "版本", "阶段", "拟制", "审核", "会签", "批准", "日期", "阶段标记"]
        }
    },
    "validation": {
        "strict_mode": True,
        "max_retries": 5,
        "tolerances": {
            "first_line_indent_pt": 3,
            "list_indent_cm": 0.25,
            "heading_indent_pt": 1.0,
            "line_spacing_pt": 1.0
        },
        "checks": [
            "page_margins", "page_size", "cover_fonts", "body_fonts",
            "heading_fonts", "revision_section", "toc_section",
            "line_spacing", "paragraph_alignment", "first_line_indent",
            "page_numbers", "table_borders", "table_header_fonts",
            "table_body_fonts", "header_fonts", "footer_fonts",
            "list_indent", "heading_indent", "figure_caption", "table_caption"
        ]
    }
}


# ──────────────────────────────────────────────
# 合法值域
# ──────────────────────────────────────────────

VALID_PAGE_SIZES = {"A4", "A3", "Letter", "Legal"}
VALID_ORIENTATIONS = {"portrait", "landscape"}
VALID_ALIGNMENTS = {"left", "center", "right", "both", "奇偶分页"}


# ──────────────────────────────────────────────
# Spec 类
# ──────────────────────────────────────────────

class Spec:
    """格式规范对象，提供属性访问和便捷查询方法。"""

    def __init__(self, data: dict):
        self._data = data

    # --- 便捷属性 ---
    @property
    def page(self): return self._data['page']

    @property
    def fonts(self): return self._data['fonts']

    @property
    def sizes(self): return self._data['sizes']

    @property
    def spacing(self): return self._data['spacing']

    @property
    def alignment(self): return self._data['alignment']

    @property
    def special_sections(self): return self._data['special_sections']

    @property
    def validation(self): return self._data['validation']

    @property
    def meta(self): return self._data['meta']

    @property
    def version(self): return self._data['version']

    @property
    def heading(self): return self._data.get('heading', {})

    @property
    def list(self): return self._data.get('list', {})

    @property
    def numbering_reset(self): return self._data.get('numbering_reset', {})

    @property
    def figure_caption(self): return self._data.get('figure_caption', {})

    @property
    def table_caption(self): return self._data.get('table_caption', {})

    # --- 便捷查询 ---

    def font_pair(self, key: str) -> dict:
        """获取字体配对 {cjk, latin}。"""
        return self.fonts.get(key, self.fonts['body'])

    def size_pt(self, key: str) -> float:
        """获取字号（pt）。"""
        return self.sizes.get(key, 16)

    def line_spacing_pt(self, element: str) -> float:
        """获取行间距（pt）。"""
        if element in ('h1', 'h2', 'h3', 'h4', 'cover_title', 'cover_subtitle', 'toc_title', 'revision_title'):
            return self.spacing['title_line_spacing_pt']
        return self.spacing['body_line_spacing_pt']

    def alignment_for(self, key: str, default: str = 'both') -> str:
        """获取对齐方式。"""
        return self.alignment.get(key, default)

    def to_dict(self) -> dict:
        return deepcopy(self._data)


# ──────────────────────────────────────────────
# 加载与校验
# ──────────────────────────────────────────────

def load_spec(spec_path: str = None) -> Spec:
    """
    加载格式规范文件。

    Args:
        spec_path: JSON 规范文件路径。为 None 时返回默认规范。

    Returns:
        Spec 对象

    Raises:
        FileNotFoundError: 文件不存在
        json.JSONDecodeError: JSON 解析错误
        ValueError: 校验失败
    """
    if spec_path is None:
        log.info("使用内置默认格式规范")
        return Spec(deepcopy(DEFAULT_SPEC))

    p = Path(spec_path)
    if not p.exists():
        raise FileNotFoundError(f"规范文件不存在: {spec_path}")

    log.info(f"加载规范文件: {spec_path}")

    with open(p, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    # 基础校验
    _validate_basic(raw)

    # 深度合并默认值（用户未提供的字段使用默认值）
    merged = deepcopy(DEFAULT_SPEC)
    _deep_merge(merged, raw)

    # 值域校验
    _validate_values(merged)

    log.info(f"规范加载成功: {merged['meta'].get('name', '未命名')} v{merged.get('version', '?')}")
    return Spec(merged)


# ──────────────────────────────────────────────
# 校验函数
# ──────────────────────────────────────────────

def _validate_basic(data: dict):
    """基础结构校验。"""
    # version 检查
    if 'version' in data and not isinstance(data['version'], str):
        raise ValueError(f"version 必须是字符串: {data['version']}")

    # fonts 结构检查
    if 'fonts' in data:
        for key, pair in data['fonts'].items():
            if key.startswith('_'):
                continue  # 跳过注释/元数据键
            if not isinstance(pair, dict):
                raise ValueError(f"fonts.{key} 必须是对象，如 {{'cjk': '...', 'latin': '...'}}")
            if 'cjk' not in pair or 'latin' not in pair:
                raise ValueError(f"fonts.{key} 缺少 cjk 或 latin 字段")


def _validate_values(data: dict):
    """值域校验。"""
    # 页面设置
    page = data.get('page', {})
    if page.get('size') not in VALID_PAGE_SIZES:
        raise ValueError(f"无效的页面尺寸: {page.get('size')}，合法值: {VALID_PAGE_SIZES}")
    if page.get('orientation') not in VALID_ORIENTATIONS:
        raise ValueError(f"无效的页面方向: {page.get('orientation')}，合法值: {VALID_ORIENTATIONS}")

    # 对齐方式
    for key, val in data.get('alignment', {}).items():
        if key.startswith('_'):
            continue
        if val not in VALID_ALIGNMENTS:
            raise ValueError(f"无效的对齐方式 alignment.{key}={val}，合法值: {VALID_ALIGNMENTS}")

    # 字号范围（跳过注释键）
    for key, val in data.get('sizes', {}).items():
        if key.startswith('_'):
            continue
        if not isinstance(val, (int, float)) or val < 1 or val > 128:
            raise ValueError(f"无效的字号 sizes.{key}={val}，应在 1-128 pt 之间")

    # 数值范围
    spacing = data.get('spacing', {})
    for key in ('body_line_spacing_pt', 'title_line_spacing_pt'):
        if key in spacing and (spacing[key] < 0 or spacing[key] > 200):
            raise ValueError(f"{key} 应在 0-200 pt 之间: {spacing[key]}")


def _deep_merge(base: dict, override: dict):
    """深度合并 override 到 base 中，base 原地修改。"""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = deepcopy(value)


# ──────────────────────────────────────────────
# 导出规范文件
# ──────────────────────────────────────────────

def export_spec(spec: Spec, output_path: str):
    """将规范导出为 JSON 文件。"""
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(spec.to_dict(), f, ensure_ascii=False, indent=2)
    log.info(f"规范已导出到: {output_path}")
