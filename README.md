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
  font styles (not just colors). Color schemes can't strike text, so
  strikethrough is drawn with a combining overlay (`U+0336`) on each char
- Code spans are literal (`__init__` stays as is) and backslash escapes
  (`\*not italic\*`) are honored
- Unicode box tables with per-cell word wrap, alignment, and inline
  formatting preserved across wrap boundaries; `\|` and pipes inside code
  spans don't split cells
- Fenced code blocks (``` or ~~~, any fence length) with continuous syntax
  highlighting for the embedded language: python, js, jsx, ts, tsx, c,
  c++, c#, rust, go, ruby, java, php, lua, shell/bash, html, xml,
  css/scss, json, yaml/yml, sql, diff (plain code block for the rest)
- Task lists, bullet and ordered lists with hanging indent on wrap,
  blockquotes (nested), horizontal rules, ATX headings (H1–H6)
- Re-renders on viewport resize so content always fits the pane, keeping
  the scroll position
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

Running the command again focuses the existing preview; running it from
the preview jumps back to the source. Closing either the source or the
preview cleans up the pair. Previews restored with the session are
re-attached to their source file (or closed if it is no longer open).

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
  `U+200D`, `U+2060`, `U+2061`–`U+2064`, `U+2066`, `U+2069`, `U+FEFF`) to
  mark inline formatting runs and headings, plus `U+0336` overlays for
  strikethrough. If you copy text from the preview to another place
  those characters will come along — copy from the source instead.
- How the strikethrough overlay looks depends on the font.
- Force-wrapping of very long code lines happens at the character level,
  so a literal split across a wrap boundary may tokenize oddly. Cosmetic
  only.
- Wide characters (CJK, emoji) count as one column, so tables containing
  them may misalign.

## Development

The text transform is pure Python and has unit tests that run outside
Sublime Text:

```sh
python3 -m unittest discover -s tests
```

## License

MIT — see [LICENSE](LICENSE).
