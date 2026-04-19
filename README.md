# MarkdownPrettyPreview

A Sublime Text 4 plugin that opens a read-only, prettified rendering of a
Markdown document in a sibling view. The preview updates live as the
source is edited.

Headings get underlines, task lists become `▢` / `▣` boxes, blockquotes
become `▌` bars, tables are drawn with Unicode box characters and
word-wrap cells, fenced code blocks are framed between `╒═╡ lang ╞═╕` /
`╘═══╛` banners with per-language syntax highlighting inside.

## Features

- Real-time debounced preview
- Proper Markdown inline formatting: **bold**, *italic*, ~~strikethrough~~,
  `inline code`, [links](https://example.com) — with actual italic/bold
  font styles (not just colors)
- Unicode box tables with per-cell word wrap, alignment, and inline
  formatting preserved across wrap boundaries
- Fenced code blocks with continuous syntax highlighting for the
  embedded language: python, js, ts, c, c++, rust, go, ruby, java,
  php, shell/bash, html, css/scss, json, yaml/yml, sql (generic
  fallback for the rest)
- Task lists, blockquotes (nested), horizontal rules, ATX headings (H1–H6)
- Re-renders on viewport resize so content always fits the pane
- Opens either as a tab in the same group (VSCode-style toggle) or as a
  side-by-side view in a separate group

## Installation

### Package Control

Once listed on the Package Control channel:

1. Open the command palette
2. `Package Control: Install Package`
3. `MarkdownPrettyPreview`

### Manual

```sh
cd "$HOME/Library/Application Support/Sublime Text/Packages"   # macOS
# or "%APPDATA%\Sublime Text\Packages" on Windows,
# or "$HOME/.config/sublime-text/Packages" on Linux
git clone https://github.com/neverbot/MarkdownPrettyPreview.git
```

## Usage

With a Markdown file active:

- **Command palette**: `Markdown Pretty Preview: Open`
- **Keybinding**: `super+alt+m` (macOS) / `ctrl+alt+m` (Linux/Windows)

Running the command again focuses the existing preview. Closing either
the source or the preview cleans up the pair.

## Settings

`Preferences → Package Settings → Markdown Pretty Preview → Settings`

| Key                         | Default | Description                                                                                                   |
| --------------------------- | ------- | ------------------------------------------------------------------------------------------------------------- |
| `debounce_ms`               | `100`   | Milliseconds to wait after a change before re-rendering.                                                      |
| `preview_in_same_group`     | `true`  | `true`: preview opens as a sibling tab; `false`: preview opens in a separate group, forcing a 2-column layout. |
| `code_block_leading_space`  | `true`  | Prefix each code line with one space for visual air. Banners extend to cover it.                              |
| `table_row_spacing`         | `true`  | Insert an empty row between data rows in tables for breathing room.                                           |

## Caveats

- The preview uses zero-width Unicode sentinels (`U+200B`, `U+200C`,
  `U+200D`, `U+2060`, `U+2061`–`U+2064`, `U+2066`, `U+2069`) to mark
  inline formatting runs. If you copy text from the preview to another
  place those characters will come along — copy from the source instead.
- Force-wrapping of very long code lines happens at the character level,
  so a literal split across a wrap boundary may tokenize oddly. Cosmetic
  only.
- Tables with `|` escaped inside cells (`\|`) are not yet supported.

## License

MIT — see [LICENSE](LICENSE).
