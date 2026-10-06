"""Unit tests for the pure-text transform (no Sublime Text needed).

Run from the package root:  python3 -m unittest discover -s tests
"""

import os
import sys
import types
import unittest

# Minimal stand-ins so the plugin module imports outside Sublime Text.
sys.modules.setdefault('sublime', types.ModuleType('sublime'))
_sp = types.ModuleType('sublime_plugin')
_sp.TextCommand = _sp.WindowCommand = _sp.EventListener = object
sys.modules.setdefault('sublime_plugin', _sp)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import MarkdownPrettyPreview as mpp  # noqa: E402

HIDDEN = {ord(c): None for pair in mpp.KIND_MARKS.values() for c in pair}
HIDDEN[ord(mpp.HEADING_MARK)] = None
HIDDEN[ord(mpp.STRIKE_OVERLAY)] = None


def visible(text):
    """What the reader sees: drop sentinels and overlays."""
    return text.translate(HIDDEN)


def render(md, width=60):
    return mpp.transform_markdown(md, width)


class InlineTests(unittest.TestCase):

    def test_strike_gets_overlay_per_char(self):
        out = render('~~gone~~ x')
        o, c = mpp.KIND_MARKS['strike']
        s = mpp.STRIKE_OVERLAY
        self.assertEqual(out, o + 'g' + s + 'o' + s + 'n' + s + 'e' + s + c + ' x')

    def test_strike_overlay_inside_nested_run(self):
        out = render('~~a **b** c~~')
        self.assertEqual(visible(out), 'a b c')
        # every visible char is struck, including the bold one
        self.assertEqual(out.count(mpp.STRIKE_OVERLAY), 5)

    def test_code_content_is_literal(self):
        self.assertEqual(mpp.parse_inline('`__init__` method'),
                         ('__init__ method', [(0, 8, 'code')]))
        self.assertEqual(mpp.parse_inline('run `ls *.py *.md` now'),
                         ('run ls *.py *.md now', [(4, 16, 'code')]))

    def test_emphasis_closing_inside_code_is_ignored(self):
        plain, runs = mpp.parse_inline('*a `b* c`')
        self.assertEqual(plain, '*a b* c')
        self.assertEqual(runs, [(3, 7, 'code')])

    def test_bold_around_code(self):
        plain, runs = mpp.parse_inline('**x `y` z**')
        self.assertEqual(plain, 'x y z')
        self.assertEqual(sorted(runs), [(0, 5, 'bold'), (2, 3, 'code')])

    def test_backslash_escapes(self):
        self.assertEqual(mpp.parse_inline(r'\*not italic\* ok'), ('*not italic* ok', []))

    def test_escapes_not_applied_in_code(self):
        self.assertEqual(mpp.parse_inline(r'`a\*b`')[0], r'a\*b')


class BlockTests(unittest.TestCase):

    def test_heading_keeps_trailing_hash_without_space(self):
        lines = visible(render('# Learn C#')).split('\n')
        self.assertEqual(lines[0], 'Learn C#')

    def test_heading_closing_sequence_removed(self):
        self.assertEqual(visible(render('## Title ##')).split('\n')[0], 'Title')

    def test_heading_lines_carry_marker(self):
        for md in ('# One', '## Two', '### Three'):
            first = render(md).split('\n')[0]
            self.assertTrue(first.startswith(mpp.HEADING_MARK), md)

    def test_h3_wrapped_lines_all_marked(self):
        lines = render('### ' + 'word ' * 30, 40).split('\n')
        self.assertGreater(len(lines), 1)
        self.assertTrue(all(ln.startswith(mpp.HEADING_MARK) for ln in lines))

    def test_paragraph_indent_kept_when_wrapping(self):
        lines = render('    ' + 'word ' * 30, 40).split('\n')
        self.assertGreater(len(lines), 1)
        self.assertTrue(all(ln.startswith('    w') for ln in lines))

    def test_list_item_hanging_indent(self):
        lines = render('  - ' + 'word ' * 30, 40).split('\n')
        self.assertTrue(lines[0].startswith('  - word'))
        self.assertTrue(all(ln.startswith('    word') for ln in lines[1:]))

    def test_ordered_list_hanging_indent(self):
        lines = render('10. ' + 'word ' * 30, 40).split('\n')
        self.assertTrue(lines[0].startswith('10. word'))
        self.assertTrue(all(ln.startswith('    word') for ln in lines[1:]))

    def test_four_backtick_fence_contains_three(self):
        out = render('````md\n```py\nx\n```\n````')
        self.assertEqual(out.count('╒'), 1)
        self.assertIn(' ```py', out)

    def test_fence_lang_lowercased(self):
        self.assertIn('╡ python ╞', render('```Python\nx\n```'))

    def test_table_escaped_pipe_and_code_pipe(self):
        self.assertEqual(mpp.split_row(r'| a \| b | `x|y` |'), [r'a \| b', '`x|y`'])
        out = visible(render('| a | b |\n|---|---|\n| `x|y` | p \\| q |'))
        self.assertIn('x|y', out)
        self.assertIn('p | q', out)


if __name__ == '__main__':
    unittest.main()
