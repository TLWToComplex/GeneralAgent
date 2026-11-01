"""
track_changes.py — Track Changes 修订追踪模块

实现 OOXML 修订标记（w:rPrChange / w:pPrChange），
每次格式修改自动在 XML 中插入修订记录，
使 Word/WPS 能够以"修订模式"展示所有格式变更。

工作原理：
  w:rPrChange → 记录 run 属性（字体、字号、加粗、斜体等）的修改
  w:pPrChange → 记录段落属性（对齐、缩进、行距等）的修改

  每个 Change 元素包含：
  - w:id     → 全局唯一修订编号
  - w:author → 修订者名称
  - w:date   → 修订时间（ISO 8601 UTC）
  - 子 w:rPr/w:pPr → 修改前的旧属性值
"""

from datetime import datetime, timezone
from copy import deepcopy
from lxml import etree

from utils import NSMAP

W = NSMAP['w']

# ──────────────────────────────────────────────
# 修订追踪器
# ──────────────────────────────────────────────


class RevisionTracker:
    """修订追踪器。

    管理修订 ID 生成、作者名和时间戳。
    一个文档实例对应一个 RevisionTracker，确保所有修订 ID 全局唯一。
    """

    def __init__(self, author: str = "doc-审阅修订"):
        self.author = author
        self._next_id = 1

    def next_id(self) -> int:
        """获取下一个修订 ID，自动递增。"""
        current = self._next_id
        self._next_id += 1
        return current

    @staticmethod
    def now_iso() -> str:
        """当前 UTC 时间的 ISO 8601 格式化字符串。"""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ──────────────────────────────────────────────
# XML 深拷贝（lxml 安全版）
# ──────────────────────────────────────────────


def deepcopy_element(elem: etree._Element) -> etree._Element:
    """安全深拷贝 lxml 元素。

    使用 tostring → fromstring 确保完全独立，
    避免 copy.deepcopy 在部分 lxml 版本中的父引用问题。
    """
    return etree.fromstring(etree.tostring(elem))


def elements_equal(e1: etree._Element, e2: etree._Element) -> bool:
    """比较两个 lxml 元素是否等价（忽略 rPrChange/pPrChange 标记元素）。

    比较维度：标签、属性、子元素（递归）。
    用于判断格式修订是否有实际差异——如果 old == new，跳过记录。
    """
    if e1.tag != e2.tag:
        return False

    # 排除修订标记元素后比较属性
    attrs1 = {k: v for k, v in e1.attrib.items()}
    attrs2 = {k: v for k, v in e2.attrib.items()}
    if attrs1 != attrs2:
        return False

    # 比较子元素（排除 rPrChange / pPrChange）
    children1 = [c for c in e1 if c.tag not in (f'{{{W}}}rPrChange', f'{{{W}}}pPrChange')]
    children2 = [c for c in e2 if c.tag not in (f'{{{W}}}rPrChange', f'{{{W}}}pPrChange')]

    if len(children1) != len(children2):
        return False

    for c1, c2 in zip(children1, children2):
        if not elements_equal(c1, c2):
            return False

    return True


# ──────────────────────────────────────────────
# w:rPrChange — Run 属性修订
# ──────────────────────────────────────────────


def track_rPr_change(rPr_elem: etree._Element, old_rPr_elem: etree._Element,
                     tracker: RevisionTracker) -> bool:
    """在 rPr 元素中插入 w:rPrChange 修订标记。

    Args:
        rPr_elem:     当前的 w:rPr 元素（修改后的新值所在位置）
        old_rPr_elem: 修改前的 w:rPr 元素副本（旧属性）
        tracker:      RevisionTracker 实例（提供 id/author/date）

    Returns:
        bool: True 表示成功插入修订标记，False 表示跳过（无差异或已存在）。

    插入位置：rPrChange 作为 rPr 的第一个子元素。
    修正记录结构：
      <w:rPr>                          ← 当前（新值）
        <w:rPrChange w:id="1" ...>     ← 修订标记
          <w:rPr>                      ← 旧属性
            <w:rFonts .../>
            <w:sz w:val="24"/>
          </w:rPr>
        </w:rPrChange>
        <w:rFonts .../>               ← 新值
        <w:sz w:val="32"/>
      </w:rPr>
    """
    # 已有 rPrChange 则跳过（避免重复标记）
    existing = rPr_elem.find(f'{{{W}}}rPrChange')
    if existing is not None:
        return False

    # 从旧 rPr 中移除已有的 rPrChange（避免递归嵌套）
    old_change = old_rPr_elem.find(f'{{{W}}}rPrChange')
    if old_change is not None:
        old_rPr_elem.remove(old_change)

    # 跳过空修订：old == new 时不记录（避免噪声）
    if elements_equal(old_rPr_elem, rPr_elem):
        return False

    rPrChange = etree.Element(f'{{{W}}}rPrChange')
    rPrChange.set(f'{{{W}}}id', str(tracker.next_id()))
    rPrChange.set(f'{{{W}}}author', tracker.author)
    rPrChange.set(f'{{{W}}}date', tracker.now_iso())
    rPrChange.append(old_rPr_elem)

    # 插入为 rPr 的第一个子元素
    rPr_elem.insert(0, rPrChange)
    return True


# ──────────────────────────────────────────────
# w:pPrChange — 段落属性修订
# ──────────────────────────────────────────────


def track_pPr_change(pPr_elem: etree._Element, old_pPr_elem: etree._Element,
                     tracker: RevisionTracker) -> bool:
    """在 pPr 元素中插入 w:pPrChange 修订标记。

    Args:
        pPr_elem:     当前的 w:pPr 元素（修改后的新值所在位置）
        old_pPr_elem: 修改前的 w:pPr 元素副本（旧属性）
        tracker:      RevisionTracker 实例

    Returns:
        bool: True 表示成功插入修订标记，False 表示跳过。

    插入结构与 track_rPr_change 对称：
      <w:pPr>
        <w:pPrChange w:id="..." ...>
          <w:pPr>
            <w:jc w:val="left"/>
            <w:ind w:left="720" .../>
          </w:pPr>
        </w:pPrChange>
        <w:jc w:val="center"/>
        <w:ind w:left="0" .../>
      </w:pPr>
    """
    existing = pPr_elem.find(f'{{{W}}}pPrChange')
    if existing is not None:
        return False

    old_change = old_pPr_elem.find(f'{{{W}}}pPrChange')
    if old_change is not None:
        old_pPr_elem.remove(old_change)

    # 跳过空修订
    if elements_equal(old_pPr_elem, pPr_elem):
        return False

    pPrChange = etree.Element(f'{{{W}}}pPrChange')
    pPrChange.set(f'{{{W}}}id', str(tracker.next_id()))
    pPrChange.set(f'{{{W}}}author', tracker.author)
    pPrChange.set(f'{{{W}}}date', tracker.now_iso())
    pPrChange.append(old_pPr_elem)

    pPr_elem.insert(0, pPrChange)
    return True
