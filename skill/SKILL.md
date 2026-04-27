---
name: mermaid-to-svg
description: Convert Mermaid diagrams in Markdown files to SVG images. Use this skill when the user wants to convert Mermaid charts in Markdown to SVG format, generate SVG visualizations from Mermaid code blocks, or batch process Markdown files containing diagrams.
---

# Mermaid to SVG

Convert Mermaid diagrams in Markdown files to SVG images.

## Overview

This skill helps you convert Mermaid diagrams embedded in Markdown files into standalone SVG images. It:

- Processes single Markdown files or entire directories recursively
- Creates a folder with the same name as each Markdown file to store SVGs
- Generates simplified SVG names (001.svg, 002.svg, etc.)
- Automatically adds links after each Mermaid code block
- Cleans up unused SVG files from previous runs
- Auto-detects Chrome for Puppeteer if needed

## Prerequisites

The following must be installed on your system:

1. **Python 3.8+** (standard library only, no pip packages needed)
2. **Node.js and npm**
3. **Mermaid CLI (mmdc)**:
   ```bash
   npm install -g @mermaid-js/mermaid-cli
   ```
4. **Chrome/Chromium** for Puppeteer:
   ```bash
   npx puppeteer browsers install chrome
   ```

## Usage

### Basic Usage

```bash
python3 md_mermaid_to_svg.py <path>
```

### Process a Single File

```bash
python3 md_mermaid_to_svg.py ./document.md
```

### Process a Directory

```bash
python3 md_mermaid_to_svg.py ./docs
```

This recursively processes all `.md` files in the directory.

## Output Structure

For a Markdown file named `doc.md` with 3 Mermaid diagrams:

```
doc.md
doc/
├── 001.svg
├── 002.svg
└── 003.svg
```

The Markdown file will be updated with links after each Mermaid block:

```markdown
```mermaid
flowchart TD
    A --> B
```

<!-- mermaid-svg-link-begin -->
[打开 Mermaid SVG](./doc/001.svg)
<!-- mermaid-svg-link-end -->
```

## Script Location

The main script is bundled in this skill's `scripts/` directory:
- `scripts/md_mermaid_to_svg.py`
