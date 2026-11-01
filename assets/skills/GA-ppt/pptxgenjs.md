# PptxGenJS - Content Page Generation

This guide covers generating **content pages** with rich layouts using PptxGenJS. These pages use the template's background image and brand colors.

For cover/divider/end pages, read [editing.md](editing.md).

---

## Setup

```javascript
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10" x 5.625"
pres.author = "公司";

// Brand colors
const BRAND = {
  RED: "C00000",
  DARK_RED: "C00000",
  WHITE: "FFFFFF",
  BLACK: "000000",
  LIGHT_GRAY: "CECECE",
  MID_GRAY: "999999",
  BG_GRAY: "F5F5F5",
};

const FONT = "Microsoft YaHei";
```

---

## Layout Dimensions

Slide dimensions (coordinates in inches):
- `LAYOUT_16x9`: 10" × 5.625" (default)
- `LAYOUT_16x10`: 10" × 6.25"
- `LAYOUT_4x3`: 10" × 7.5"
- `LAYOUT_WIDE`: 13.3" × 7.5"

---

## Text & Formatting

```javascript
// Basic text
slide.addText("Simple Text", {
  x: 0.69, y: 1.50, w: 8.62, h: 2, fontSize: 24, fontFace: FONT,
  color: "363636", bold: true, align: "center", valign: "middle"
});

// Character spacing (use charSpacing, not letterSpacing which is silently ignored)
slide.addText("SPACED TEXT", { x: 0.69, y: 1.50, w: 8.62, h: 1, charSpacing: 6 });

// Rich text arrays
slide.addText([
  { text: "Bold ", options: { bold: true } },
  { text: "Italic ", options: { italic: true } }
], { x: 0.69, y: 3, w: 8.62, h: 1 });

// Multi-line text (requires breakLine: true)
slide.addText([
  { text: "Line 1", options: { breakLine: true } },
  { text: "Line 2", options: { breakLine: true } },
  { text: "Line 3" }  // Last item doesn't need breakLine
], { x: 0.69, y: 1.50, w: 8.62, h: 2 });

// Text box margin (internal padding)
slide.addText("Title", {
  x: 0.69, y: 0.30, w: 8.62, h: 0.6,
  margin: 0  // Use 0 when aligning text with other elements like shapes or icons
});
```

**Tip:** Text boxes have internal margin by default. Set `margin: 0` when you need text to align precisely with shapes, lines, or icons at the same x-position.

---

## Lists & Bullets

```javascript
// ✅ CORRECT: Multiple bullets
slide.addText([
  { text: "First item", options: { bullet: true, breakLine: true } },
  { text: "Second item", options: { bullet: true, breakLine: true } },
  { text: "Third item", options: { bullet: true } }
], { x: 0.69, y: 1.50, w: 8.62, h: 3 });

// ❌ WRONG: Never use unicode bullets
slide.addText("• First item", { ... });  // Creates double bullets

// Sub-items and numbered lists
{ text: "Sub-item", options: { bullet: true, indentLevel: 1 } }
{ text: "First", options: { bullet: { type: "number" }, breakLine: true } }
```

---

## Content Page Slide Master

Define a minimal master — **do NOT set background or red bar** (merge_content.py injects them automatically):

```javascript
pres.defineSlideMaster({
  title: "CONTENT_PAGE",
  // No background — injected by merge_content.py
  // No red bar — injected by merge_content.py
});
```

Create content slides:

```javascript
let slide = pres.addSlide({ masterName: "CONTENT_PAGE" });
```

---

## Content Safe Zones

| Zone | Position | Purpose |
|------|----------|---------|
| Title | x=0.69", y=0.30", w=8.62", h=1.09" | Slide title |
| Content | x=0.69", y=1.50", w=8.62", h=3.57" | Main content |
| Page number | x=7.12", y=5.34", w=2.25", h=0.30" | Do not cover |

---

## Icons (react-icons)

Use react-icons to generate SVG icons, then rasterize to PNG for universal compatibility.

### Setup

```javascript
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const { FaCheckCircle, FaChartLine, FaRocket, FaLightbulb, FaStar, FaUsers, FaCog, FaShieldAlt } = require("react-icons/fa");

function renderIconSvg(IconComponent, color = "#000000", size = 256) {
  return ReactDOMServer.renderToStaticMarkup(
    React.createElement(IconComponent, { color, size: String(size) })
  );
}

async function iconToBase64Png(IconComponent, color, size = 256) {
  const svg = renderIconSvg(IconComponent, color, size);
  const pngBuffer = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + pngBuffer.toString("base64");
}
```

### Add Icon to Slide

```javascript
const iconData = await iconToBase64Png(FaCheckCircle, "#C00000", 256);

slide.addImage({
  data: iconData,
  x: 0.69, y: 1.60, w: 0.50, h: 0.50  // Size in inches
});
```

**Note**: Use size 256 or higher for crisp icons. The size parameter controls rasterization resolution, not display size (set by `w` and `h` in inches).

### Icon Libraries

Install: `npm install -g react-icons react react-dom sharp`

Popular icon sets in react-icons:
- `react-icons/fa` - Font Awesome
- `react-icons/md` - Material Design
- `react-icons/hi` - Heroicons
- `react-icons/bi` - Bootstrap Icons

---

## Shapes

```javascript
slide.addShape(pres.shapes.RECTANGLE, {
  x: 0.69, y: 1.50, w: 3.0, h: 2.0,
  fill: { color: "F5F5F5" }, line: { color: "CECECE", width: 1 }
});

slide.addShape(pres.shapes.OVAL, { x: 4, y: 1.50, w: 1.0, h: 1.0, fill: { color: "C00000" } });

slide.addShape(pres.shapes.LINE, {
  x: 0.69, y: 2.00, w: 8.62, h: 0, line: { color: "CECECE", width: 1, dashType: "dash" }
});

// With transparency
slide.addShape(pres.shapes.RECTANGLE, {
  x: 0.69, y: 1.50, w: 8.62, h: 3.57,
  fill: { color: "FFFFFF", transparency: 80 }
});

// Rounded rectangle
slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
  x: 0.69, y: 1.50, w: 4.10, h: 2.50,
  fill: { color: "FFFFFF" }, rectRadius: 0.1
});

// With shadow
slide.addShape(pres.shapes.RECTANGLE, {
  x: 0.69, y: 1.50, w: 4.10, h: 3.57,
  fill: { color: "FFFFFF" },
  shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.15 }
});
```

Shadow options:

| Property | Type | Range | Notes |
|----------|------|-------|-------|
| `type` | string | `"outer"`, `"inner"` | |
| `color` | string | 6-char hex (e.g. `"000000"`) | No `#` prefix, no 8-char hex |
| `blur` | number | 0-100 pt | |
| `offset` | number | 0-200 pt | Must be non-negative |
| `angle` | number | 0-359 degrees | 135 = bottom-right, 270 = upward |
| `opacity` | number | 0.0-1.0 | Use this for transparency, never encode in color string |

---

## Slide Backgrounds

> ⚠️ **Do NOT set `slide.background` on content pages!** The merge script (`merge_content.py`) injects the background image and red bar into the slideMaster automatically. Setting `slide.background` will override the template background.

```javascript
// Solid color (for reference only — do NOT use on content pages)
slide.background = { color: "F1F1F1" };

// Color with transparency
slide.background = { color: "FF3399", transparency: 50 };

// Image from URL
slide.background = { path: "https://example.com/bg.jpg" };

// Image from base64
slide.background = { data: "image/png;base64,iVBORw0KGgo..." };
```

---

## Images

### Image Sources

```javascript
// From file path
slide.addImage({ path: "images/chart.png", x: 0.69, y: 1.50, w: 4.0, h: 3.0 });

// From URL
slide.addImage({ path: "https://example.com/image.jpg", x: 0.69, y: 1.50, w: 4.0, h: 3.0 });

// From base64 (faster, no file I/O)
slide.addImage({ data: "image/png;base64,iVBORw0KGgo...", x: 0.69, y: 1.50, w: 4.0, h: 3.0 });
```

### Image Options

```javascript
slide.addImage({
  path: "image.png",
  x: 0.69, y: 1.50, w: 5, h: 3,
  rotate: 45,              // 0-359 degrees
  rounding: true,          // Circular crop
  transparency: 50,        // 0-100
  flipH: true,             // Horizontal flip
  flipV: false,            // Vertical flip
  altText: "Description",  // Accessibility
  hyperlink: { url: "https://example.com" }
});
```

### Calculate Dimensions (preserve aspect ratio)

```javascript
const origWidth = 1978, origHeight = 923, maxHeight = 3.0;
const calcWidth = maxHeight * (origWidth / origHeight);
const centerX = 0.69 + (8.62 - calcWidth) / 2;

slide.addImage({ path: "image.png", x: centerX, y: 1.50, w: calcWidth, h: maxHeight });
```

### Image Sizing Modes

```javascript
// Contain - fit inside, preserve ratio
{ sizing: { type: 'contain', w: 4, h: 3 } }

// Cover - fill area, preserve ratio (may crop)
{ sizing: { type: 'cover', w: 4, h: 3 } }

// Crop - cut specific portion
{ sizing: { type: 'crop', x: 0.5, y: 0.5, w: 2, h: 2 } }
```

### Supported Formats

- **Standard**: PNG, JPG, GIF (animated GIFs work in Microsoft 365)
- **SVG**: Works in modern PowerPoint/Microsoft 365

---

## Better Charts

Default charts look dated. Apply these options for a modern appearance:

```javascript
slide.addChart(pres.charts.BAR, chartData, {
  x: 0.69, y: 1.50, w: 8.62, h: 3.57, barDir: "col",

  // Custom colors (use brand + secondary accent)
  chartColors: ["C00000", "1C7293", "36454F"],

  // Clean background
  chartArea: { fill: { color: "FFFFFF" }, roundedCorners: true },

  // Muted axis labels
  catAxisLabelColor: "64748B",
  valAxisLabelColor: "64748B",

  // Subtle grid (value axis only)
  valGridLine: { color: "E2E8F0", size: 0.5 },
  catGridLine: { style: "none" },

  // Data labels on bars
  showValue: true,
  dataLabelPosition: "outEnd",
  dataLabelColor: "000000",

  // Hide legend for single series
  showLegend: false,
});

// Line chart
slide.addChart(pres.charts.LINE, [{
  name: "趋势", labels: ["Q1", "Q2", "Q3", "Q4"], values: [450, 550, 620, 710]
}], {
  x: 0.69, y: 1.50, w: 8.62, h: 3.57,
  lineSize: 3, lineSmooth: true,
  chartColors: ["C00000"],
  showLegend: false,
});

// Pie chart
slide.addChart(pres.charts.PIE, [{
  name: "占比", labels: ["A", "B", "C"], values: [35, 45, 20]
}], {
  x: 0.69, y: 1.50, w: 5.0, h: 3.57,
  chartColors: ["C00000", "1C7293", "CECECE"],
  showPercent: true, showLegend: true, legendPos: "b",
});
```

Chart types: BAR, LINE, PIE, DOUGHNUT, SCATTER, BUBBLE, RADAR

---

## Tables

```javascript
slide.addTable([
  ["Header 1", "Header 2"],
  ["Cell 1", "Cell 2"]
], {
  x: 0.69, y: 1.50, w: 8.62, h: 2,
  border: { pt: 1, color: "999999" }, fill: { color: "F1F1F1" }
});

// Advanced with merged cells
let tableData = [
  [{ text: "Header", options: { fill: { color: "C00000" }, color: "FFFFFF", bold: true } }, "Cell"],
  [{ text: "Merged", options: { colspan: 2 } }]
];
slide.addTable(tableData, { x: 0.69, y: 3.50, w: 8.62, colW: [4.31, 4.31] });
```

---

## Output and Merge

```javascript
pres.writeFile({ fileName: "content_slides.pptx" });
```

Then run merge_content.py to inject background + red bar and pack into the final template structure.

---

## Common Pitfalls

These issues cause file corruption, visual bugs, or broken output. Avoid them.

1. **NEVER use "#" with hex colors** — causes file corruption
   ```javascript
   color: "C00000"      // ✅ CORRECT
   color: "#C00000"     // ❌ WRONG
   ```

2. **NEVER encode opacity in hex color strings** — 8-char colors (e.g., `"00000020"`) corrupt the file. Use the `opacity` property instead.
   ```javascript
   shadow: { type: "outer", blur: 6, offset: 2, color: "00000020" }          // ❌ CORRUPTS FILE
   shadow: { type: "outer", blur: 6, offset: 2, color: "000000", opacity: 0.12 }  // ✅ CORRECT
   ```

3. **Use `bullet: true`** — NEVER unicode symbols like "•" (creates double bullets)

4. **Use `breakLine: true`** between text array items or runs will merge together

5. **Avoid `lineSpacing` with bullets** — causes excessive gaps; use `paraSpaceAfter` instead

6. **Each presentation needs fresh instance** — don't reuse `pptxgen()` objects

7. **NEVER reuse option objects across calls** — PptxGenJS mutates objects in-place. Sharing one object between multiple calls corrupts the second shape.
   ```javascript
   const shadow = { type: "outer", blur: 6, offset: 2, color: "000000", opacity: 0.15 };
   slide.addShape(pres.shapes.RECTANGLE, { shadow, ... });  // ❌ second call gets already-converted values
   slide.addShape(pres.shapes.RECTANGLE, { shadow, ... });

   const makeShadow = () => ({ type: "outer", blur: 6, offset: 2, color: "000000", opacity: 0.15 });
   slide.addShape(pres.shapes.RECTANGLE, { shadow: makeShadow(), ... });  // ✅ fresh object each time
   slide.addShape(pres.shapes.RECTANGLE, { shadow: makeShadow(), ... });
   ```

8. **Don't use `ROUNDED_RECTANGLE` with accent borders** — rectangular overlay bars won't cover rounded corners. Use `RECTANGLE` instead.

9. **Stay in safe zones** — y=1.50" to y=5.07" for content; the merge script injects a red bar at y=0-0.06" and a background image.

10. **Font**: Always `"Microsoft YaHei"` for content pages.

---

## Quick Reference

- **Shapes**: RECTANGLE, OVAL, LINE, ROUNDED_RECTANGLE
- **Charts**: BAR, LINE, PIE, DOUGHNUT, SCATTER, BUBBLE, RADAR
- **Layout**: 10" × 5.625" (16:9)
- **Safe zones**: title y=0.30-1.39", content y=1.50-5.07"
- **Alignment**: "left", "center", "right"
- **Chart data labels**: "outEnd", "inEnd", "center"