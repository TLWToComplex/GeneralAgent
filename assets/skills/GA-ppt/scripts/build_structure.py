# -*- coding: utf-8 -*-
import sys, json, re, shutil, zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

try:
    import defusedxml.minidom as minidom_parser
except ImportError:
    import xml.dom.minidom as minidom_parser

CHAPTER_CHARS = ["\u4e00", "\u4e8c", "\u4e09", "\u56db", "\u4e94"]
TITLE_BAR_NAMES = {
    "\u4e00": "\u77e9\u5f62 25",
    "\u4e8c": "\u77e9\u5f62 6",
    "\u4e09": "\u77e9\u5f62 3",
    "\u56db": "\u77e9\u5f62 9",
    "\u4e94": "\u77e9\u5f62 13",
}
ORIGINAL_TITLE = "\u5927\u6a21\u578b\u5e94\u7528\u80fd\u529b\u63d0\u5347\u57f9\u8bad\u65b9\u6848\u4e13\u5bb6\u8bc4\u5ba1\u4f1a"
ORIGINAL_HEADER = "\u6c47\u62a5\u5185\u5bb9"

def parse_xml(path):
    return minidom_parser.parse(str(path))

def write_xml(dom, path):
    Path(path).write_bytes(dom.toxml(encoding='utf-8'))

def get_sp_text(sp):
    texts = []
    for t in sp.getElementsByTagName('a:t'):
        if t.firstChild:
            texts.append(t.firstChild.nodeValue)
    return ''.join(texts).strip()

def get_sp_name(sp):
    cNvPr = sp.getElementsByTagName('p:cNvPr')
    return cNvPr[0].getAttribute('name') if cNvPr else ''

def split_title(title_text):
    if len(title_text) <= 4:
        return title_text, ""
    mid = len(title_text) // 2
    return title_text[:mid], title_text[mid:]

def unpack_template(reference_path, output_dir):
    output_dir = Path(output_dir)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    with zipfile.ZipFile(str(reference_path), 'r') as z:
        z.extractall(str(output_dir))
    for d in ['__MACOSX']:
        p = output_dir / d
        if p.exists():
            shutil.rmtree(p)
    print(f"Unpacked {reference_path} -> {output_dir}")

def edit_cover(base_dir, title):
    slide_path = Path(base_dir) / "ppt" / "slides" / "slide1.xml"
    slide_text = slide_path.read_text(encoding="utf-8")
    slide_text = slide_text.replace(ORIGINAL_TITLE, title)
    slide_path.write_text(slide_text, encoding="utf-8")
    print(f"Cover: title -> \"{title}\"")

def make_divider(base_dir, highlight_index, num_chapters, chapter_titles):
    slides_dir = Path(base_dir) / "ppt" / "slides"
    dom = parse_xml(slides_dir / "slide2.xml")
    all_chars = CHAPTER_CHARS[:5]
    target_char = CHAPTER_CHARS[highlight_index]
    target_bar = TITLE_BAR_NAMES.get(target_char, '')

    # Step 1: Chapter NUMBER text colors
    for sp in dom.getElementsByTagName('p:sp'):
        text = get_sp_text(sp)
        if text not in all_chars:
            continue
        txBody_list = [c for c in sp.childNodes if c.nodeName == 'p:txBody']
        if not txBody_list:
            continue
        txBody = txBody_list[0]
        if text == target_char:
            for elem in list(txBody.getElementsByTagName('a:srgbClr')):
                if elem.getAttribute('val') == 'D20000':
                    elem.setAttribute('val', 'C00000')
            for elem in list(txBody.getElementsByTagName('a:prstClr')):
                if elem.getAttribute('val') == 'black':
                    srgb = dom.createElement('a:srgbClr')
                    srgb.setAttribute('val', 'C00000')
                    elem.parentNode.replaceChild(srgb, elem)
        else:
            for elem in list(txBody.getElementsByTagName('a:srgbClr')):
                if elem.getAttribute('val') == 'D20000':
                    preset = dom.createElement('a:prstClr')
                    preset.setAttribute('val', 'black')
                    elem.parentNode.replaceChild(preset, elem)

    # Step 2: Title bar FILLS
    for sp in dom.getElementsByTagName('p:sp'):
        name = get_sp_name(sp)
        if name not in TITLE_BAR_NAMES.values():
            continue
        spPr_list = [c for c in sp.childNodes if c.nodeName == 'p:spPr']
        if not spPr_list:
            continue
        spPr = spPr_list[0]
        is_highlighted = (name == target_bar)
        for fn in ['a:solidFill', 'a:noFill', 'a:grpFill', 'a:pattFill', 'a:blipFill']:
            for old in list(c for c in spPr.childNodes if c.nodeName == fn):
                spPr.removeChild(old)
        sf = dom.createElement('a:solidFill')
        srgb = dom.createElement('a:srgbClr')
        srgb.setAttribute('val', 'C00000' if is_highlighted else 'CECECE')
        sf.appendChild(srgb)
        insert_after = None
        for child in spPr.childNodes:
            if child.nodeType == child.ELEMENT_NODE and child.nodeName == 'a:prstGeom':
                insert_after = child
        if insert_after and insert_after.nextSibling:
            spPr.insertBefore(sf, insert_after.nextSibling)
        else:
            spPr.appendChild(sf)

    # Step 2b: Title bar TEXT colors
    for sp in dom.getElementsByTagName('p:sp'):
        name = get_sp_name(sp)
        if name not in TITLE_BAR_NAMES.values():
            continue
        is_highlighted = (name == target_bar)
        for rPr in sp.getElementsByTagName('a:rPr'):
            sf_list = rPr.getElementsByTagName('a:solidFill')
            if sf_list:
                sf = sf_list[0]
                for child in list(sf.childNodes):
                    if child.nodeType == child.ELEMENT_NODE:
                        sf.removeChild(child)
                if is_highlighted:
                    sc = dom.createElement('a:schemeClr')
                    sc.setAttribute('val', 'bg1')
                else:
                    sc = dom.createElement('a:prstClr')
                    sc.setAttribute('val', 'black')
                sf.appendChild(sc)
        for epr in sp.getElementsByTagName('a:endParaRPr'):
            sf_list = epr.getElementsByTagName('a:solidFill')
            if sf_list:
                sf = sf_list[0]
                for child in list(sf.childNodes):
                    if child.nodeType == child.ELEMENT_NODE:
                        sf.removeChild(child)
                if is_highlighted:
                    sc = dom.createElement('a:schemeClr')
                    sc.setAttribute('val', 'bg1')
                else:
                    sc = dom.createElement('a:prstClr')
                    sc.setAttribute('val', 'black')
                sf.appendChild(sc)

    # Step 3: Remove unused chapters
    chars_to_remove = all_chars[num_chapters:]
    bars_to_remove = [TITLE_BAR_NAMES[ch] for ch in chars_to_remove if ch in TITLE_BAR_NAMES]
    for sp in list(dom.getElementsByTagName('p:sp')):
        name = get_sp_name(sp)
        text = get_sp_text(sp)
        if name in bars_to_remove or text in chars_to_remove:
            sp.parentNode.removeChild(sp)

    # Step 4: Fix global colors
    for elem in dom.getElementsByTagName('a:srgbClr'):
        val = elem.getAttribute('val')
        if val in ('D20000', 'FF0000'):
            elem.setAttribute('val', 'C00000')

    # Step 5: Update header
    for sp in dom.getElementsByTagName('p:sp'):
        for t in sp.getElementsByTagName('a:t'):
            if t.firstChild and t.firstChild.nodeValue == ORIGINAL_HEADER:
                t.firstChild.nodeValue = "\u76ee\u5f55"

    # Step 6: Update chapter titles
    bar_order = ["\u77e9\u5f62 25", "\u77e9\u5f62 6", "\u77e9\u5f62 3", "\u77e9\u5f62 9", "\u77e9\u5f62 13"]
    for bar_idx, bar_name in enumerate(bar_order):
        if bar_idx >= num_chapters or bar_idx >= len(chapter_titles):
            break
        new_title = chapter_titles[bar_idx]
        part1, part2 = split_title(new_title)
        for sp in dom.getElementsByTagName('p:sp'):
            if get_sp_name(sp) != bar_name:
                continue
            runs = sp.getElementsByTagName('a:r')
            run_idx = 0
            if run_idx < len(runs):
                t_elem = runs[run_idx].getElementsByTagName('a:t')
                if t_elem and t_elem[0].firstChild:
                    t_elem[0].firstChild.nodeValue = part1
                run_idx += 1
            if part2 and run_idx < len(runs):
                t_elem = runs[run_idx].getElementsByTagName('a:t')
                if t_elem and t_elem[0].firstChild:
                    t_elem[0].firstChild.nodeValue = part2
                run_idx += 1
            while run_idx < len(runs):
                t_elem = runs[run_idx].getElementsByTagName('a:t')
                if t_elem and t_elem[0].firstChild:
                    t_elem[0].firstChild.nodeValue = ""
                run_idx += 1
            break

    return dom

def build_dividers(base_dir, chapter_titles):
    slides_dir = Path(base_dir) / "ppt" / "slides"
    rels_dir = slides_dir / "_rels"
    num_chapters = len(chapter_titles)
    s2r = (rels_dir / "slide2.xml.rels").read_text(encoding="utf-8")
    s2r_nn = re.sub(r'\s*<Relationship[^>]*notesSlide[^>]*/>\s*', '\n', s2r)
    for ch_idx in range(num_chapters):
        slide_num = 5 + ch_idx
        dom = make_divider(base_dir, ch_idx, num_chapters, chapter_titles)
        write_xml(dom, slides_dir / f"slide{slide_num}.xml")
        (rels_dir / f"slide{slide_num}.xml.rels").write_text(s2r_nn, encoding="utf-8")
        print(f"Divider: slide{slide_num} (chapter {ch_idx+1}: {chapter_titles[ch_idx]})")

def update_relationships(base_dir, num_chapters):
    base = Path(base_dir)
    prp = base / "ppt" / "_rels" / "presentation.xml.rels"
    pr = prp.read_text(encoding="utf-8")
    for i in range(16, 30):
        pr = re.sub(rf'\s*<Relationship[^>]*Id="rId{i}"[^>]*/>\s*', '\n', pr)
    nr = ""
    for i in range(num_chapters):
        rid = f"rId{16+i}"
        slide_num = 5 + i
        nr += f'  <Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{slide_num}.xml"/>\n'
    pr = pr.replace('</Relationships>', nr + '</Relationships>')
    prp.write_text(pr, encoding="utf-8")
    print(f"Relationships: rId16-rId{15+num_chapters} added")

    ctp = base / "[Content_Types].xml"
    ct = ctp.read_text(encoding="utf-8")
    for i in range(5, 15):
        ct = re.sub(rf'\s*<Override[^>]*slide{i}\.xml[^>]*/>\s*', '\n', ct)
    ov = ""
    for i in range(num_chapters):
        slide_num = 5 + i
        ov += f'  <Override PartName="/ppt/slides/slide{slide_num}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>\n'
    ct = ct.replace('</Types>', ov + '</Types>')
    ctp.write_text(ct, encoding="utf-8")
    print("Content_Types: updated")

    pp = base / "ppt" / "presentation.xml"
    pc = pp.read_text(encoding="utf-8")
    sld_entries = []
    sld_id = 256
    sld_entries.append(f'    <p:sldId id="{sld_id}" r:id="rId5"/>')
    sld_id += 1
    for i in range(num_chapters):
        rid = f"rId{16+i}"
        sld_entries.append(f'    <p:sldId id="{sld_id}" r:id="{rid}"/>')
        sld_id += 1
    sld_entries.append(f'    <p:sldId id="{sld_id}" r:id="rId9"/>')
    ns_xml = "<p:sldIdLst>\n" + "\n".join(sld_entries) + "\n  </p:sldIdLst>"
    pc = re.sub(r'<p:sldIdLst>.*?</p:sldIdLst>', ns_xml, pc, flags=re.DOTALL)
    pp.write_text(pc, encoding="utf-8")
    print("presentation.xml: slide order set")

def main():
    if len(sys.argv) < 2:
        print("Usage: python build_structure.py config.json")
        sys.exit(1)

    config_path = sys.argv[1]
    with open(config_path, 'r', encoding='utf-8-sig') as f:
        config = json.load(f)

    reference = config.get("reference", "templates/reference.pptx")
    output = config.get("output", "unpacked")
    cover_title = config.get("cover", {}).get("title", "")
    chapters = config.get("chapters", [])

    if not cover_title:
        print("ERROR: cover.title is required")
        sys.exit(1)
    if not chapters:
        print("ERROR: chapters list is required (1-5 chapters)")
        sys.exit(1)
    if len(chapters) > 5:
        print(f"ERROR: max 5 chapters supported, got {len(chapters)}")
        sys.exit(1)

    print(f"=== Building PPT structure ===")
    print(f"Title: {cover_title}")
    print(f"Chapters ({len(chapters)}): {', '.join(chapters)}")
    print()

    unpack_template(reference, output)
    edit_cover(output, cover_title)
    build_dividers(output, chapters)
    update_relationships(output, len(chapters))

    print(f"\n=== Structure ready! ===")
    print(f"Output: {output}/")
    print(f"Slides: slide1 (cover) + slide5-{4+len(chapters)} (dividers) + slide4 (end)")
    print(f"Next: generate content pages with PptxGenJS, then merge.")

if __name__ == "__main__":
    main()