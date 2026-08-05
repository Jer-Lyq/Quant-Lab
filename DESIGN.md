---
name: Quant Lab
description: Institutional quant research workbench UI.
colors:
  canvas: "#eef2ec"
  canvas-deep: "#e4ebe4"
  panel: "#ffffff"
  panel-soft: "#f8faf7"
  rail: "#13231b"
  rail-deep: "#102018"
  ink: "#132018"
  muted: "#66746b"
  line: "#d6dfd7"
  accent: "#2f7d5b"
  accent-soft: "#dbeae0"
typography:
  headline:
    fontFamily: "Segoe UI, Microsoft YaHei, PingFang SC, system-ui, sans-serif"
    fontSize: "30px"
    fontWeight: 700
    lineHeight: 1.08
  body:
    fontFamily: "Segoe UI, Microsoft YaHei, PingFang SC, system-ui, sans-serif"
    fontSize: "16px"
    lineHeight: 1.6
  label:
    fontFamily: "Segoe UI, Microsoft YaHei, PingFang SC, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 600
rounded:
  md: "8px"
  pill: "999px"
spacing:
  sm: "8px"
  md: "14px"
  lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.panel}"
    rounded: "{rounded.md}"
    padding: "0 18px"
  card:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
---

# Design System: Quant Lab

## Overview

**Creative North Star: "Institutional Research Desk"**

Quant Lab uses a restrained workbench system: a dark instrument rail, a pale research canvas, crisp green action states, compact panels, and tabular numerals. The interface should feel precise and durable, like a research terminal that has been softened just enough for daily use.

**Key Characteristics:**
- Dark persistent navigation for instrument context.
- Pale canvas and white inspection panels for charts, tables, and metadata.
- Green accent reserved for selected state and primary actions.
- Dense but readable spacing tuned for repeated research workflows.

## Colors

The palette is restrained: deep rail neutrals, pale operational surfaces, and one green accent.

### Primary
- **Desk Green**: The primary action and selection color.
- **Signal Wash**: A pale green support color used for session chips and subtle selected-state backgrounds.

### Neutral
- **Research Rail**: The dark left-side workspace surface.
- **Canvas Mist**: The main content background.
- **Paper Panel**: Cards, command bars, charts, and table surfaces.
- **Graphite Ink**: Main text.
- **Muted Ledger**: Secondary text and labels.
- **Quiet Rule**: Borders and separators.

**The Rare Accent Rule.** Green is used for state and action, not general decoration.

## Typography

**Display Font:** Segoe UI / Microsoft YaHei / PingFang SC system stack.
**Body Font:** Segoe UI / Microsoft YaHei / PingFang SC system stack.

**Character:** One clear UI family carries the whole product. The hierarchy comes from weight, spacing, and density rather than decorative type.

### Hierarchy
- **Headline**: Strong page and instrument names.
- **Title**: Panel and sidebar headings.
- **Body**: Metadata, descriptions, and ordinary UI text.
- **Label**: Chips, secondary labels, and compact control text.

## Layout

The core structure is a split workbench: a fixed-width instrument rail on the left and a flexible research surface on the right. The admin command area uses a five-column line on wide screens and folds the primary action to a second aligned row on narrower desktop widths. Below that, instrument identity, actions, stats, chart, and table keep a vertical inspection flow.

## Elevation & Depth

Depth is functional and subtle. Panels use soft shadows and borders to separate tools from the canvas without making every section feel like a floating card.

## Shapes

Corners are consistently controlled at 8px for panels, fields, buttons, list items, and charts. Pills are reserved for session identity and compact status chips.

## Components

### Buttons
- **Shape:** Compact rectangular controls with 8px radius.
- **Primary:** Green action buttons with enough width to read Chinese command text.
- **Hover / Focus:** State should be visible through contrast, border, and native focus treatment.

### Cards / Containers
- **Corner Style:** 8px radius.
- **Background:** White or very pale green-white.
- **Shadow Strategy:** Soft ambient shadow for command panels, stat boxes, chart, and table surfaces.

### Inputs / Fields
- **Style:** Pale or dark surface depending on context; search fields inside the rail use translucent dark treatment.
- **Focus:** Green ring/border in the rail, native Element Plus focus elsewhere.

### Navigation
- **Style:** Dark left rail with translucent instrument rows. Active items use green border and a tonal selected background.

## Do's and Don'ts

### Do:
- **Do** keep the admin command strip compact and aligned.
- **Do** preserve clear separation between browsing, syncing, and inspecting.
- **Do** keep chart and table surfaces calm so data remains primary.

### Don't:
- **Don't** use decorative gradients, oversized marketing sections, or large hero compositions in the authenticated workspace.
- **Don't** scatter accent green across inactive UI.
- **Don't** allow control rows to overflow horizontally at ordinary desktop widths.
