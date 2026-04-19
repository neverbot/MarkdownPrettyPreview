"""
MarkdownPrettyPreview
=====================

Sublime Text plugin that opens a read-only, prettified rendering of a
Markdown document in a sibling view. The preview updates live as the
source is edited.

Usage
-----
  * Command palette: "Markdown Pretty Preview: Open"
  * Default keybinding (over a Markdown buffer): super+alt+m on macOS,
    ctrl+alt+m on Linux/Windows.

Rendering pipeline
------------------
Sublime can't render HTML-quality Markdown inline. Phantoms use minihtml
which lacks a usable table renderer, so instead we transform the source
into a heavier monospace form (Unicode box drawing for tables and code
blocks, banner lines for code fences, checkboxes for task items, etc.)
and show that in a plain text buffer with a custom sublime-syntax that
colors it like Markdown.

Styling inline formatting (bold/italic/code/link/strike)
--------------------------------------------------------
``view.add_regions`` can color text but can't apply font styles
(italic/bold). The only way to get italic/bold in our rendering is to
route the text through a sublime-syntax scope. So the transform strips
the Markdown markers (``**`` / ``*`` / ``_`` / ``~~`` / `` ` `` /
``[label](url)``) and wraps each formatted run with a pair of zero-width
Unicode sentinel chars. The companion ``MarkdownPrettyPreview.sublime-
syntax`` matches those sentinels and pushes into scoped contexts, which
the color scheme renders with both colors AND font styles.

Privacy
-------
This plugin runs entirely locally. It does not open network connections
or read files outside the source view it was opened against.
"""

import sublime
import sublime_plugin
import re

PREVIEW_OF = "mpp_preview_of"
HAS_PREVIEW = "mpp_has_preview"
SETTINGS_FILE = "MarkdownPrettyPreview.sublime-settings"
PREVIEW_SYNTAX = "Packages/MarkdownPrettyPreview/MarkdownPrettyPreview.sublime-syntax"

# Zero-width sentinels; must match the `variables` block in the syntax file.
# Distinct open/close chars per kind so the prototype (which matches OPEN
# chars to push into each scope) never collides with a context's own pop
# rule (which matches the matching CLOSE char). This lets us nest scopes
# correctly: bold inside italic produces a proper stack.
KIND_MARKS = {
    'bold':   ('\u200B', '\u200C'),  # ZWSP / ZWNJ
    'italic': ('\u200D', '\u2060'),  # ZWJ / WORD JOINER
    'strike': ('\u2061', '\u2062'),  # FUNCTION APPLICATION / INVISIBLE TIMES
    'code':   ('\u2063', '\u2064'),  # INVISIBLE SEPARATOR / INVISIBLE PLUS
    'link':   ('\u2066', '\u2069'),  # LRI / PDI (bidi, hidden via draw_unicode_bidi)
}


def get_setting(key, default):
    """Read a single key from the plugin's settings file, with fallback."""
    return sublime.load_settings(SETTINGS_FILE).get(key, default)


# ---------------------------------------------------------------------------
# Inline parsing: strip markers, remember where runs were.
# ---------------------------------------------------------------------------

INLINE_PATTERNS = [
    ("code",   re.compile(r'`([^`\n]+)`')),
    ("bold",   re.compile(r'\*\*([^\s*][^*]*?)\*\*')),
    ("bold",   re.compile(r'__([^\s_][^_]*?)__')),
    ("strike", re.compile(r'~~([^\s~][^~]*?)~~')),
    ("italic", re.compile(r'(?<!\w)\*([^\s*][^*]*?)\*(?!\w)')),
    ("italic", re.compile(r'(?<!\w)_([^\s_][^_]*?)_(?!\w)')),
    ("link",   re.compile(r'!?\[([^\]\n]+)\]\([^)\n]+\)')),
]


def parse_inline(text):
    """Strip Markdown inline markers and return ``(plain, runs)``.

    ``plain`` is the text with all markers removed; ``runs`` is a list of
    ``(start, end, kind)`` tuples in coordinates of ``plain``. The scanner
    repeatedly picks the earliest match across all patterns, so outer
    constructs (``**bold with *italic* inside**``) resolve before inner
    ones, yielding properly nested runs.
    """
    runs = []
    plain = text

    def map_pos(p, ms, cs, ce, me):
        # Translate a position in the pre-strip string to the post-strip
        # string. ``ms..me`` is the match range (e.g. ``**foo**``), and
        # ``cs..ce`` is the capture inside it (``foo``). Everything before
        # ms is unchanged; positions inside the capture shift by ``-(cs-ms)``;
        # everything after the match shifts by the total stripped length.
        if p <= ms:
            return p
        if p <= cs:
            return ms
        if p <= ce:
            return ms + (p - cs)
        if p <= me:
            return ms + (ce - cs)
        return p - ((cs - ms) + (me - ce))

    while True:
        best = None
        for kind, pat in INLINE_PATTERNS:
            m = pat.search(plain)
            if not m:
                continue
            if best is None or m.start() < best[0]:
                best = (m.start(), m.end(), m.start(1), m.end(1), kind)
        if best is None:
            return plain, runs

        ms, me, cs, ce, kind = best
        content = plain[cs:ce]
        new_runs = []
        for s, e, k in runs:
            ns = map_pos(s, ms, cs, ce, me)
            ne = map_pos(e, ms, cs, ce, me)
            if ne > ns:
                new_runs.append((ns, ne, k))
        new_runs.append((ms, ms + len(content), kind))
        runs = new_runs
        plain = plain[:ms] + content + plain[me:]


def inject_sentinels(text, runs):
    """Wrap each run in ``text`` with its kind's (open, close) sentinel pair.

    Events are ordered so the resulting string is a valid stack trace:
      - at a shared position, CLOSES come before OPENS (adjacent runs);
      - among simultaneous closes, INNER (larger start) closes first;
      - among simultaneous opens, OUTER (larger end) opens first.
    This keeps nesting like ``**bold *italic* tail**`` well-formed.
    """
    if not runs:
        return text
    events = []
    for s, e, k in runs:
        # Tuple: (pos, phase, tiebreak, kind, is_open).
        # phase: 0 = close (comes first at same pos), 1 = open.
        # Close tiebreak: -start → larger start (inner) sorts first.
        # Open tiebreak: -end → larger end (outer) sorts first.
        events.append((s, 1, -e, k, True))
        events.append((e, 0, -s, k, False))
    events.sort()

    parts = []
    last = 0
    for pos, _, _, k, is_open in events:
        parts.append(text[last:pos])
        o, c = KIND_MARKS[k]
        parts.append(o if is_open else c)
        last = pos
    parts.append(text[last:])
    return ''.join(parts)


# ---------------------------------------------------------------------------
# Word wrap with span tracking
# ---------------------------------------------------------------------------

def word_wrap_with_spans(text, width):
    """Greedy word-wrap preserving origin spans.

    Returns ``[(line_text, plain_start, plain_end), ...]`` where the span
    points back into the input. The span is needed by callers that have
    formatting runs in the same coordinate space and must restrict each
    run to the visible slice of each wrapped line.

    Words longer than ``width`` are force-broken at the character level.
    """
    if not text:
        return [("", 0, 0)]
    width = max(1, width)

    tokens = []
    i, n = 0, len(text)
    while i < n:
        j = i
        if text[i] == " ":
            while j < n and text[j] == " ":
                j += 1
            tokens.append(("space", i, j))
        else:
            while j < n and text[j] != " ":
                j += 1
            tokens.append(("word", i, j))
        i = j

    lines = []
    parts = []
    cur_len = 0

    def flush():
        nonlocal parts, cur_len
        while parts and text[parts[-1][1]] == " ":
            parts.pop()
        if not parts:
            parts = []
            cur_len = 0
            return
        line_text = "".join(text[s:e] for _, s, e in parts)
        lines.append((line_text, parts[0][1], parts[-1][2]))
        parts = []
        cur_len = 0

    for kind, s, e in tokens:
        if kind == "space":
            if parts:
                parts.append(("space", s, e))
                cur_len += (e - s)
            continue
        word_len = e - s
        if word_len > width:
            flush()
            w = s
            while w < e:
                chunk_end = min(w + width, e)
                lines.append((text[w:chunk_end], w, chunk_end))
                w = chunk_end
            continue
        if cur_len + word_len > width:
            flush()
            parts.append(("word", s, e))
            cur_len = word_len
        else:
            parts.append(("word", s, e))
            cur_len += word_len
    flush()
    return lines or [("", 0, 0)]


def restrict_runs(runs, start, end):
    """Clip formatting runs to ``[start, end)`` and rebase to 0.

    Used when we wrap a line: each visual line needs its own local copy
    of the runs so sentinels are balanced within that line (scopes must
    not straddle newlines in the rendered output).
    """
    out = []
    for s, e, k in runs:
        ns = max(s, start)
        ne = min(e, end)
        if ne > ns:
            out.append((ns - start, ne - start, k))
    return out


# ---------------------------------------------------------------------------
# Line-level transforms
# ---------------------------------------------------------------------------

SEPARATOR_RE = re.compile(r'^\s*\|?\s*:?-{3,}:?(\s*\|\s*:?-{3,}:?)*\s*\|?\s*$')
FENCE_RE = re.compile(r'^\s*(```|~~~)')
FENCE_OPEN_RE = re.compile(r'^\s*(```|~~~)\s*(.*)$')
HEADING_RE = re.compile(r'^(#{1,6})\s+(.*?)\s*#*\s*$')
HR_RE = re.compile(r'^\s*(\*\s*\*\s*\*[\s*]*|-\s*-\s*-[\s-]*|_\s*_\s*_[\s_]*)\s*$')
TASK_RE = re.compile(r'^(\s*)[-*+]\s+\[([ xX])\]\s*(.*)$')
BLOCKQUOTE_RE = re.compile(r'^(\s*)((?:>\s?)+)(.*)$')


def split_row(line):
    """Split a Markdown table row into a list of trimmed cell strings.

    Leading/trailing pipes are stripped so ``| a | b |`` and ``a | b`` both
    yield ``['a', 'b']``. Does not handle escaped pipes inside cells (rare
    in practice).
    """
    s = line.strip()
    if s.startswith('|'):
        s = s[1:]
    if s.endswith('|'):
        s = s[:-1]
    return [c.strip() for c in s.split('|')]


def parse_alignments(separator_line):
    """Map a Markdown table separator row to per-column alignment strings.

    Reads the ``:---``, ``:---:``, ``---:`` conventions; defaults to left.
    """
    out = []
    for c in split_row(separator_line):
        left = c.startswith(':')
        right = c.endswith(':')
        if left and right:
            out.append('center')
        elif right:
            out.append('right')
        else:
            out.append('left')
    return out


def wrap_line_with_prefix(plain, runs, max_width, first_prefix='', cont_prefix=None):
    """Wrap ``plain`` + formatting runs to ``max_width``, emitting prefixed lines.

    Used for any block that needs a leading decoration on its first line
    (e.g. ``▢ ``, ``▌ ``) and a different continuation indent on wrapped
    lines. Each visual line gets its own restricted copy of the runs so
    sentinels open and close within the same line.
    """
    if cont_prefix is None:
        cont_prefix = first_prefix
    avail = max(1, max_width - max(len(first_prefix), len(cont_prefix)))

    if len(plain) <= avail:
        return [first_prefix + inject_sentinels(plain, runs)]

    out = []
    for i, (ltxt, ps, pe) in enumerate(word_wrap_with_spans(plain, avail)):
        prefix = first_prefix if i == 0 else cont_prefix
        local = restrict_runs(runs, ps, pe)
        out.append(prefix + inject_sentinels(ltxt, local))
    return out


def transform_heading(line, max_width):
    """Render an ATX heading (``# title``).

    H1/H2 get a matching underline (``━`` / ``─``). Deeper levels render
    without an underline since most color schemes distinguish them by
    size/weight in the scope ``markup.heading.markdown``. Returns a list
    of output lines or ``None`` if the line is not a heading.
    """
    m = HEADING_RE.match(line)
    if not m:
        return None
    level = len(m.group(1))
    if level > 2:
        plain, runs = parse_inline(line)
        return wrap_line_with_prefix(plain, runs, max_width)
    title_plain, title_runs = parse_inline(m.group(2))
    title_lines = wrap_line_with_prefix(title_plain, title_runs, max_width)
    # Underline length mirrors the visible title width but never exceeds the
    # viewport -- so long H1/H2 titles don't force horizontal scroll.
    underline_width = max(3, min(len(title_plain), max_width))
    underline = ('━' if level == 1 else '─') * underline_width
    return title_lines + [underline]


def transform_task(line, max_width):
    """Render a GFM task list item (``- [ ] ...`` / ``- [x] ...``).

    The list marker and checkbox square are replaced with ``▢`` / ``▣``,
    continuation lines align under the task text. Returns ``None`` if the
    line is not a task item.
    """
    m = TASK_RE.match(line)
    if not m:
        return None
    indent, mark, rest = m.group(1), m.group(2), m.group(3)
    box = '▣' if mark in ('x', 'X') else '▢'
    if not rest:
        return [indent + box]
    first = indent + box + ' '
    cont = indent + '  '
    rest_plain, rest_runs = parse_inline(rest)
    return wrap_line_with_prefix(rest_plain, rest_runs, max_width, first, cont)


def transform_blockquote(line, max_width):
    """Render a blockquote line (``> ...``).

    Each ``>`` marker becomes a ``▌`` bar. Nesting is indicated by repeating
    the bar (``▌ ▌ ``). Returns ``None`` if the line is not a blockquote.
    """
    m = BLOCKQUOTE_RE.match(line)
    if not m:
        return None
    indent, markers, rest = m.group(1), m.group(2), m.group(3)
    depth = markers.count('>')
    prefix = indent + ('▌ ' * depth)
    rest_plain, rest_runs = parse_inline(rest)
    return wrap_line_with_prefix(rest_plain, rest_runs, max_width, prefix)


def transform_hr(line, width):
    """Render ``---`` / ``***`` / ``___`` as a full-viewport ``─`` separator.

    Returns ``None`` if the line is not a horizontal rule.
    """
    if HR_RE.match(line):
        return '─' * width
    return None


def render_code_block(lang, code_lines, max_width, opts=None):
    """Render a fenced code block as double-line banners above and below the
    code, with no side borders. The companion sublime-syntax matches the top
    banner, embeds the language's scope continuously, and escapes on the
    bottom banner -- so multi-line constructs (triple-quoted strings, block
    comments) tokenize correctly across line boundaries.

    Double-line ═ distinguishes code blocks from single-line table borders
    and HR separators.
    """
    # One leading space on every code line for visual air; banners extend
    # to cover it. Force-wrap budget shrinks by the same amount.
    opts = opts or {}
    line_prefix = ' ' if opts.get('code_block_leading_space', True) else ''
    wrap_budget = max(10, max_width - len(line_prefix))

    wrapped = []
    for raw in code_lines:
        if not raw:
            wrapped.append('')
            continue
        if len(raw) <= wrap_budget:
            wrapped.append(raw)
            continue
        pos = 0
        while pos < len(raw):
            wrapped.append(raw[pos:pos + wrap_budget])
            pos += wrap_budget

    longest_code = max([len(line) for line in wrapped] or [0])
    content_width = longest_code + len(line_prefix)
    if lang:
        title = '╡ ' + lang + ' ╞'
        lead = 3
        min_title_inner = lead + len(title) + 3
        inner_needed = max(content_width, min_title_inner)
        inner = min(max(6, inner_needed), max_width - 2)
        trailing = max(3, inner - lead - len(title))
        middle = '═' * lead + title + '═' * trailing
        if len(middle) > inner:
            middle = middle[:inner]
        top = '╒' + middle + '╕'
    else:
        inner = min(max(6, content_width), max_width - 2)
        top = '╒' + '═' * inner + '╕'
    bottom = '╘' + '═' * inner + '╛'

    out = [top, '']
    for wl in wrapped:
        out.append(line_prefix + wl if wl else '')
    out.append('')
    out.append(bottom)
    return out


# ---------------------------------------------------------------------------
# Table rendering with per-visual-line sentinels
# ---------------------------------------------------------------------------

def allocate_column_widths(naturals, content_budget, min_width=3):
    """Distribute ``content_budget`` characters across table columns.

    ``naturals`` are the columns' ideal widths (length of the widest cell).
    If everything fits we return that. Otherwise we give each column at
    least ``min_width``, then hand out the remaining budget proportionally
    to how much each column exceeded ``min_width`` (so a very long column
    gets more of the leftover than a short one). Any stray chars from
    integer division land on the widest columns first.
    """
    n = len(naturals)
    if n == 0:
        return []
    if sum(naturals) <= content_budget:
        return list(naturals)
    min_width = max(1, min(min_width, content_budget // n))
    remaining = content_budget - min_width * n
    if remaining < 0:
        return [max(1, content_budget // n)] * n
    excess = [max(0, w - min_width) for w in naturals]
    total_excess = sum(excess)
    if total_excess == 0:
        widths = [min_width] * n
    else:
        widths = [min_width + (remaining * e) // total_excess for e in excess]
    leftover = content_budget - sum(widths)
    order = sorted(range(n), key=lambda i: -naturals[i])
    j = 0
    while leftover > 0:
        widths[order[j % n]] += 1
        leftover -= 1
        j += 1
    return widths


def render_box_table(header_cells, row_cells, aligns, max_width, opts=None):
    """Render a Markdown table as a full Unicode box with wrapped cells.

    Cells come in as ``(plain, runs)`` tuples so that inline formatting
    (bold/italic/code/link/strike) is preserved across wrap boundaries.
    Padding is computed from the PLAIN length (not the sentinel-injected
    string) so columns stay aligned.

    ``opts['table_row_spacing']`` (default True) inserts an empty row
    between each pair of data rows for breathing room.
    """
    col_count = len(header_cells)
    row_cells = [r + [("", [])] * (col_count - len(r)) for r in row_cells]
    aligns = (aligns + ['left'] * col_count)[:col_count]

    naturals = [len(header_cells[j][0]) for j in range(col_count)]
    for row in row_cells:
        for j in range(col_count):
            naturals[j] = max(naturals[j], len(row[j][0]))

    overhead = 3 * col_count + 1
    content_budget = max(col_count, max_width - overhead)
    widths = allocate_column_widths(naturals, content_budget)

    def hline(left, mid, right, fill='─'):
        return left + mid.join(fill * (w + 2) for w in widths) + right

    def render_row(cells):
        per_cell = []  # per column: list of (plain_line, sentineled_line)
        for j in range(col_count):
            plain, runs = cells[j]
            spans = word_wrap_with_spans(plain, widths[j])
            lines = []
            for ltxt, ps, pe in spans:
                local = restrict_runs(runs, ps, pe)
                lines.append((ltxt, inject_sentinels(ltxt, local)))
            per_cell.append(lines)
        height = max(len(c) for c in per_cell) or 1
        for j in range(col_count):
            while len(per_cell[j]) < height:
                per_cell[j].append(("", ""))

        out = []
        for k in range(height):
            parts = ["│"]
            for j in range(col_count):
                plain_cell, sent_cell = per_cell[j][k]
                total_pad = max(0, widths[j] - len(plain_cell))
                if aligns[j] == 'right':
                    left_p, right_p = total_pad, 0
                elif aligns[j] == 'center':
                    left_p = total_pad // 2
                    right_p = total_pad - left_p
                else:
                    left_p, right_p = 0, total_pad
                parts.append(' ' + (' ' * left_p) + sent_cell + (' ' * right_p) + ' ')
                parts.append('│')
            out.append(''.join(parts))
        return out

    opts = opts or {}
    spacing = bool(opts.get('table_row_spacing', True))
    empty_row = [("", [])] * col_count

    out = [hline('┌', '┬', '┐')]
    out.extend(render_row(header_cells))
    out.append(hline('├', '┼', '┤'))
    for idx, row in enumerate(row_cells):
        if spacing and idx > 0:
            out.extend(render_row(empty_row))
        out.extend(render_row(row))
    out.append(hline('└', '┴', '┘'))
    return out


# ---------------------------------------------------------------------------
# Top-level transform
# ---------------------------------------------------------------------------

def transform_markdown(text, max_width=80, opts=None):
    """Convert Markdown source to the prettified monospace preview form.

    Walks the input line by line dispatching to the block-level transforms
    (fence, table, hr, heading, task, blockquote) and falling back to a
    plain paragraph. Multi-line constructs (code fences, tables) consume
    multiple input lines per iteration.

    ``max_width`` is the target viewport width in characters; everything
    wraps or truncates to fit. ``opts`` is a dict of rendering preferences
    (see ``update_preview`` for the keys).
    """
    lines = text.split('\n')
    out = []
    i = 0

    while i < len(lines):
        line = lines[i]

        fence_m = FENCE_OPEN_RE.match(line)
        if fence_m:
            fence_char = fence_m.group(1)
            info = fence_m.group(2).strip()
            lang = info.split()[0] if info else ''
            i += 1
            code_lines = []
            while i < len(lines):
                if lines[i].lstrip().startswith(fence_char):
                    i += 1
                    break
                code_lines.append(lines[i])
                i += 1
            out.extend(render_code_block(lang, code_lines, max_width, opts))
            continue

        if (
            '|' in line
            and i + 1 < len(lines)
            and SEPARATOR_RE.match(lines[i + 1])
        ):
            header_cells = [parse_inline(c) for c in split_row(line)]
            aligns = parse_alignments(lines[i + 1])
            i += 2
            row_cells = []
            while (
                i < len(lines)
                and lines[i].strip()
                and '|' in lines[i]
                and not FENCE_RE.match(lines[i])
            ):
                row_cells.append([parse_inline(c) for c in split_row(lines[i])])
                i += 1
            out.extend(render_box_table(header_cells, row_cells, aligns, max_width, opts))
            continue

        hr = transform_hr(line, max_width)
        if hr is not None:
            out.append(hr)
            i += 1
            continue

        heading = transform_heading(line, max_width)
        if heading is not None:
            out.extend(heading)
            i += 1
            continue

        task = transform_task(line, max_width)
        if task is not None:
            out.extend(task)
            i += 1
            continue

        bq = transform_blockquote(line, max_width)
        if bq is not None:
            out.extend(bq)
            i += 1
            continue

        plain, runs = parse_inline(line)
        out.extend(wrap_line_with_prefix(plain, runs, max_width))
        i += 1

    return '\n'.join(out)


# ---------------------------------------------------------------------------
# View wiring
# ---------------------------------------------------------------------------

def find_view_by_id(view_id):
    """Locate a view by id across all windows, or ``None`` if it's gone."""
    for window in sublime.windows():
        for v in window.views():
            if v.id() == view_id:
                return v
    return None


def ensure_two_column_layout(window):
    """Switch the window to a 2-column layout if it only has one group.

    Used when the user prefers the preview in a separate group and the
    window is still single-column. Existing multi-column layouts are
    left untouched.
    """
    layout = window.layout()
    if len(layout.get("cols", [])) >= 3:
        return
    window.set_layout({
        "cols": [0.0, 0.5, 1.0],
        "rows": [0.0, 1.0],
        "cells": [[0, 0, 1, 1], [1, 0, 2, 1]],
    })


def pick_preview_group(window, source_view):
    """Choose which group the preview view should live in.

    Prefers the group immediately to the right of the source; falls back
    to group 0 if the source is in the rightmost group (and wraps around
    safely when the source is itself in group 0).
    """
    source_group, _ = window.get_view_index(source_view)
    num_groups = window.num_groups()
    if num_groups < 2:
        return 1
    target = source_group + 1
    if target >= num_groups:
        target = 0 if source_group != 0 else 1
    return target


def viewport_char_width(view, fallback=80):
    """Estimate the preview's usable width in monospace characters.

    Divides the viewport pixel width by the font's em width, minus a small
    gutter to avoid words hugging the scrollbar edge. Falls back to 80 if
    the view hasn't been laid out yet (em_width == 0).
    """
    try:
        px_w, _ = view.viewport_extent()
        em = view.em_width()
        if em and em > 0 and px_w and px_w > 0:
            return max(20, int(px_w / em) - 2)
    except Exception:
        pass
    return fallback


def update_preview(source_view, preview_view):
    """Re-render the preview from the current source content.

    Reads the source buffer, measures the preview's viewport, gathers user
    rendering options, and runs the transform. The preview is briefly made
    writable to allow the replacement, then locked back to read-only.
    """
    content = source_view.substr(sublime.Region(0, source_view.size()))
    max_width = viewport_char_width(preview_view)
    opts = {
        'code_block_leading_space': get_setting('code_block_leading_space', True),
        'table_row_spacing': get_setting('table_row_spacing', True),
    }
    transformed = transform_markdown(content, max_width=max_width, opts=opts)
    preview_view.set_read_only(False)
    preview_view.run_command("mpp_replace_content", {"content": transformed})
    preview_view.set_read_only(True)
    _last_viewport_width[preview_view.id()] = max_width


class MppReplaceContentCommand(sublime_plugin.TextCommand):
    """Replace the whole preview buffer with new content, preserving the caret.

    A plain ``view.replace`` of the full buffer leaves the entire new text
    selected, which is disruptive on every debounced update. We capture the
    caret position beforehand and restore a zero-length selection after.
    """

    def run(self, edit, content):
        old_pos = self.view.sel()[0].begin() if len(self.view.sel()) else 0
        self.view.replace(edit, sublime.Region(0, self.view.size()), content)
        clamped = min(old_pos, self.view.size())
        sel = self.view.sel()
        sel.clear()
        sel.add(sublime.Region(clamped, clamped))


class OpenMarkdownPrettyPreviewCommand(sublime_plugin.WindowCommand):
    """Open (or focus existing) preview for the active Markdown view.

    If a preview already exists for the current view, just focus it.
    Otherwise, create a new scratch view, wire up the source <-> preview
    association via view settings, apply view-local settings that keep the
    zero-width sentinels invisible, and trigger an initial render.
    """

    def run(self):
        source_view = self.window.active_view()
        if not source_view:
            return

        existing_id = source_view.settings().get(HAS_PREVIEW)
        if existing_id:
            existing = find_view_by_id(existing_id)
            if existing:
                self.window.focus_view(existing)
                return

        same_group = bool(get_setting("preview_in_same_group", True))
        if same_group:
            source_group, _ = self.window.get_view_index(source_view)
            target_group = source_group
        else:
            ensure_two_column_layout(self.window)
            target_group = pick_preview_group(self.window, source_view)

        self.window.focus_group(target_group)
        preview_view = self.window.new_file()
        preview_view.set_scratch(True)
        source_name = source_view.file_name() or "untitled"
        preview_view.set_name("Preview: " + source_name.split('/')[-1])
        preview_view.assign_syntax(PREVIEW_SYNTAX)

        preview_view.settings().set("word_wrap", False)
        preview_view.settings().set("spell_check", False)
        preview_view.settings().set("gutter", False)
        # Stop Sublime from rendering our zero-width sentinels as <0xNNNN>
        # placeholders. These settings only affect the preview view.
        preview_view.settings().set("draw_unicode_white_space", "none")
        preview_view.settings().set("draw_white_space", "none")
        preview_view.settings().set("draw_unicode_bidi", False)

        preview_view.settings().set(PREVIEW_OF, source_view.id())
        source_view.settings().set(HAS_PREVIEW, preview_view.id())

        update_preview(source_view, preview_view)
        preview_view.set_read_only(True)

        # In same-group mode source and preview share one pane, so leave the
        # preview tab active (the user just asked to see it). In new-group
        # mode both are visible side-by-side, so return focus to the source
        # for continued editing.
        if same_group:
            self.window.focus_view(preview_view)
        else:
            self.window.focus_view(source_view)


_debounce_epochs = {}
_last_viewport_width = {}


class MppListener(sublime_plugin.EventListener):
    """Wires source buffer edits and lifecycle events to preview updates."""

    def on_modified_async(self, view):
        # Debounced rebuild. Each edit stamps a monotonic epoch; the
        # scheduled callback only fires if no newer edit has superseded it.
        preview_id = view.settings().get(HAS_PREVIEW)
        if not preview_id:
            return
        source_id = view.id()
        epoch = view.change_count()
        _debounce_epochs[source_id] = epoch

        def fire():
            if _debounce_epochs.get(source_id) != epoch:
                return
            preview = find_view_by_id(preview_id)
            source = find_view_by_id(source_id)
            if preview and source:
                update_preview(source, preview)

        sublime.set_timeout_async(fire, get_setting("debounce_ms", 100))

    def on_activated_async(self, view):
        # When the preview regains focus, re-render if the viewport size
        # has changed since we last drew (e.g. user resized the window or
        # dragged the group divider).
        source_id = view.settings().get(PREVIEW_OF)
        if not source_id:
            return
        current = viewport_char_width(view)
        last = _last_viewport_width.get(view.id())
        if last == current:
            return
        source = find_view_by_id(source_id)
        if source:
            update_preview(source, view)

    def on_close(self, view):
        # Closing the source closes its preview too (and vice versa cleans
        # up the source's HAS_PREVIEW marker), keeping the pair consistent.
        preview_id = view.settings().get(HAS_PREVIEW)
        if preview_id:
            preview = find_view_by_id(preview_id)
            if preview:
                win = preview.window()
                if win:
                    win.focus_view(preview)
                    win.run_command("close_file")
        source_id = view.settings().get(PREVIEW_OF)
        if source_id:
            source = find_view_by_id(source_id)
            if source:
                source.settings().erase(HAS_PREVIEW)
        _debounce_epochs.pop(view.id(), None)
        _last_viewport_width.pop(view.id(), None)


_POLL_INTERVAL_MS = 500


def _poll_viewport_sizes():
    """Periodic check so live resizes redraw without needing focus change.

    ``on_activated_async`` only fires when the preview regains focus, but
    users often resize the window while the source is focused. A cheap
    poll (default 500 ms) re-renders any preview whose viewport width has
    changed, then reschedules itself.
    """
    for preview_id, last_w in list(_last_viewport_width.items()):
        preview = find_view_by_id(preview_id)
        if not preview:
            _last_viewport_width.pop(preview_id, None)
            continue
        current = viewport_char_width(preview)
        if current == last_w:
            continue
        source_id = preview.settings().get(PREVIEW_OF)
        if source_id is None:
            continue
        source = find_view_by_id(source_id)
        if source:
            update_preview(source, preview)
    sublime.set_timeout_async(_poll_viewport_sizes, _POLL_INTERVAL_MS)


def plugin_loaded():
    """Sublime calls this after the package is loaded; kicks off the poll."""
    sublime.set_timeout_async(_poll_viewport_sizes, _POLL_INTERVAL_MS)
