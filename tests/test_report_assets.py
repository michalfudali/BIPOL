"""Offline typesetting must keep the report self-contained."""
from calculations.report_assets import math_assets
from pathlib import Path


def test_math_assets_embed_every_font_face():
    assets = math_assets()
    assert assets['css'].count('data:font/woff2;base64,') >= 20
    assert 'url(fonts/' not in assets['css']
    assert assets['css'].count('@font-face') == assets['css'].count('data:font/woff2;base64,')
    assert '</script' not in assets['katex']


def test_report_templates_do_not_contain_corrupted_tex_escape_characters():
    root = Path(__file__).resolve().parents[1] / 'templates'
    for name in ['project_report.html', 'trend_report.html', 'report.html',
                 *[str(p.relative_to(root)) for p in (root / 'reports').glob('*.html')]]:
        text = (root / name).read_text(encoding='utf-8')
        assert not any(ord(c) < 32 and c not in '\n\t' for c in text), name
        assert '\night' not in text
        assert '\text' not in text  # A tab followed by "ext" is not a TeX command.
