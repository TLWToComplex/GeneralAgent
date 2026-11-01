"""
测试 Track Changes 修订功能。
验证格式化后的输出文档是否包含 w:rPrChange / w:pPrChange 修订标记。
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from lxml import etree
from pathlib import Path
from zipfile import ZipFile

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def check_track_changes(docx_path: str):
    """检查 docx 文件中是否包含修订标记。"""
    print(f"\n{'='*60}")
    print(f"检查文件: {docx_path}")
    print(f"{'='*60}")

    with ZipFile(docx_path) as z:
        # 检查 document.xml
        with z.open('word/document.xml') as f:
            doc_xml = etree.parse(f)

        root = doc_xml.getroot()

        # 查找修订标记
        rPrChanges = root.findall(f'.//{{{W}}}rPrChange')
        pPrChanges = root.findall(f'.//{{{W}}}pPrChange')

        print(f"\n  修订标记统计:")
        print(f"    w:rPrChange (run属性修改): {len(rPrChanges)} 处")
        print(f"    w:pPrChange (段落属性修改): {len(pPrChanges)} 处")
        print(f"    合计: {len(rPrChanges) + len(pPrChanges)} 处")

        if rPrChanges:
            print(f"\n  rPrChange 详情（前5个）:")
            for i, rc in enumerate(rPrChanges[:5]):
                author = rc.get(f'{{{W}}}author', 'N/A')
                rev_id = rc.get(f'{{{W}}}id', 'N/A')
                date = rc.get(f'{{{W}}}date', 'N/A')
                # 检查旧的 rPr 内容
                old_rPr = rc.find(f'{{{W}}}rPr')
                old_fonts = '无'
                if old_rPr is not None:
                    rFonts = old_rPr.find(f'{{{W}}}rFonts')
                    if rFonts is not None:
                        parts = []
                        for attr in ['eastAsia', 'ascii', 'hAnsi']:
                            val = rFonts.get(f'{{{W}}}{attr}')
                            if val:
                                parts.append(f"{attr}={val}")
                        old_fonts = ', '.join(parts) if parts else '(empty)'
                print(f"    [{i+1}] id={rev_id}, author={author}, date={date}")
                print(f"         旧字体: {old_fonts}")

        if pPrChanges:
            print(f"\n  pPrChange 详情（前5个）:")
            for i, pc in enumerate(pPrChanges[:5]):
                author = pc.get(f'{{{W}}}author', 'N/A')
                rev_id = pc.get(f'{{{W}}}id', 'N/A')
                date = pc.get(f'{{{W}}}date', 'N/A')
                old_pPr = pc.find(f'{{{W}}}pPr')
                old_jc = '无'
                old_ind = '无'
                if old_pPr is not None:
                    jc = old_pPr.find(f'{{{W}}}jc')
                    if jc is not None:
                        old_jc = jc.get(f'{{{W}}}val', '?')
                    ind = old_pPr.find(f'{{{W}}}ind')
                    if ind is not None:
                        left = ind.get(f'{{{W}}}left', '?')
                        fl = ind.get(f'{{{W}}}firstLine', '?')
                        old_ind = f'left={left}, firstLine={fl}'
                print(f"    [{i+1}] id={rev_id}, author={author}, date={date}")
                print(f"         旧对齐: {old_jc}, 旧缩进: {old_ind}")

    result = len(rPrChanges) > 0 or len(pPrChanges) > 0
    print(f"\n  结论: {'PASS' if result else 'FAIL'} - {'有' if result else '无'}修订标记")
    return result


def main():
    test_dir = Path(__file__).parent
    input_file = test_dir / 'test_simple.docx'
    output_file = test_dir / 'test_track_output.docx'

    if not input_file.exists():
        print(f"[SKIP] 测试文件不存在: {input_file}")
        return

    print("=" * 60)
    print("Track Changes 功能测试")
    print("=" * 60)

    # 导入格式化模块
    from format_applier import apply_format, FormatContext
    from spec_loader import load_spec
    from doc_analyzer import analyze_document

    spec = load_spec(str(test_dir.parent / 'templates' / 'default-spec.json'))
    print(f"\n已加载规范: {spec.name if hasattr(spec, 'name') else 'default-spec.json'}")

    # 执行格式化（默认 track_changes=True）
    try:
        result_path = apply_format(
            str(input_file),
            spec,
            str(output_file)
        )
        print(f"\n格式化完成: {result_path}")
    except Exception as e:
        print(f"\n格式化失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 检查修订标记
    if output_file.exists():
        check_track_changes(str(output_file))
    else:
        print(f"\n[ERROR] 输出文件不存在: {output_file}")


if __name__ == '__main__':
    main()
