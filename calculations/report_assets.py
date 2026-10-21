"""Portable mathematical typesetting, including fonts, without a CDN dependency."""
import base64
from functools import lru_cache
from pathlib import Path
import re


@lru_cache(maxsize=1)
def math_assets():
    root = Path(__file__).resolve().parents[1] / 'static' / 'vendor' / 'katex'
    css = (root / 'katex.min.css').read_text(encoding='utf-8')
    # WOFF2 is supported by the application's target browsers; embed it once per face.
    def font_source(match):
        encoded = base64.b64encode((root / 'fonts' / match[1]).read_bytes()).decode('ascii')
        return f'src:url(data:font/woff2;base64,{encoded}) format("woff2")'
    css = re.sub(r'src:url\(fonts/([^)]*\.woff2)\)\s*format\("woff2"\)[^;}]*', font_source, css)
    return {'css': css,
            'katex': (root / 'katex.min.js').read_text(encoding='utf-8').replace('</script', '<\\/script'),
            'render': (root / 'contrib' / 'auto-render.min.js').read_text(encoding='utf-8').replace('</script', '<\\/script')}
