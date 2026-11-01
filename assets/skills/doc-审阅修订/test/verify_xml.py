"""深度检查 Track Changes XML 结构"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from zipfile import ZipFile
from lxml import etree
from pathlib import Path

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

docx_path = Path(__file__).parent / 'test_track_output.docx'

with ZipFile(docx_path) as z:
    with z.open('word/document.xml') as f:
        doc_xml = etree.parse(f)
    
    root = doc_xml.getroot()
    body = root.find(f'{{{W}}}body')
    
    # 找到第一个包含 rPrChange 的 run
    for rc in root.iter(f'{{{W}}}rPrChange'):
        parent = rc.getparent()  # 这是 w:rPr
        grandparent = parent.getparent()  # 这是 w:r
        
        print("=" * 60)
        print("rPrChange XML 结构验证")
        print("=" * 60)
        
        # 打印 rPr 的完整结构
        rPr_xml = etree.tostring(parent, pretty_print=True, encoding='unicode')
        # 限制长度
        if len(rPr_xml) > 2500:
            rPr_xml = rPr_xml[:2500] + "\n... (truncated)"
        print(rPr_xml)
        break
    
    # 找到第一个包含 pPrChange 的 pPr
    for pc in root.iter(f'{{{W}}}pPrChange'):
        parent = pc.getparent()
        
        print("\n" + "=" * 60)
        print("pPrChange XML 结构验证")
        print("=" * 60)
        
        pPr_xml = etree.tostring(parent, pretty_print=True, encoding='unicode')
        if len(pPr_xml) > 2500:
            pPr_xml = pPr_xml[:2500] + "\n... (truncated)"
        print(pPr_xml)
        break
    
print("\n" + "=" * 60)
print("验证结论")
print("=" * 60)

# 检查关键属性
errors = []
for rc in root.iter(f'{{{W}}}rPrChange'):
    if rc.get(f'{{{W}}}id') is None:
        errors.append("rPrChange 缺少 w:id")
    if rc.get(f'{{{W}}}author') is None:
        errors.append("rPrChange 缺少 w:author")
    if rc.get(f'{{{W}}}date') is None:
        errors.append("rPrChange 缺少 w:date")
    old_rPr = rc.find(f'{{{W}}}rPr')
    if old_rPr is None:
        errors.append("rPrChange 缺少子 w:rPr")

for pc in root.iter(f'{{{W}}}pPrChange'):
    if pc.get(f'{{{W}}}id') is None:
        errors.append("pPrChange 缺少 w:id")
    if pc.get(f'{{{W}}}author') is None:
        errors.append("pPrChange 缺少 w:author")
    if pc.get(f'{{{W}}}date') is None:
        errors.append("pPrChange 缺少 w:date")
    old_pPr = pc.find(f'{{{W}}}pPr')
    if old_pPr is None:
        errors.append("pPrChange 缺少子 w:pPr")

if errors:
    print("\n错误:")
    for e in errors:
        print(f"  [FAIL] {e}")
else:
    print("\n所有 XML 结构验证通过！")
    print("- rPrChange 包含 w:id, w:author, w:date 属性 ✓")
    print("- rPrChange 包含子 w:rPr 元素 ✓")
    print("- pPrChange 包含 w:id, w:author, w:date 属性 ✓")
    print("- pPrChange 包含子 w:pPr 元素 ✓")
