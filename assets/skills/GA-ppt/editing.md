# Editing Presentations - Template & Merge

This guide covers the **template structure** and **merge** portions of the hybrid workflow.
For content generation, read [pptxgenjs.md](pptxgenjs.md).

---

## Template File

``
skills/pptx/templates/reference.pptx
``

4-page template:
- slide1: Cover (red background + logo)
- slide2: Section divider (chapter list with 5 slots: 一二三四五)
- slide3: Content page template — **NOT used directly**
- slide4: End page (decorative image)

---

## Step 1: Build Structure

**Use `scripts/build_structure.py`. Do NOT manually edit XML.**

### Config

``json
{
  "reference": "templates/reference.pptx",
  "output": "unpacked",
  "cover": { "title": "Your Presentation Title" },
  "chapters": ["Chapter One", "Chapter Two", "Chapter Three"]
}
``

### Run

``bash
python scripts/build_structure.py config.json
``

### What it does

1. Unpacks reference.pptx
2. Replaces cover title text
3. Creates one divider per chapter (slide5, slide6, ...) with:
   - Current chapter: red number (C00000) + red title bar (C00000) + white text
   - Other chapters: black number + gray bar (CECECE) + black text
   - Unused chapters removed (template has 5 slots, use 1-5)
   - Chapter titles filled into title bar shapes
4. Sets up rId16+ for dividers, content types, slide order

---

## Step 2: Generate Content Pages

Read [pptxgenjs.md](pptxgenjs.md) for detailed layouts.

---

## Step 3: Merge and Pack

**Use `scripts/merge_content.py`. Do NOT manually edit XML/rels.**

### Config

``json
{
  "template_dir": "unpacked",
  "content_pptx": "content_slides.pptx",
  "output": "output.pptx",
  "reference": "templates/reference.pptx",
  "layout": [
    {"chapter": 1, "content_pages": 3},
    {"chapter": 2, "content_pages": 2},
    {"chapter": 3, "content_pages": 3}
  ]
}
``

### Run

``bash
python scripts/merge_content.py merge_config.json
``

### What it does

1. Unpacks content_slides.pptx
2. Copies each content slide into the template (slide7, slide8, ...)
3. Injects `<p:bg>` with image3.jpeg background into each content slide
4. Injects red top bar shape (C00000) into each content slide
5. Creates clean .rels for each content slide:
   - rId1 → slideLayout1 (template's layout)
   - rId2 → image3.jpeg (background)
   - No notesSlide references (avoids sharing conflicts)
6. Assigns rIds for content slides (continues from highest existing rId)
7. Updates [Content_Types].xml
8. Builds interleaved slide order:
   ``
   cover → ch1_divider → content × N → ch2_divider → content × N → ... → end
   ``
9. Runs clean.py to remove orphaned template files (slide2, slide3, etc.)
10. Packs final PPTX with `--validate false`

---

## rId Management

| Range | Purpose |
|-------|---------|
| rId1-rId15 | Template internals (slideMasters, theme, etc.) |
| rId16-rId(15+N) | Divider slides (from build_structure.py) |
| rId(16+N)+ | Content slides (from merge_content.py) |

Both scripts handle rId assignment automatically. No manual rId management needed.

---

## Common Pitfalls

- **Do NOT manually edit divider XML** — use build_structure.py
- **Do NOT manually edit rels/content types** — use merge_content.py
- **Background image** — merge_content.py injects it directly into each slide XML (not via Slide Master)
- **notesSlide** — merge_content.py strips all notes references to avoid sharing conflicts
- **Validation** — use `--validate false` (pre-existing GBK warnings are harmless)