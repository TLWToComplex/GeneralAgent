---
name: pptx
description: "Use this skill any time a .pptx file is involved — creating, reading, editing, or combining presentations. Trigger on: deck, slides, presentation, .pptx filename."
license: Proprietary. LICENSE.txt has complete terms
---

# PPTX Skill

## Absolute Execution Order (Do Not Skip)

When creating a new presentation, follow this exact order every time. Do not jump directly to PptxGenJS. Do not create only `content_slides.pptx`. Do not pack the deck before `merge_content.py` runs.

0. **Source understanding** — if the user provided a PDF, Word document, image, or other source file, first use the platform-extracted content to build the deck outline.
1. **build_structure.py** — create the cover + chapter dividers + end page from the final outline.
2. **PptxGenJS** — create only the middle content slides as `content_slides.pptx`.
3. **merge_content.py** — merge content slides into the structure deck according to the chapter layout.
4. **Final output** — return only the merged `output.pptx` or the final renamed PPTX.

A valid run must produce and use these files in order:

```text
config.json
unpacked/
content_slides.pptx
merge_config.json
output.pptx
```

If any source file is available, the deck title, chapters, and slide content must come from that source. Generic sample content is forbidden.

---

## Hybrid Workflow (Mandatory)

1. **build_structure.py** — cover + dividers + end (pass JSON config)
2. **PptxGenJS** — content pages with rich layouts
3. **merge_content.py** — merge content into template, clean, pack

---

## Source File Input (PDF / Word / Images)

When the user uploads a PDF, Word document, image, or any source file and asks to create a presentation, use the platform-extracted file content as the primary source for the PPT.

Mandatory rules:
- First understand and summarize the uploaded file content before designing the deck.
- Use the file's title, section headings, key arguments, data, and images as the basis for the cover, chapters, and content slides.
- Do not invent an unrelated topic or generic content when a source file is available.
- Convert the source file into a clear presentation outline before Step 1.
- If the uploaded file has no clear chapters, create logical chapters from the file structure.
- If the uploaded file includes useful images or charts and the platform exposes them, incorporate them into content slides when appropriate.
- Keep the Hybrid Workflow unchanged: build structure first, generate content slides with PptxGenJS, then merge with merge_content.py.

### Required source-file planning step

Before running `build_structure.py`, derive this internal plan from the uploaded file content:

```json
{
  "title": "presentation title from the uploaded source",
  "chapters": [
    {"title": "chapter title from source", "content_pages": 1, "key_points": ["source-based point"]}
  ]
}
```

Then use the same `title` and `chapters` to write `config.json`, generate the content slides, and write `merge_config.json`. The `layout` in `merge_config.json` must match the number of content pages created for each chapter.

If the platform-extracted file content is long, summarize it into a PPT-friendly outline. If it is short, keep the chapters fewer and more focused. Never ignore the file and generate a generic deck.

## Quick Reference

| Task | How |
|------|-----|
| Create presentation | This file for overview, then [editing.md](editing.md) + [pptxgenjs.md](pptxgenjs.md) |
| Read/analyze | `python -m markitdown presentation.pptx` |
| Visual overview | `python scripts/thumbnail.py presentation.pptx` |

---

## Step 1: Build Structure

Write a JSON config and run the script. **Do NOT manually edit XML.**

``json
{
  "reference": "templates/reference.pptx",
  "output": "unpacked",
  "cover": { "title": "Your Title" },
  "chapters": ["Chapter 1", "Chapter 2", "Chapter 3"]
}
``

``bash
python scripts/build_structure.py config.json
``

Output: unpacked/ with slide1 (cover) + slide5+ (dividers) + slide4 (end).

## Step 2: Generate Content (PptxGenJS)

Read [pptxgenjs.md](pptxgenjs.md) for layouts, safe zones, and patterns.

Key rules:
- **Do NOT define background or red bar in Slide Master** — `merge_content.py` injects these automatically
- Safe zones: title y=0.30"-1.39", content y=1.50"-5.07"
- Font: `Microsoft YaHei`, brand color: `C00000`
- Content pages should only define the middle-section content; layout/slideLayout from PptxGenJS is preserved
- **Every content slide must include at least one visual element** — icons in colored circles, shapes, charts, or images. Plain title + bullets is not acceptable
- **Vary layouts across slides** — alternate between icon rows, two-column cards, stat callouts, charts, and grids. Never use the same layout twice in a row

Output: `content_slides.pptx`

## Step 3: Merge and Pack

Write a merge config and run the script. **Do NOT manually edit XML/rels.**

```json
{
  "template_dir": "unpacked",
  "content_pptx": "content_slides.pptx",
  "output": "output.pptx",
  "layout": [
    {"chapter": 1, "content_pages": 3},
    {"chapter": 2, "content_pages": 2},
    {"chapter": 3, "content_pages": 3}
  ]
}
```

```bash
python scripts/merge_content.py merge_config.json
```

This handles:
- **Discovers** PptxGenJS's complete master chain (slide → slideLayout → slideMaster → theme)
- **Copies** the entire master system as an independent master into the template (auto-renamed to avoid conflicts)
- **Injects** background image + red bar into the copied slideMaster (not content pages)
- **Copies content slides XML verbatim** — zero modifications to PptxGenJS output
- **Updates** content slide rels: remaps slideLayout target to copied layout, drops notesSlide
- Sets up rIds and content types
- Builds interleaved slide order (divider → content → divider → content → ...)
- Runs clean.py to remove orphaned files
- Packs final PPTX with `--validate false`

### Architecture

```
Content pages (PptxGenJS)           Template (build_structure.py)
      │                                      │
      │  XML: untouched                       │  slide1 (cover)
      │  rels: slideLayout40.xml              │  slide5-8 (dividers)
      │         │                             │  slide4 (end)
      │         ▼                             │
      │  slideLayout40.xml ──────────┐        │
      │         │                    │        │
      │         ▼                    ▼        │
      │  slideMaster4.xml      slideMaster3   │
      │    (bg + red bar)      (template)     │
      │         │                    │        │
      │         ▼                    ▼        │
      │     theme6.xml          theme1-5      │
      │                                      │
      └────── merge_content.py ──────────────┘
                      │
                      ▼
                output.pptx
```

**Key principle**: Content pages and their master system are self-contained. The template's existing masters (for cover/dividers/end) are completely separate.

---

## Template Reference

| Page | Method | Description |
|------|--------|-------------|
| Cover (slide1) | build_structure.py | Title replacement only |
| Dividers (slide5+) | build_structure.py | Auto highlight + colors |
| Content (slide9+) | PptxGenJS → merge_content.py | XML verbatim; bg + red bar from copied slideMaster |
| End (slide4) | Automatic | No edits needed |

---

---

## Design Ideas

**Don't create boring slides.** Even with template constraints (red accent, Microsoft YaHei font, background image), content pages should be visually varied and engaging. Plain bullets on a white card won't impress anyone.

### Before Starting

- **Pick a bold, content-informed color palette**: Choose secondary accent colors that feel designed for THIS topic. C00000 is always primary, but the supporting colors should reflect the subject matter.
- **Dominance over equality**: One color should dominate (60-70% visual weight). Use C00000 as the primary accent, with 1-2 neutral supporting tones.
- **Dark/light contrast**: Use the template's background for visual depth — dark title zones and light content areas create a "sandwich" structure that adds visual interest.
- **Commit to a visual motif**: Pick ONE distinctive element and repeat it across content slides — rounded image frames, icons in colored circles, thick single-side borders, stat callouts.
- **Vary every slide**: Never repeat the same layout twice in a row.

### Accent Colors

Beyond the brand red (C00000), introduce secondary accent colors to add visual depth. Choose based on topic:

| Theme | Secondary | Usage |
|-------|-----------|-------|
| **Professional** | `1C7293` (teal) | Charts, icon circles |
| **Warm** | `B85042` (terracotta) | Stat highlights, table headers |
| **Fresh** | `2C5F2D` (forest) | Icon fills, data bars |
| **Modern** | `36454F` (charcoal) | Card backgrounds, borders |
| **Bold** | `F96167` (coral) | Secondary highlights |

**Rule**: C00000 stays for titles and primary visual weight. Use secondary colors sparingly for variety.

### For Each Slide

**Every slide needs a visual element** — image, chart, icon, or shape. Text-only slides are forgettable.

**Layout options:**
- Two-column (text left, illustration on right)
- Icon + text rows (icon in colored circle, bold header, description below)
- 2x2 or 2x3 grid (image on one side, grid of content blocks on other)
- Half-bleed image (full left or right side) with content overlay

**Data display:**
- Large stat callouts (big numbers 60-72pt with small labels below)
- Comparison columns (before/after, pros/cons, side-by-side options)
- Timeline or process flow (numbered steps, arrows)

**Visual polish:**
- Icons in small colored circles next to section headers
- Italic accent text for key stats or taglines

### Typography

Content pages use **Microsoft YaHei** (template constraint).

| Element | Size | Weight | Color |
|---------|------|--------|-------|
| Slide title | 28pt | Bold | C00000 |
| Section header | 18pt | Bold | C00000 |
| Body text | 14pt | Regular | 000000 |
| Captions | 12pt | Regular | 999999 |
| Stat numbers | 48pt | Bold | C00000 |
| Table headers | 14pt | Bold | FFFFFF on C00000 |

### Spacing

- Title zone: y=0.30" to y=1.39"
- Content zone: y=1.50" to y=5.07"
- 0.3-0.5" between content blocks
- Leave breathing room—don't fill every inch

### Avoid (Common Mistakes)

- **Don't repeat the same layout** — vary columns, cards, callouts, and charts across slides
- **Don't center body text** — left-align paragraphs and lists; center only titles and stat numbers
- **Don't skimp on size contrast** — titles need 28pt to stand out from 14pt body
- **Don't default to blue** — use C00000 as primary accent; secondary colors should reflect the topic, not default to generic blue
- **Don't mix spacing randomly** — choose 0.3" or 0.5" gaps and use consistently
- **Don't style one slide and leave the rest plain** — commit fully or keep it simple throughout
- **Don't create text-only slides** — add images, icons, charts, or visual elements; avoid plain title + bullets
- **Don't forget text box padding** — when aligning shapes with text, set `margin: 0` on the text box
- **Don't use low-contrast elements** — icons AND text need strong contrast against the background
- **NEVER use accent lines under titles** — these are a hallmark of AI-generated slides; use whitespace or background color instead

---

## QA (Required)

**Assume there are problems. Your job is to find them.**

Your first render is almost never correct. Approach QA as a bug hunt, not a confirmation step. If you found zero issues on first inspection, you weren't looking hard enough.

### Content QA

```bash
python -m markitdown output.pptx
```

Check for missing content, typos, wrong order.

**Check for leftover placeholder text:**

```bash
python -m markitdown output.pptx | grep -iE "xxxx|lorem|ipsum|this.*(page|slide).*layout"
```

If grep returns results, fix them before declaring success.

## Dependencies

- `pip install "markitdown[pptx]" defusedxml` — extraction + XML parsing
- `pip install Pillow` — thumbnails
- `npm install -g pptxgenjs` — content generation
- `npm install -g react-icons react react-dom sharp` — icon generation