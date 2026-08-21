# PPT_Template_Creation.md
*TBN Internal · June 2026*
*Guidance for Claude AI — PowerPoint template creation for TBN reporting projects*

---

## Purpose

This document governs how Claude creates and modifies PowerPoint template files for use in TBN reporting projects. Templates produced by this process are used directly in PowerPoint with Copilot, and also consumed by ChartGen (M02 Template Reader).

Two scenarios are covered: creating a new template from scratch, and adding a new slide layout to an existing template.

**Output format:** all templates are produced as `.pptx` files. A `.pptx` contains:
- A slide master with named slide layouts defining the structure and visual design of each page type
- One real slide — the cover page — as the first and only actual slide
- One sample slide per layout, demonstrating the visual design of that layout to Copilot

The sample slides are how Copilot learns the template. They must visually demonstrate the layout — background, title band, footer, placeholder positions — not just list placeholder names.

---

## Opening Decision Gate

**Before anything else, ask:**

> Are you creating a completely new template, or adding a new slide layout to an existing one?

This is the first question, always.

---

## Path A — New Template From Scratch

### Step 1 — Page Dimensions

Ask the user:

> What format is this template for?
> - **A4 portrait** (21 × 29.7 cm) — document-style, typically PDF output
> - **A4 landscape** (29.7 × 21 cm) — wider format, suits both reports and presentations
> - **Standard widescreen** (33.87 × 19.05 cm) — screen-first, presentations and slidepacks
> - **Other** — user specifies dimensions

Record the choice. All placeholder positions, margins, and safe zones are calculated relative to this. Do not proceed until confirmed.

**Dimension reference (in EMUs):**

| Format | Width (EMU) | Height (EMU) |
|--------|-------------|--------------|
| A4 portrait | 6858000 | 9144000 |
| A4 landscape | 9144000 | 6858000 |
| Standard widescreen | 9144000 | 5143500 |

### Step 2 — Assets

Ask the user:

> Do you have any existing assets to work from? For example:
> - An existing `.pptx` file to use as a style reference
> - A logo file
> - A colour palette or brand guidelines
> - Any other visual reference material

This step is non-blocking — if the user has nothing, proceed on defaults.

**CRITICAL — assets are visual inspiration only. Their structure is completely irrelevant.**

Any `.pptx` file provided at this stage is a source of visual properties only: colours, fonts, and branding. That is all. Extract those properties silently and move on.

- Do not inspect, comment on, or ask questions about the slides, layouts, or structure of a reference file
- Do not ask whether to use layouts from the reference file
- Do not ask whether the reference file is complete or well-structured
- Never use a reference file as a base — the new template is always built from scratch
- Never subject a reference file to the consistency audit — that is a Path B behaviour only

The canonical layout set (Appendix B) is always the output. The only thing a reference `.pptx` can change is the visual appearance of those layouts — colours, fonts, branding. Nothing else.

Extract from any reference `.pptx`: dominant colours, fonts in use, approximate margin widths, and any logo or branding assets visible. Use these silently to inform the visual design conversation that follows.

If a colour palette is provided or extracted, record the hex values for use throughout. If none is available, use ChartGen defaults:

| Role | Hex |
|------|-----|
| Navy (primary) | `071A34` |
| Crimson (accent) | `C12958` |
| Orange (accent) | `E7492D` |
| White | `FFFFFF` |
| Light grey (backgrounds) | `F4F4F4` |
| Mid grey (borders, captions) | `CCCCCC` |

### Step 3 — Visual Design Conversation

**This step is mandatory and always runs in full — regardless of what assets were provided in Step 2.**

Assets inform this conversation; they do not replace it. Receiving a reference `.pptx`, a logo, or a colour palette does not mean the user's formatting preferences are known — it means there is useful material to draw on when asking. Never skip or abbreviate this conversation on the basis that assets were supplied.

Ask the following questions one at a time, in plain English, in a natural conversational sequence. Do not present them as a list or a form. Where assets provide relevant context, weave that in as a suggestion within the question (e.g. "I can see your brand uses navy — would you like that as the title band colour?"). If the user has no preference on any question, apply the default.

**Question 1 — Page background**

> "What would you like the background of your pages to look like — plain white, a light colour, or something else?"

Default: white (`FFFFFF`). If brand colours are available, suggest the lightest brand colour as an alternative. Apply consistently across all layouts except the cover, which may differ.

**Question 2 — Title area**

> "For the title at the top of each page, would you like it on a plain background, or would you prefer a coloured band or bar behind the title to make it stand out?"

Default: a solid coloured band spanning the full page width, using the primary brand colour (or navy `071A34` if none available), with the title text in white. Height should comfortably contain the title text with padding. Apply consistently across all content layouts.

**Question 3 — Footer**

> "Would you like a footer at the bottom of each page — for example, with a page number, a copyright line, or a brand colour bar?"

Default: a thin coloured bar at the bottom of every layout using the primary brand colour, with a small copyright/organisation text placeholder left and page number right. No more than 8–10% of page height.

**Question 4 — Accent colour usage**

> "Do you want accent colours used anywhere — for example, to highlight section dividers, table headers, or chart legend areas?"

Default: secondary brand colour (or crimson `C12958`) for section divider backgrounds and table header rows. Mid grey for borders and dividing lines within content areas.

**Question 5 — Additional layouts**

> "I'll create the full standard set of layouts — cover, contents, section divider, text, chart, table, and dashboard pages. Are there any additional or specific layouts you're looking for?"

The default output is always the complete canonical set defined in Appendix B. Build all archetypes unless the user explicitly removes any or requests changes. If the user names additional layouts, incorporate them.

**Tone and approach:**
- Assume the user is neither a developer nor a designer. Do not use technical terms without explanation.
- Make confident design proposals — offer a clear default and invite the user to push back.
- After producing any draft, say something like: *"I've put together a first version — please have a look and tell me how it feels. We'll keep refining it until you're happy."* Vary the wording naturally.
- Never consider a template finished until the user explicitly confirms they are happy.
- The user holds final authority on any design decision not explicitly governed by this document.

**Applying the design across all layouts**

Once the visual design is established, apply it consistently to every layout and every sample slide:

- Background colour set on every layout and sample slide
- Title band present on every content layout at the same position and height
- Footer bar present on every layout at the same position and height
- All text elements using the agreed font at the agreed sizes
- Placeholder borders invisible — remove borders from all placeholder shapes unless they serve a deliberate design purpose
- Brand colours used purposefully and consistently
- The cover and section divider layouts may deviate from the standard content treatment but must feel part of the same visual family

### Step 4 — Build and Present

Build the complete template as a `.pptx` file using python-pptx. The file must contain:

1. **A slide master** with all named layouts (see Naming Conventions and Appendix B)
2. **One real slide** — the cover page, fully styled, as the first slide in the deck
3. **One sample slide per layout** — each demonstrating the visual design of that layout with placeholder prompt text visible (e.g. `Title 1`, `Chart 1`, `Text 1`)

Sample slides must show the full visual design — background, title band, footer, placeholder positions. They are not blank white pages with text labels. Copilot learns the template from these sample slides; if they are blank, Copilot learns nothing.

Present the file immediately on completion. After presenting, invite feedback and iterate until the user is satisfied.

---

## Path B — Adding a Layout to an Existing Template

### Step 1 — Receive the File

The user uploads an existing `.pptx` template file.

### Step 2 — Consistency Audit

Run the audit silently before engaging the user in any design conversation. Do not ask the user to do this — it is your job. See Appendix A for the full audit procedure.

After the audit, present a short plain-English summary:

> "I've reviewed the existing template. Here's what I found: [findings]. I'll follow the conventions already established in the file when building the new layout. [Flag any significant inconsistencies.]"

If the file was produced by this process previously and follows ChartGen conventions cleanly, say so briefly and move on.

### Step 3 — Design Conversation

Ask what the new layout needs to display and propose a design from the archetype library.

**Critical constraint:** do not run the visual design conversation from Path A Step 3 — the visual design is already established by the existing template. Match fonts, colours, margin widths, title band height, footer treatment, and spacing exactly to what is already present. Do not introduce any new visual elements unless the user explicitly requests them and is aware this creates an inconsistency.

### Step 4 — Build, Insert, and Present

Build the new layout, insert it into the existing template file, and add a corresponding sample slide. Present the file. Invite feedback and iterate until the user is satisfied.

---

## Naming Conventions

These conventions are mandatory. ChartGen (M02) and Copilot both rely on them.

### Layout Names

Copilot recognises the following keywords in layout names: **Title**, **Section**, **Content**, **Agenda**, **Conclusion**. Layout names must incorporate these keywords where applicable so Copilot selects the right layout for each slide type.

Format: `[Keyword]-[Descriptor]`

| Layout | Name | Copilot keyword |
|--------|------|-----------------|
| Cover page | `Title-Cover` | Title |
| Contents / index | `Agenda-Contents` | Agenda |
| Section divider | `Section-Divider` | Section |
| Two-column prose | `Content-Text` | Content |
| Single chart | `Content-Chart` | Content |
| Two stacked charts | `Content-ChartDouble` | Content |
| Table with intro text | `Content-Table` | Content |
| Metrics dashboard | `Content-Dashboard` | Content |
| Stats callout grid | `Content-StatsGrid` | Content |
| Chart + small table | `Content-Mixed` | Content |

### Placeholder Names

Format: `[Type] [Number]` — space-separated, title case, numbered left-to-right top-to-bottom within each layout.

| Type | Use |
|------|-----|
| `Title` | Slide or section title |
| `Subtitle` | Secondary title or descriptor |
| `Chart` | Chart insertion target |
| `Text` | Body text or narrative |
| `Table` | Table insertion target |
| `Image` | Logo, icon, or supporting image |

Examples: `Title 1`, `Chart 1`, `Text 1`, `Text 2`, `Image 1`

### Placeholder Types

All placeholders must be proper PowerPoint placeholder objects — not text boxes or shapes. This is mandatory:

- **Text placeholders** — for `Title`, `Subtitle`, `Text` slots
- **Picture placeholders** — for `Chart`, `Image` slots
- **Table placeholders** — for `Table` slots

ChartGen inserts charts and images by reading placeholder position and size. A text box or freeform shape will not be recognised by M02. Placeholder prompt text (the greyed text visible when empty) must be set to the placeholder name — e.g. `Title 1`, `Chart 1` — not sample content such as "Productivity" or "Click to add title."

---

## Design Principles

**Consistency is the primary constraint.** Margins, band heights, font sizes, and spacing must be identical across all layouts. A 1.5cm margin on one layout means 1.5cm on every layout.

**Safe zone defaults:**

| Format | Margin |
|--------|--------|
| A4 portrait | 1.5 cm |
| A4 landscape | 1.5 cm |
| Standard widescreen | 1.27 cm (0.5") |

**Typography defaults (overridable by user):**

| Element | Size |
|---------|------|
| Slide title | 28–36pt |
| Section header | 18–22pt |
| Body / narrative | 12–14pt |
| Caption / label | 10–11pt |

Default to safe-list fonts (Arial, Calibri, Cambria) unless the user specifies otherwise. Note: fonts outside the safe list may not render accurately in QA previews.

---

## Technical Reference

All template files are built using **python-pptx**. Templates are saved as `.pptx` (not `.potx`).

### Slide Dimensions

```python
from pptx import Presentation
from pptx.util import Emu

prs = Presentation()

# A4 portrait
prs.slide_width = Emu(6858000)
prs.slide_height = Emu(9144000)

# A4 landscape
prs.slide_width = Emu(9144000)
prs.slide_height = Emu(6858000)

# Standard widescreen
prs.slide_width = Emu(9144000)
prs.slide_height = Emu(5143500)
```

### Coordinate Model

All placeholder positions and sizes are defined in EMUs.

```python
EMU_PER_CM = 360000
EMU_PER_INCH = 914400

# Example: 1.5cm margin
margin = int(1.5 * EMU_PER_CM)  # 540000 EMU
```

### Background Colour

Apply background colour to each layout via the slide background fill:

```python
from pptx.dml.color import RGBColor
from pptx.util import Pt
from lxml import etree

def set_slide_background(slide_layout, hex_colour):
    background = slide_layout.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor.from_string(hex_colour)
```

### Coloured Title Band

Add a solid rectangle as the title band behind the title placeholder:

```python
from pptx.util import Emu
from pptx.dml.color import RGBColor

def add_title_band(slide_layout, width_emu, band_height_emu, hex_colour):
    txBox = slide_layout.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        0, 0, width_emu, band_height_emu
    )
    txBox.fill.solid()
    txBox.fill.fore_color.rgb = RGBColor.from_string(hex_colour)
    txBox.line.fill.background()  # no border
```

### Footer Bar

```python
def add_footer_bar(slide_layout, width_emu, page_height_emu, bar_height_emu, hex_colour):
    top = page_height_emu - bar_height_emu
    bar = slide_layout.shapes.add_shape(1, 0, top, width_emu, bar_height_emu)
    bar.fill.solid()
    bar.fill.fore_color.rgb = RGBColor.from_string(hex_colour)
    bar.line.fill.background()
```

### Reading Placeholder Names (M02 pattern)

```python
def read_template_placeholders(pptx_path):
    prs = Presentation(pptx_path)
    layouts = {}
    for layout in prs.slide_master.slide_layouts:
        placeholders = []
        for ph in layout.placeholders:
            placeholders.append({
                'name': ph.name,
                'left': ph.left,
                'top': ph.top,
                'width': ph.width,
                'height': ph.height
            })
        layouts[layout.name] = placeholders
    return layouts
```

---

## QA

After building, convert to images and inspect:

```bash
python scripts/office/soffice.py --headless --convert-to pdf --outdir /home/claude/ output.pptx
rm -f slide-*.jpg
pdftoppm -jpeg -r 150 output.pdf slide
```

Check every sample slide for:
- Background colour applied
- Title band visible and correctly positioned
- Footer bar visible and correctly positioned
- Placeholder prompt text showing correctly (e.g. `Title 1`, not empty)
- No content overlapping slide edges
- Consistent margins across all layouts

---

## Appendix A — Consistency Audit Procedure

When inspecting an existing `.pptx` before adding a layout (Path B only), extract and compare across all slide layouts:

1. **Slide dimensions** — confirm width and height; flag if non-standard
2. **Fonts** — list all font families; flag if more than one family appears across comparable elements
3. **Margins** — infer from placeholder positions; flag significant variation between layouts
4. **Placeholder naming** — check against `[Type] [Number]` convention; flag any that do not conform
5. **Colour usage** — list dominant colours; flag significant variation suggesting mixed design origins
6. **Font sizes** — check title and body sizes are consistent; flag outliers

Present findings as a brief plain-English summary. This is informational, not a blocker.

---

## Appendix B — Layout Archetypes

Derived from review of real TBN report outputs (NCC Analysis and Intermediate Care reports, June 2026). Content-agnostic structural layouts only.

| Archetype | Layout Name | Description | Typical Placeholders | Notes |
|-----------|-------------|-------------|----------------------|-------|
| Cover | `Title-Cover` | Report cover page. Title, subtitle, organisation name, logos, decorative elements. | `Title 1`, `Subtitle 1`, `Text 1`, `Image 1`, `Image 2` | Image slots for logos. Text 1 is org name or date line. |
| Contents | `Agenda-Contents` | Section index. Two-column table of section names and page numbers. | `Title 1`, `Table 1` | Structural feature of the report. |
| Section Divider | `Section-Divider` | Opens a new section. Icon top-left, section title, brief descriptor. | `Title 1`, `Text 1`, `Image 1` | Image 1 is the section icon. Visually distinct from content pages. |
| Text | `Content-Text` | Narrative text, typically two-column prose. No charts or tables. | `Title 1`, `Text 1`, `Text 2` | Text 2 is the right column. For introduction, methodology, how-to pages. |
| Chart | `Content-Chart` | Single benchmarking chart. Legend/summary panel right; financial summary below. | `Title 1`, `Chart 1`, `Text 1`, `Text 2` | Text 1 is legend panel. Text 2 is summary below chart. |
| Chart Double | `Content-ChartDouble` | Two charts stacked vertically, each with legend panel and summary. Most common layout in TBN individualised reports. | `Title 1`, `Chart 1`, `Text 1`, `Text 2`, `Chart 2`, `Text 3`, `Text 4` | Numbering top-to-bottom: Chart 1 / Text 1 (legend) / Text 2 (summary) / Chart 2 / Text 3 (legend) / Text 4 (summary). |
| Table | `Content-Table` | Introductory prose above a full-width data table. For summary and ranking tables. | `Title 1`, `Text 1`, `Table 1` | Text 1 is intro paragraph(s). Table 1 fills remaining area. |
| Dashboard | `Content-Dashboard` | Multi-row metrics table. Each row shows metric name, distribution bar, and numeric summary columns. | `Title 1`, `Table 1` | Distribution bars are part of the table. Table dominates the page. |
| Stats Grid | `Content-StatsGrid` | Grid of stat callout boxes. Each box contains icon, headline figure, descriptor, submission value. For PREM, staff survey, clinical case review. | `Title 1`, `Table 1` | Rendered as a structured table of callout cells. Content via flag replacement. |
| Mixed | `Content-Mixed` | Question/subheading, horizontal bar chart left, small data table right. For yes/no and categorical comparisons. | `Title 1`, `Text 1`, `Chart 1`, `Table 1` | Text 1 is the question/subheading. Chart 1 and Table 1 sit side by side. |

---

*End of document*
