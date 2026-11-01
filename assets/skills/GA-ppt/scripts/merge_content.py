# -*- coding: utf-8 -*-
"""
merge_content.py - Deterministic content page merger.

Copies PptxGenJS content slides into template, preserving the complete
master chain: content_slide -> slideLayout -> slideMaster -> theme.
Content page XML is never modified; background + red bar are injected
into the copied slideMaster.

Usage:
    python scripts/merge_content.py config.json

Config JSON format:
{
  "template_dir": "unpacked",
  "content_pptx": "content_slides.pptx",
  "output": "output.pptx",
  "layout": [
    {"chapter": 1, "content_pages": 3},
    {"chapter": 2, "content_pages": 2}
  ]
}
"""
import sys
import json
import re
import shutil
import subprocess
import zipfile
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SCRIPTS_DIR = Path(__file__).parent
SLIDE_REL_RE = re.compile(
    r'<Relationship[^>]*Id="(rId\d+)"[^>]*'
    r'Target="slides/slide(\d+)\.xml"[^>]*/>'
)


# ============================================================
#  Final output compatibility fixes
# ============================================================

FULL_SLIDE_CX = 9144000
FULL_SLIDE_CY = 5143500
OVERSCAN_X = 91440    # 1% of 16:9 slide width
OVERSCAN_Y = 51435    # 1% of 16:9 slide height
OVERSCAN_CX = FULL_SLIDE_CX + OVERSCAN_X * 2
OVERSCAN_CY = FULL_SLIDE_CY + OVERSCAN_Y * 2


def _update_slide_overrides_in_content_types(template_dir, slide_count):
    """Rewrite slide Override entries to match physical slide1..slideN.xml order."""
    ctp = template_dir / "[Content_Types].xml"
    if not ctp.exists():
        return

    ct = ctp.read_text(encoding="utf-8")
    slide_ct = "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"

    # Remove old slide overrides, including orphaned template slides.
    ct = re.sub(
        r'\s*<Override\s+PartName="/ppt/slides/slide\d+\.xml"\s+'
        r'ContentType="application/vnd\.openxmlformats-officedocument\.presentationml\.slide\+xml"\s*/>',
        '',
        ct,
    )

    overrides = ''.join(
        f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="{slide_ct}"/>'
        for i in range(1, slide_count + 1)
    )
    ct = ct.replace('</Types>', overrides + '</Types>')
    ctp.write_text(ct, encoding="utf-8")


def enforce_physical_slide_order(template_dir, sld_entries):
    """Rename ppt/slides/slideN.xml so file order matches presentation order.

    Some company PPT previewers read slide files by physical filename order instead of
    respecting ppt/presentation.xml <p:sldIdLst>. PowerPoint/PDF export uses sldIdLst,
    but those previewers show all divider pages before content pages. This function
    keeps the existing rIds/play order, then rewrites the slide relationship targets
    and renames slide XML files so slide1.xml, slide2.xml, ... follow the final order.
    """
    slides_dir = template_dir / "ppt" / "slides"
    rels_dir = slides_dir / "_rels"
    prp = template_dir / "ppt" / "_rels" / "presentation.xml.rels"

    if not slides_dir.exists() or not prp.exists():
        print("WARNING: physical slide order skipped; slides or presentation rels not found")
        return

    pr_text = prp.read_text(encoding="utf-8")

    rid_to_old_slide = {}
    for m in SLIDE_REL_RE.finditer(pr_text):
        rid_to_old_slide[m.group(1)] = int(m.group(2))

    ordered_old_nums = []
    ordered_rids = []
    for _sid, rid in sld_entries:
        if rid not in rid_to_old_slide:
            print(f"WARNING: physical order skipped; {rid} has no slide target")
            return
        ordered_rids.append(rid)
        ordered_old_nums.append(rid_to_old_slide[rid])

    if len(set(ordered_old_nums)) != len(ordered_old_nums):
        print("WARNING: physical order skipped; duplicate slide references found")
        return

    old_to_new = {old_num: new_num for new_num, old_num in enumerate(ordered_old_nums, start=1)}
    rid_to_new = {rid: old_to_new[old_num] for rid, old_num in zip(ordered_rids, ordered_old_nums)}

    # Move selected slides to temporary names first to avoid collisions like slide5 -> slide2.
    tmp_slide_paths = {}
    tmp_rels_paths = {}
    for old_num in ordered_old_nums:
        old_slide = slides_dir / f"slide{old_num}.xml"
        if not old_slide.exists():
            print(f"WARNING: physical order skipped; {old_slide.name} not found")
            return
        tmp_slide = slides_dir / f"__physical_order_tmp_{old_num}.xml"
        if tmp_slide.exists():
            tmp_slide.unlink()
        old_slide.rename(tmp_slide)
        tmp_slide_paths[old_num] = tmp_slide

        old_rels = rels_dir / f"slide{old_num}.xml.rels"
        if old_rels.exists():
            tmp_rels = rels_dir / f"__physical_order_tmp_{old_num}.xml.rels"
            if tmp_rels.exists():
                tmp_rels.unlink()
            old_rels.rename(tmp_rels)
            tmp_rels_paths[old_num] = tmp_rels

    # Remove files that would collide with the final sequential names.
    for new_num in range(1, len(ordered_old_nums) + 1):
        target_slide = slides_dir / f"slide{new_num}.xml"
        if target_slide.exists():
            target_slide.unlink()
        target_rels = rels_dir / f"slide{new_num}.xml.rels"
        if target_rels.exists():
            target_rels.unlink()

    # Rename the temp files to their final sequential names.
    for old_num, new_num in old_to_new.items():
        tmp_slide_paths[old_num].rename(slides_dir / f"slide{new_num}.xml")
        if old_num in tmp_rels_paths:
            tmp_rels_paths[old_num].rename(rels_dir / f"slide{new_num}.xml.rels")

    # Update presentation.xml.rels by rId, preserving all other relationships.
    def repl_rel(match):
        rel_xml = match.group(0)
        rid_match = re.search(r'Id="(rId\d+)"', rel_xml)
        if not rid_match:
            return rel_xml
        rid = rid_match.group(1)
        if rid not in rid_to_new:
            return rel_xml
        return re.sub(r'Target="slides/slide\d+\.xml"',
                      f'Target="slides/slide{rid_to_new[rid]}.xml"', rel_xml)

    pr_text = re.sub(r'<Relationship[^>]*Target="slides/slide\d+\.xml"[^>]*/>', repl_rel, pr_text)
    prp.write_text(pr_text, encoding="utf-8")

    _update_slide_overrides_in_content_types(template_dir, len(ordered_old_nums))

    print("Applied physical slide filename order:")
    for old_num, new_num in old_to_new.items():
        print(f"  slide{old_num}.xml -> slide{new_num}.xml")


def overscan_structure_master_backgrounds(template_dir, protected_master_name=None, protected_layout_names=None):
    """Adjust structure-page template pictures to match the user's corrected sample.

    This does NOT change content generation, slide insertion, layout mapping, or
    the reference template file. It only edits full-bleed template pictures in
    the unpacked final PPT before packing.

    The corrected sample shows that the structure-page artwork itself needs
    slightly different picture transforms:
      - image1.jpeg is used by cover/end pages.
      - image3.jpeg is used by chapter divider / contents pages.

    The values below are extracted from the user's manually corrected PPT and
    rounded to stable EMU values.
    """
    protected_layout_names = set(protected_layout_names or [])

    # Full slide: 9144000 x 5143500 EMU.
    # These values intentionally match the manually corrected visual target.
    # Cover/end background artwork (image1.jpeg).
    COVER_END_X = 0
    COVER_END_Y = 53975
    COVER_END_CX = 9521200
    COVER_END_CY = 5143500

    # Directory/chapter-divider background artwork (image3.jpeg).
    DIVIDER_X = 0
    DIVIDER_Y = -635
    DIVIDER_CX = 9532000
    DIVIDER_CY = 5349900

    full_xfrm_re = re.compile(
        r'<a:xfrm>\s*<a:off\s+x="-?\d+"\s+y="-?\d+"\s*/>\s*'
        r'<a:ext\s+cx="\d+"\s+cy="\d+"\s*/>\s*</a:xfrm>'
    )
    blip_re = re.compile(r'<a:blip[^>]*(?:r:embed|embed)="(rId\d+)"[^>]*/>')

    def _relationship_targets_for(xml_path):
        """Return rId -> target for the rels file belonging to an xml part."""
        # slide1.xml -> _rels/slide1.xml.rels; slideLayout1.xml -> _rels/...
        rels_path = xml_path.parent / "_rels" / f"{xml_path.name}.rels"
        mapping = {}
        if not rels_path.exists():
            return mapping
        rel_text = rels_path.read_text(encoding="utf-8")
        for m in re.finditer(r'<Relationship[^>]*Id="([^"]+)"[^>]*Target="([^"]+)"[^>]*/>', rel_text):
            mapping[m.group(1)] = m.group(2)
        return mapping

    def _target_transform(target):
        """Return the desired transform tuple for a related image target."""
        if not target:
            return None
        normalized = target.replace('\\', '/').lower()
        if normalized.endswith('/image1.jpeg') or normalized.endswith('image1.jpeg'):
            return (COVER_END_X, COVER_END_Y, COVER_END_CX, COVER_END_CY)
        if normalized.endswith('/image3.jpeg') or normalized.endswith('image3.jpeg'):
            return (DIVIDER_X, DIVIDER_Y, DIVIDER_CX, DIVIDER_CY)
        return None

    def _replace_pic_xfrm(pic_xml, rid_to_target):
        """Replace only full-page template picture xfrm blocks inside a p:pic."""
        blip = blip_re.search(pic_xml)
        if not blip:
            return pic_xml, 0
        target = rid_to_target.get(blip.group(1), '')
        transform = _target_transform(target)
        if not transform:
            return pic_xml, 0
        x, y, cx, cy = transform
        replacement = (
            f'<a:xfrm><a:off x="{x}" y="{y}"/>'
            f'<a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        )

        def repl_xfrm(m):
            block = m.group(0)
            # Only touch the full-bleed template artwork, not icons or small images.
            if 'cx="9144000"' in block and 'cy="5143500"' in block:
                return replacement
            # Also allow re-running after a previous shift/overscan attempt.
            has_near_full = re.search(r'cx="9[0-9]{6,7}"', block) and re.search(r'cy="5[0-9]{6,7}"', block)
            return replacement if has_near_full else block

        new_pic, count = full_xfrm_re.subn(repl_xfrm, pic_xml, count=1)
        return new_pic, count

    candidate_dirs = [
        template_dir / "ppt" / "slideMasters",
        template_dir / "ppt" / "slideLayouts",
        template_dir / "ppt" / "slides",
    ]

    changed = []
    pic_re = re.compile(r'<p:pic>.*?</p:pic>', re.S)
    for folder in candidate_dirs:
        if not folder.exists():
            continue
        for xml_path in sorted(folder.glob("*.xml")):
            # Never adjust the copied content-slide master/layout chain.
            # Those parts control the content pages; changing their full-bleed
            # image transforms would alter content-page size/position.
            if folder.name == "slideMasters" and xml_path.name == protected_master_name:
                continue
            if folder.name == "slideLayouts" and xml_path.name in protected_layout_names:
                continue

            xml = xml_path.read_text(encoding="utf-8")
            rid_to_target = _relationship_targets_for(xml_path)
            if not rid_to_target:
                # Some masters/layouts may not use picture relationships; still
                # keep the white canvas fallback below.
                new_xml = xml
                replaced = 0
            else:
                replaced = 0
                def repl_pic(m):
                    nonlocal replaced
                    new_pic, count = _replace_pic_xfrm(m.group(0), rid_to_target)
                    replaced += count
                    return new_pic
                new_xml = pic_re.sub(repl_pic, xml)

            # Keep a white fallback canvas so any tiny exposed edge is not blue.
            new_xml = new_xml.replace('srgbClr val="1F4E79"', 'srgbClr val="FFFFFF"')
            new_xml = new_xml.replace('srgbClr val="1f4e79"', 'srgbClr val="FFFFFF"')

            if new_xml != xml:
                xml_path.write_text(new_xml, encoding="utf-8")
                changed.append(f"{folder.name}/{xml_path.name} adjusted_pics={replaced}")

    if changed:
        print("Applied structure/template background manual-fit adjustment:")
        for item in changed:
            print(f"  {item}")

# ============================================================
#  Master chain discovery & copy
# ============================================================

def discover_master_chain(content_dir):
    """Discover full PptxGenJS master chain from content slides.

    Returns dict: {
        'slidelayout': 'slideLayout2.xml',
        'slidemaster': 'slideMaster1.xml',
        'theme': 'theme1.xml',
        'extra_layouts': ['slideLayout1.xml'],   # layouts ref'd by master
    }
    """
    # Step 1: find which slideLayout content slides reference
    slides_rels_dir = content_dir / "ppt" / "slides" / "_rels"
    layout_name = None
    for rels_file in sorted(slides_rels_dir.glob("slide*.xml.rels")):
        text = rels_file.read_text(encoding="utf-8")
        m = re.search(r'Target="\.\./slideLayouts/(slideLayout\d+\.xml)"', text)
        if m:
            layout_name = m.group(1)
            break

    if not layout_name:
        return None

    # Step 2: find which slideMaster the slideLayout references
    layout_rels = content_dir / "ppt" / "slideLayouts" / "_rels" / f"{layout_name}.rels"
    master_name = None
    if layout_rels.exists():
        text = layout_rels.read_text(encoding="utf-8")
        m = re.search(r'Target="\.\./slideMasters/(slideMaster\d+\.xml)"', text)
        if m:
            master_name = m.group(1)

    if not master_name:
        return None

    # Step 3: find theme + extra layouts from slideMaster rels
    master_rels = content_dir / "ppt" / "slideMasters" / "_rels" / f"{master_name}.rels"
    theme_name = None
    extra_layouts = []
    if master_rels.exists():
        text = master_rels.read_text(encoding="utf-8")
        tm = re.search(r'Target="\.\./theme/(theme\d+\.xml)"', text)
        if tm:
            theme_name = tm.group(1)
        for m in re.finditer(r'Target="\.\./slideLayouts/(slideLayout\d+\.xml)"', text):
            extra = m.group(1)
            if extra != layout_name:
                extra_layouts.append(extra)

    return {
        "slidelayout": layout_name,
        "slidemaster": master_name,
        "theme": theme_name,
        "extra_layouts": extra_layouts,
    }


def copy_master_system(content_dir, template_dir, chain):
    """Copy the complete master system into template directory.

    Renames to avoid conflicts with template's existing masters.
    Updates all internal rels to cross-reference correctly.

    Returns dict: {new_slidemaster, new_slidelayout, new_theme, new_extra_layouts}
    """
    result = {}

    # Determine template's existing max master/layout numbers to avoid conflict
    existing_masters = [int(m.group(1)) for m in
        re.finditer(r'slideMaster(\d+)\.xml',
                    "\n".join(str(p) for p in (template_dir / "ppt" / "slideMasters").glob("*.xml") if (template_dir / "ppt" / "slideMasters").exists()))
    ] if (template_dir / "ppt" / "slideMasters").exists() else []
    existing_layouts = [int(m.group(1)) for m in
        re.finditer(r'slideLayout(\d+)\.xml',
                    "\n".join(str(p) for p in (template_dir / "ppt" / "slideLayouts").glob("*.xml") if (template_dir / "ppt" / "slideLayouts").exists()))
    ] if (template_dir / "ppt" / "slideLayouts").exists() else []
    existing_themes = [int(m.group(1)) for m in
        re.finditer(r'theme(\d+)\.xml',
                    "\n".join(str(p) for p in (template_dir / "ppt" / "theme").glob("*.xml") if (template_dir / "ppt" / "theme").exists()))
    ] if (template_dir / "ppt" / "theme").exists() else []

    new_master_num = max(existing_masters or [0]) + 1
    new_layout_num = max(existing_layouts or [0]) + 1
    new_theme_num = max(existing_themes or [0]) + 1

    new_master = f"slideMaster{new_master_num}.xml"
    new_layout = f"slideLayout{new_layout_num}.xml"
    new_theme = f"theme{new_theme_num}.xml"

    extra_map = {}
    for extra in chain["extra_layouts"]:
        new_layout_num = new_layout_num + 1
        extra_map[extra] = f"slideLayout{new_layout_num}.xml"

    # --- Copy theme ---
    src_theme = content_dir / "ppt" / "theme" / chain["theme"]
    dst_theme = template_dir / "ppt" / "theme" / new_theme
    dst_theme.parent.mkdir(parents=True, exist_ok=True)
    if not dst_theme.exists():
        shutil.copy2(str(src_theme), str(dst_theme))
        print(f"  Copied theme: {chain['theme']} -> {new_theme}")

    # --- Copy slideMaster ---
    src_master = content_dir / "ppt" / "slideMasters" / chain["slidemaster"]
    dst_master = template_dir / "ppt" / "slideMasters" / new_master
    dst_master.parent.mkdir(parents=True, exist_ok=True)
    master_xml = src_master.read_text(encoding="utf-8")
    dst_master.write_text(master_xml, encoding="utf-8")

    # Copy slideMaster rels, remap references
    src_master_rels = content_dir / "ppt" / "slideMasters" / "_rels" / f"{chain['slidemaster']}.rels"
    dst_master_rels = template_dir / "ppt" / "slideMasters" / "_rels" / f"{new_master}.rels"
    dst_master_rels.parent.mkdir(parents=True, exist_ok=True)

    if src_master_rels.exists():
        rels_text = src_master_rels.read_text(encoding="utf-8")
        for orig, new in extra_map.items():
            rels_text = rels_text.replace(
                f'Target="../slideLayouts/{orig}"',
                f'Target="../slideLayouts/{new}"')
        rels_text = rels_text.replace(
            f'Target="../slideLayouts/{chain["slidelayout"]}"',
            f'Target="../slideLayouts/{new_layout}"')
        rels_text = rels_text.replace(
            f'Target="../theme/{chain["theme"]}"',
            f'Target="../theme/{new_theme}"')
        dst_master_rels.write_text(rels_text, encoding="utf-8")

    print(f"  Copied slideMaster: {chain['slidemaster']} -> {new_master}")

    # --- Copy slideLayout (the one content pages use) ---
    src_layout = content_dir / "ppt" / "slideLayouts" / chain["slidelayout"]
    dst_layout = template_dir / "ppt" / "slideLayouts" / new_layout
    dst_layout.parent.mkdir(parents=True, exist_ok=True)
    layout_xml = src_layout.read_text(encoding="utf-8")
    dst_layout.write_text(layout_xml, encoding="utf-8")

    src_layout_rels = content_dir / "ppt" / "slideLayouts" / "_rels" / f"{chain['slidelayout']}.rels"
    dst_layout_rels = template_dir / "ppt" / "slideLayouts" / "_rels" / f"{new_layout}.rels"
    dst_layout_rels.parent.mkdir(parents=True, exist_ok=True)
    if src_layout_rels.exists():
        rels_text = src_layout_rels.read_text(encoding="utf-8")
        rels_text = rels_text.replace(
            f'Target="../slideMasters/{chain["slidemaster"]}"',
            f'Target="../slideMasters/{new_master}"')
        dst_layout_rels.write_text(rels_text, encoding="utf-8")

    print(f"  Copied slideLayout: {chain['slidelayout']} -> {new_layout}")

    # --- Copy extra slideLayouts (referenced by slideMaster) ---
    for orig, new in extra_map.items():
        src_extra = content_dir / "ppt" / "slideLayouts" / orig
        dst_extra = template_dir / "ppt" / "slideLayouts" / new
        if src_extra.exists():
            shutil.copy2(str(src_extra), str(dst_extra))
            src_extra_rels = content_dir / "ppt" / "slideLayouts" / "_rels" / f"{orig}.rels"
            dst_extra_rels = template_dir / "ppt" / "slideLayouts" / "_rels" / f"{new}.rels"
            if src_extra_rels.exists():
                rels_text = src_extra_rels.read_text(encoding="utf-8")
                rels_text = rels_text.replace(
                    f'Target="../slideMasters/{chain["slidemaster"]}"',
                    f'Target="../slideMasters/{new_master}"')
                dst_extra_rels.write_text(rels_text, encoding="utf-8")
            print(f"  Copied extra layout: {orig} -> {new}")

    result["slidemaster"] = new_master
    result["slidelayout"] = new_layout
    result["theme"] = new_theme
    result["extra_layouts"] = extra_map

    return result


def inject_master_bg_and_bar(template_dir, new_master_name):
    """Inject background image + red bar into the copied slideMaster.

    Background references image3.jpeg (copied from template).
    Red bar is a shape added to slideMaster's spTree.
    """
    master_path = template_dir / "ppt" / "slideMasters" / new_master_name
    master_rels_path = template_dir / "ppt" / "slideMasters" / "_rels" / f"{new_master_name}.rels"

    xml = master_path.read_text(encoding="utf-8")
    rels_text = master_rels_path.read_text(encoding="utf-8") if master_rels_path.exists() else (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '</Relationships>'
    )

    # Get next available rId
    existing_rids = [int(m) for m in re.findall(r'rId(\d+)', rels_text)]
    next_rid = max(existing_rids or [0]) + 1
    bg_rid = f"rId{next_rid}"

    # Add background image rel
    bg_rel = (
        f'  <Relationship Id="{bg_rid}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
        'Target="../media/image3.jpeg"/>'
    )
    closing = '</Relationships>'
    idx = rels_text.rfind(closing)
    if idx >= 0:
        rels_text = rels_text[:idx] + bg_rel + '\n' + rels_text[idx:]
    else:
        rels_text += '\n' + bg_rel
    master_rels_path.write_text(rels_text, encoding="utf-8")

    # Inject <p:bg> into slideMaster's cSld (before spTree)
    bg_xml = f'''<p:bg>
      <p:bgPr>
        <a:blipFill dpi="0" rotWithShape="1">
          <a:blip r:embed="{bg_rid}">
            <a:lum/>
          </a:blip>
          <a:srcRect/>
          <a:stretch>
            <a:fillRect/>
          </a:stretch>
        </a:blipFill>
        <a:effectLst/>
      </p:bgPr>
    </p:bg>
    '''

    if '<p:bg>' not in xml:
        xml = re.sub(
            r'(<p:cSld[^>]*>)\s*(<p:spTree>)',
            rf'\1\n    {bg_xml}\2',
            xml, count=1
        )

    # Get max shape id from slideMaster's spTree
    max_id = 0
    for m in re.finditer(r'id="(\d+)"', xml):
        max_id = max(max_id, int(m.group(1)))
    bar_id = max_id + 100  # offset to avoid conflicts

    # Inject red bar into slideMaster's spTree
    red_bar_xml = f'''<p:sp>
        <p:nvSpPr>
          <p:cNvPr id="{bar_id}" name="RedBar"/>
          <p:cNvSpPr/>
          <p:nvPr/>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm>
            <a:off x="0" y="0"/>
            <a:ext cx="9144000" cy="54864"/>
          </a:xfrm>
          <a:prstGeom prst="rect">
            <a:avLst/>
          </a:prstGeom>
          <a:solidFill>
            <a:srgbClr val="C00000"/>
          </a:solidFill>
          <a:ln>
            <a:noFill/>
          </a:ln>
        </p:spPr>
        <p:txBody>
          <a:bodyPr/>
          <a:lstStyle/>
          <a:p>
            <a:endParaRPr lang="zh-CN"/>
          </a:p>
        </p:txBody>
      </p:sp>'''

    if 'name="RedBar"' not in xml:
        xml = xml.replace('</p:grpSpPr>', '</p:grpSpPr>\n      ' + red_bar_xml, 1)

    master_path.write_text(xml, encoding="utf-8")

    return bg_rid


# ============================================================
#  Content-Type helpers
# ============================================================

def add_to_content_types(template_dir, entries):
    """Add Override entries to [Content_Types].xml.

    entries: list of part strings like "/ppt/slideMasters/slideMaster99.xml"
    """
    ctp = template_dir / "[Content_Types].xml"
    ct = ctp.read_text(encoding="utf-8")
    for part in entries:
        xml_path = template_dir / part.lstrip("/")
        if not xml_path.exists():
            continue
        if "slideMaster" in part:
            content_type = "application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"
        elif "slideLayout" in part:
            content_type = "application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"
        elif "theme" in part:
            content_type = "application/vnd.openxmlformats-officedocument.theme+xml"
        else:
            content_type = "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"

        ov_line = f'  <Override PartName="{part}" ContentType="{content_type}"/>'
        if ov_line not in ct:
            ct = ct.replace('</Types>', ov_line + '\n</Types>')
    ctp.write_text(ct, encoding="utf-8")


def register_master_in_presentation(template_dir, new_names):
    """Register the new slideMaster + slideLayouts + theme in presentation.xml.

    Without this, PowerPoint doesn't recognize the new master chain and
    reassigns content slides to existing template masters, overwriting layouts.

    This adds:
    1. Relationships in presentation.xml.rels for slideMaster and theme
    2. Entry in <p:sldMasterIdLst> in presentation.xml
    3. SlideLayout entries under the new slideMaster
    """
    prp = template_dir / "ppt" / "_rels" / "presentation.xml.rels"
    pr_text = prp.read_text(encoding="utf-8")

    # --- Add relationships for new slideMaster and theme ---
    existing_rids = [int(m) for m in re.findall(r'Id="rId(\d+)"', pr_text)]
    next_rid = max(existing_rids or [0]) + 1

    master_rid = f"rId{next_rid}"
    next_rid += 1
    theme_rid = f"rId{next_rid}"
    next_rid += 1

    new_rels = (
        f'  <Relationship Id="{master_rid}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" '
        f'Target="slideMasters/{new_names["slidemaster"]}"/>\n'
        f'  <Relationship Id="{theme_rid}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" '
        f'Target="theme/{new_names["theme"]}"/>\n'
    )

    closing = '</Relationships>'
    idx = pr_text.rfind(closing)
    if idx >= 0:
        pr_text = pr_text[:idx] + new_rels + pr_text[idx:]
    prp.write_text(pr_text, encoding="utf-8")
    print(f"  Added rels: {master_rid} -> {new_names['slidemaster']}, {theme_rid} -> {new_names['theme']}")

    # --- Add <p:sldMasterId> entry in presentation.xml ---
    pp = template_dir / "ppt" / "presentation.xml"
    pc = pp.read_text(encoding="utf-8")

    # Find next available sldMasterId
    existing_master_ids = [int(m) for m in re.findall(r'<p:sldMasterId[^>]*id="(\d+)"', pc)]
    next_master_id = max(existing_master_ids or [0]) + 1

    # Build layout entries for this master
    # Extract layout number from filename
    layout_num = re.search(r'slideLayout(\d+)', new_names["slidelayout"]).group(1)

    layout_entries = f'        <p:sldLayoutId id="{int(layout_num) + 2147483648}" r:id="{master_rid}"/>\n'

    # Also register extra layouts
    for extra_name in new_names.get("extra_layouts", {}).values():
        extra_num = re.search(r'slideLayout(\d+)', extra_name).group(1)
        layout_entries += f'        <p:sldLayoutId id="{int(extra_num) + 2147483648}" r:id="{master_rid}"/>\n'

    master_entry = (
        f'    <p:sldMasterId id="{next_master_id}" r:id="{master_rid}">\n'
        f'      <p:cSld masterId="0"/>\n'
        f'      <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" '
        f'accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" '
        f'hlink="hlink" folHlink="folHlink"/>\n'
        f'      <p:sldLayoutIdLst>\n'
        f'{layout_entries}'
        f'      </p:sldLayoutIdLst>\n'
        f'    </p:sldMasterId>'
    )

    # Insert before </p:sldMasterIdLst>
    close_tag = '</p:sldMasterIdLst>'
    idx = pc.find(close_tag)
    if idx >= 0:
        pc = pc[:idx] + master_entry + '\n  ' + pc[idx:]
    else:
        print("  WARNING: Could not find <p:sldMasterIdLst> in presentation.xml")

    pp.write_text(pc, encoding="utf-8")
    print(f"  Registered slideMaster in presentation.xml: id={next_master_id}, rId={master_rid}")

    return master_rid, theme_rid


# ============================================================
#  Content slide rels helper
# ============================================================

def update_content_rels(original_rels_xml, new_layout_name):
    """Update content slide rels: remap slideLayout target, drop notesSlide."""
    # Remap slideLayout reference
    result = re.sub(
        r'Target="\.\./slideLayouts/slideLayout\d+\.xml"',
        f'Target="../slideLayouts/{new_layout_name}"',
        original_rels_xml
    )
    # Drop notesSlide relationship entirely
    result = re.sub(
        r'\s*<Relationship[^>]*Type="[^"]*notesSlide"[^>]*/>\s*',
        '',
        result
    )
    # Clean up any blank lines left behind
    result = re.sub(r'\n\s*\n', '\n', result)
    return result


# ============================================================
#  Main
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("Usage: python merge_content.py config.json")
        sys.exit(1)

    config_path = sys.argv[1]
    with open(config_path, 'r', encoding='utf-8-sig') as f:
        config = json.load(f)

    template_dir = Path(config["template_dir"])
    content_pptx = config["content_pptx"]
    output_pptx = config.get("output", "output.pptx")
    layout = config["layout"]

    if not layout:
        print("ERROR: layout array is required")
        sys.exit(1)

    num_chapters = len(layout)
    total_content = sum(item["content_pages"] for item in layout)
    divider_start = 5
    content_start = 5 + num_chapters

    print(f"=== Merging content pages ===")
    print(f"Chapters: {num_chapters}, Content pages: {total_content}")
    print(f"Divider range:  slide{divider_start}-slide{divider_start + num_chapters - 1}")
    print(f"Content range:   slide{content_start}-slide{content_start + total_content - 1}")
    print()

    # --- Step 0: Unpack content PPTX ---
    tmp_dir = Path(tempfile.mkdtemp(prefix="pptx_merge_"))
    content_dir = tmp_dir / "content"
    with zipfile.ZipFile(str(content_pptx), 'r') as z:
        z.extractall(str(content_dir))
    print(f"Unpacked content: {content_pptx}")

    # --- Step 0.5: Discover & copy complete master chain ---
    print("Discovering master chain...")
    chain = discover_master_chain(content_dir)
    if not chain:
        print("ERROR: Could not discover master chain from content PPTX")
        sys.exit(1)
    print(f"  slideLayout: {chain['slidelayout']}")
    print(f"  slideMaster: {chain['slidemaster']}")
    print(f"  theme:       {chain['theme']}")
    if chain['extra_layouts']:
        print(f"  extra:       {chain['extra_layouts']}")

    print("Copying master system...")
    new_names = copy_master_system(content_dir, template_dir, chain)

    # Inject background + red bar into the copied slideMaster
    inject_master_bg_and_bar(template_dir, new_names["slidemaster"])
    print(f"  Injected background + red bar into {new_names['slidemaster']}")

    # Register new master files in Content_Types
    ct_entries = []
    ct_entries.append(f"/ppt/slideMasters/{new_names['slidemaster']}")
    ct_entries.append(f"/ppt/slideLayouts/{new_names['slidelayout']}")
    ct_entries.append(f"/ppt/theme/{new_names['theme']}")
    for extra in new_names["extra_layouts"].values():
        ct_entries.append(f"/ppt/slideLayouts/{extra}")
    add_to_content_types(template_dir, ct_entries)

    # Register new master in presentation.xml (CRITICAL for layout preservation)
    print("Registering master in presentation.xml...")
    register_master_in_presentation(template_dir, new_names)

    slides_dir = template_dir / "ppt" / "slides"
    rels_dir = slides_dir / "_rels"
    media_dir = template_dir / "ppt" / "media"

    # --- Step 1: Copy content slides — XML VERBATIM, NO MODIFICATION ---
    slide_mapping = {}
    for i in range(1, total_content + 1):
        src_slide = content_dir / "ppt" / "slides" / f"slide{i}.xml"
        if not src_slide.exists():
            print(f"ERROR: content slide{i}.xml not found")
            sys.exit(1)

        dst_num = content_start + i - 1
        dst_slide = slides_dir / f"slide{dst_num}.xml"

        # Copy XML verbatim — ZERO modifications
        shutil.copy2(str(src_slide), str(dst_slide))

        # Update rels: remap slideLayout, drop notesSlide
        src_rels = content_dir / "ppt" / "slides" / "_rels" / f"slide{i}.xml.rels"
        if src_rels.exists():
            original_rels = src_rels.read_text(encoding="utf-8")
        else:
            original_rels = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
                '</Relationships>'
            )
        new_rels = update_content_rels(original_rels, new_names["slidelayout"])
        dst_rels = rels_dir / f"slide{dst_num}.xml.rels"
        dst_rels.write_text(new_rels, encoding="utf-8")

        slide_mapping[dst_num] = i

    print(f"Copied {total_content} content slides "
          f"-> slide{content_start}-slide{content_start + total_content - 1} "
          f"(XML untouched, rels remapped to {new_names['slidelayout']})")

    # --- Step 2: Copy media files ---
    content_media = content_dir / "ppt" / "media"
    if content_media.exists():
        for f in content_media.iterdir():
            dst = media_dir / f.name
            if not dst.exists():
                shutil.copy2(str(f), str(dst))

    # --- Step 3: Add content slide rIds to presentation.xml.rels ---
    prp = template_dir / "ppt" / "_rels" / "presentation.xml.rels"
    pr_text = prp.read_text(encoding="utf-8")

    existing_rids = [int(m) for m in re.findall(r'Id="rId(\d+)"', pr_text)]
    next_rid = max(existing_rids or [0]) + 1

    content_rids = {}
    new_rels_block = ""
    for dst_num in sorted(slide_mapping.keys()):
        rid = f"rId{next_rid}"
        new_rels_block += (
            f'  <Relationship Id="{rid}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            f'Target="slides/slide{dst_num}.xml"/>\n'
        )
        content_rids[dst_num] = rid
        next_rid += 1

    closing = '</Relationships>'
    idx = pr_text.rfind(closing)
    if idx >= 0:
        pr_text = pr_text[:idx] + new_rels_block + pr_text[idx:]
    else:
        pr_text += '\n' + new_rels_block
    prp.write_text(pr_text, encoding="utf-8")
    print(f"Added rIds for {total_content} content slides")

    # --- Step 4: Add content slides to [Content_Types].xml ---
    ov_entries = [
        f"/ppt/slides/slide{dst_num}.xml" for dst_num in sorted(slide_mapping.keys())
    ]
    add_to_content_types(template_dir, ov_entries)

    # --- Step 5: Build slide order ---
    pr_text = prp.read_text(encoding="utf-8")

    # Discover all existing slide rId mappings
    all_slide_rids = {}
    for m in SLIDE_REL_RE.finditer(pr_text):
        all_slide_rids[int(m.group(2))] = m.group(1)

    cover_rid = all_slide_rids.get(1)
    end_rid = all_slide_rids.get(4)
    if not cover_rid:
        print("ERROR: Could not find cover slide (slide1) rId")
        sys.exit(1)
    if not end_rid:
        print("ERROR: Could not find end slide (slide4) rId")
        sys.exit(1)

    divider_rids = {}
    for sn in range(divider_start, content_start):
        if sn in all_slide_rids:
            divider_rids[sn] = all_slide_rids[sn]

    sld_entries = []
    sld_id = 256

    # Cover
    sld_entries.append((sld_id, cover_rid))
    sld_id += 1

    # Interleave: divider -> content x N -> divider -> ...
    content_cursor = 1
    for chapter_info in layout:
        ch = chapter_info["chapter"]
        num_pages = chapter_info["content_pages"]

        divider_num = divider_start + ch - 1
        if divider_num in divider_rids:
            sld_entries.append((sld_id, divider_rids[divider_num]))
            sld_id += 1

        for _ in range(num_pages):
            if content_cursor <= total_content:
                dst_num = content_start + content_cursor - 1
                if dst_num in content_rids:
                    sld_entries.append((sld_id, content_rids[dst_num]))
                    sld_id += 1
                content_cursor += 1

    # End
    sld_entries.append((sld_id, end_rid))

    # Write presentation.xml
    pp = template_dir / "ppt" / "presentation.xml"
    pc = pp.read_text(encoding="utf-8")
    entries_xml = "\n".join(
        f'    <p:sldId id="{sid}" r:id="{rid}"/>' for sid, rid in sld_entries
    )
    ns_xml = f"<p:sldIdLst>\n{entries_xml}\n  </p:sldIdLst>"

    sld_master_end = pc.find('</p:sldMasterIdLst>')
    if sld_master_end >= 0:
        sld_lst_start = pc.find('<p:sldIdLst>', sld_master_end)
    else:
        sld_lst_start = pc.find('<p:sldIdLst>')

    sld_lst_end = pc.find('</p:sldIdLst>', sld_lst_start) if sld_lst_start >= 0 else -1

    if sld_lst_start >= 0 and sld_lst_end >= 0:
        sld_lst_end_full = sld_lst_end + len('</p:sldIdLst>')
        pc = pc[:sld_lst_start] + ns_xml + pc[sld_lst_end_full:]
        pp.write_text(pc, encoding="utf-8")
        print("Updated presentation.xml slide order")
    else:
        print("ERROR: Could not locate <p:sldIdLst> in presentation.xml")
        sys.exit(1)

    # Print order summary
    print(f"\nSlide order ({len(sld_entries)} slides):")
    c_idx = 1
    for sid, rid in sld_entries:
        label = "?"
        for sn, r in all_slide_rids.items():
            if r == rid:
                if sn == 1:
                    label = "cover"
                elif sn == 4:
                    label = "end"
                elif divider_start <= sn < content_start:
                    label = f"ch{sn - divider_start + 1} divider"
                else:
                    label = f"content #{c_idx}"
                    c_idx += 1
                break
        if label == "?":
            for dst_num, r in content_rids.items():
                if r == rid:
                    label = f"content #{c_idx}"
                    c_idx += 1
                    break
        print(f"  {rid} -> {label}")

    # --- Step 5.5: Final compatibility fixes ---
    # Keep true PPT playback order and physical slide file order consistent for
    # older previewers, then slightly overscan structure-page backgrounds to avoid
    # right/bottom blue-edge artifacts in some renderers.
    enforce_physical_slide_order(template_dir, sld_entries)
    protected_layouts = set(new_names.get("extra_layouts", {}).values())
    protected_layouts.add(new_names["slidelayout"])
    overscan_structure_master_backgrounds(
        template_dir,
        protected_master_name=new_names["slidemaster"],
        protected_layout_names=protected_layouts,
    )

    # --- Step 6: Clean and pack ---
    clean_script = str(SCRIPTS_DIR / "clean.py")
    pack_script = str(SCRIPTS_DIR / "office" / "pack.py")

    print(f"\nCleaning orphaned files...")
    result = subprocess.run(
        [sys.executable, clean_script, str(template_dir)],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode != 0 and result.stderr:
        print(f"Clean warning: {result.stderr.strip()}")

    print(f"\nPacking {output_pptx}...")
    result = subprocess.run(
        [sys.executable, pack_script, str(template_dir), str(output_pptx),
         "--validate", "false"],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode != 0:
        if result.stderr:
            print(f"Pack error: {result.stderr.strip()}")
    else:
        size_kb = Path(output_pptx).stat().st_size / 1024
        print(f"Packed {output_pptx} ({size_kb:.0f} KB)")

    shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f"\n=== Merge complete! ===")
    print(f"Output: {output_pptx}")
    print(f"\nMaster chain: {new_names['slidemaster']}"
          f" -> {new_names['slidelayout']} -> {new_names['theme']}")
    print(f"Content pages: XML untouched, background + red bar from slideMaster")


if __name__ == "__main__":
    main()