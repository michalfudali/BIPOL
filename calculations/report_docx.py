"""Sprawozdanie jako edytowalny plik Word (DOCX).

Wejściem jest HTML dokumentu z okna podglądu, razem z poprawkami autora. Przeglądarka zastępuje
w nim wykresy SVG obrazami PNG (data URL) i zwykle także wzory KaTeX ich zapisem MathML (<math>);
surowy KaTeX też jest rozpoznawany. Wzory trafiają do Worda jako równania OMML (edytor równań),
numery tabel, rysunków i wzorów jako pola SEQ, a numer strony jako pole PAGE — po dopisaniu treści
w Wordzie numeracja się aktualizuje. Wystarcza biblioteka standardowa.
"""
import base64
import re
import struct
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from io import BytesIO

TEXT_WIDTH = 9638                    # twip: A4 (11906) minus marginesy 2 × 20 mm
TWIP_PER_MM = 1440 / 25.4
EMU_PER_MM = 36000
MAX_IMAGE_HEIGHT_MM = 225
NUMBER_COLUMN = 850                  # twip: kolumna numeru wzoru

VOID = frozenset('area base br col embed hr img input link meta source track wbr'.split())
SKIP = frozenset('button input select textarea script style template noscript dialog svg'.split())
BLOCK = frozenset('''address article aside blockquote caption dd details div dl dt figcaption figure footer form
    h1 h2 h3 h4 h5 h6 header hr li main nav ol p pre section summary table tbody td tfoot th thead tr ul'''.split())
HEADINGS = {'h1': 'Title', 'h2': 'Heading1', 'h3': 'Heading2', 'h4': 'Heading3', 'h5': 'Heading4', 'h6': 'Heading4'}
PARAGRAPH_CLASSES = (('calc-label', 'CalcLabel'), ('calc-note', 'CalcNote'), ('table-note', 'Small'),
                     ('small', 'Small'))
_INVALID_XML = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]')
_SPACES = re.compile('[ \t\n\r\f]+')
_DATA_URL = re.compile(r'data:image/(png|jpeg|jpg);base64,(.+)', re.S)

NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')


def esc(text):
    text = _INVALID_XML.sub('', str(text))
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


# ───────────────────────────── drzewo HTML ─────────────────────────────

class Node:
    __slots__ = ('tag', 'attrs', 'children')

    def __init__(self, tag, attrs=None):
        self.tag, self.attrs, self.children = tag, dict(attrs or {}), []

    def classes(self):
        return set((self.attrs.get('class') or '').split())

    def elements(self):
        return [c for c in self.children if isinstance(c, Node)]

    def text(self):
        return ''.join(c if isinstance(c, str) else c.text() for c in self.children)

    def find(self, test):
        for child in self.elements():
            if test(child):
                return child
            found = child.find(test)
            if found is not None:
                return found
        return None


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('#root')
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, ((k, v if v is not None else '') for k, v in attrs))
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, ((k, v if v is not None else '') for k, v in attrs)))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if data:
            self.stack[-1].children.append(data)


def parse_html(html):
    builder = _TreeBuilder()
    builder.feed(html)
    builder.close()
    return builder.root


def katex_math(node):
    """MathML ukryty w wyrenderowanym KaTeX (span.katex-mathml)."""
    return node.find(lambda n: n.tag == 'math')


# ───────────────────────────── MathML → OMML ─────────────────────────────

NARY = frozenset('∑∏∐∫∬∭∮∯∰⋃⋂⋁⋀⨀⨁⨂⨄⨆')
ACCENTS = {'ˉ': '̅', '¯': '̅', '‾': '̅', '̅': '̅', '_': '̅',
           '^': '̂', 'ˆ': '̂', '̂': '̂', '~': '̃', '˜': '̃', '̃': '̃',
           '˙': '̇', '̇': '̇', '¨': '̈', '̈': '̈', '→': '⃗', '⃗': '⃗',
           '˘': '̆', 'ˇ': '̌', '´': '́', 'ˊ': '́', '`': '̀', 'ˋ': '̀'}
INVISIBLE = dict.fromkeys(map(ord, '⁡⁢⁣⁤​'))
MATH_FONT = '<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></w:rPr>'
ALIGN_MARK = '<m:r><m:t>&amp;</m:t></m:r>'
CONTAINERS = frozenset('math mrow mstyle mpadded menclose semantics merror maction mtd mtr mlabeledtr'.split())


class Omml:
    """Konwersja MathML (wynik KaTeX) do Office Math Markup Language."""

    def convert(self, math):
        return self.seq(math.children)

    def seq(self, children):
        kids = [k for k in children if isinstance(k, Node) and k.tag not in ('annotation', 'annotation-xml')]
        out, i = [], 0
        while i < len(kids):
            kid = kids[i]
            if self._fence(kid):
                close = next((j for j in range(i + 1, len(kids)) if self._fence(kids[j])), None)
                if close is not None:
                    out.append(self.delimited(kid.text(), kids[close].text(), kids[i + 1:close]))
                    i = close + 1
                    continue
                if i == 0 and len(kids) > 1:
                    out.append(self.delimited(kid.text(), '', kids[1:]))
                    break
                if i == len(kids) - 1 and out:
                    return self.delimited('', kid.text(), kids[:i])
            if self._nary_op(kid) is not None:
                operand = kids[i + 1] if i + 1 < len(kids) and kids[i + 1].tag != 'mo' else None
                out.append(self.nary(kid, operand))
                i += 2 if operand is not None else 1
                continue
            out.append(self.node(kid))
            i += 1
        return ''.join(out)

    @staticmethod
    def _zwsp():
        return f'<m:r><m:rPr><m:sty m:val="p"/></m:rPr>{MATH_FONT}<m:t>\u200b</m:t></m:r>'

    @staticmethod
    def _fence(node):
        return node.tag == 'mo' and node.attrs.get('fence') == 'true'

    @staticmethod
    def _nary_op(node):
        if node.tag == 'mo':
            return node if node.text().strip() in NARY else None
        if node.tag in ('msub', 'msup', 'msubsup', 'munder', 'mover', 'munderover'):
            kids = node.elements()
            if kids and kids[0].tag == 'mo' and kids[0].text().strip() in NARY:
                return kids[0]
        return None

    def args(self, node, count):
        kids = node.elements()
        return [self.node(kids[i]) if i < len(kids) else '' for i in range(count)]

    def node(self, node):
        tag = node.tag
        if tag in ('mi', 'mn', 'mo', 'mtext', 'ms'):
            return self.token(node)
        if tag == 'mspace':
            return self.space(node)
        if tag in CONTAINERS:
            return self.seq(node.children)
        if tag == 'mphantom':
            return ''
        if tag == 'mfrac':
            num, den = self.args(node, 2)
            no_bar = node.attrs.get('linethickness', '').strip() in ('0', '0px', '0em', '0pt')
            props = '<m:fPr><m:type m:val="noBar"/></m:fPr>' if no_bar else ''
            return f'<m:f>{props}<m:num>{num or self._zwsp()}</m:num><m:den>{den or self._zwsp()}</m:den></m:f>'
        if tag == 'msqrt':
            return ('<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/>'
                    f'<m:e>{self.seq(node.children) or self._zwsp()}</m:e></m:rad>')
        if tag == 'mroot':
            base, index = self.args(node, 2)
            return f'<m:rad><m:deg>{index or self._zwsp()}</m:deg><m:e>{base or self._zwsp()}</m:e></m:rad>'
        if self._nary_op(node) is not None:
            return self.nary(node, None)
        if tag == 'msub':
            base, sub = self.args(node, 2)
            return f'<m:sSub><m:e>{base or self._zwsp()}</m:e><m:sub>{sub or self._zwsp()}</m:sub></m:sSub>'
        if tag == 'msup':
            base, sup = self.args(node, 2)
            if not base:
                kids = node.elements()
                if len(kids) > 1 and kids[1].text().strip() in ('∘', '°'):
                    return f'<m:r><m:rPr><m:sty m:val="p"/></m:rPr>{MATH_FONT}<m:t>°</m:t></m:r>'
                base = self._zwsp()
            return f'<m:sSup><m:e>{base}</m:e><m:sup>{sup or self._zwsp()}</m:sup></m:sSup>'
        if tag == 'msubsup':
            base, sub, sup = self.args(node, 3)
            return (f'<m:sSubSup><m:e>{base or self._zwsp()}</m:e><m:sub>{sub or self._zwsp()}</m:sub>'
                    f'<m:sup>{sup or self._zwsp()}</m:sup></m:sSubSup>')
        if tag in ('mover', 'munder', 'munderover'):
            return self.under_over(node)
        if tag == 'mtable':
            return self.table(node)
        return self.seq(node.children)

    def token(self, node):
        text = node.text().translate(INVISIBLE)
        if not text:
            return ''
        variant = node.attrs.get('mathvariant')
        if node.tag in ('mtext', 'ms'):
            return f'<m:r><m:rPr><m:nor/></m:rPr><m:t xml:space="preserve">{esc(text)}</m:t></m:r>'
        style = None
        if node.tag == 'mi':
            if variant == 'normal' or (variant is None and len(text) > 1):
                style = 'p'
            elif variant in ('bold', 'bold-italic'):
                style = 'b' if variant == 'bold' else 'bi'
        script = '<m:scr m:val="double-struck"/>' if variant == 'double-struck' else ''
        props = f'<m:rPr>{script}<m:sty m:val="{style}"/></m:rPr>' if style else (
            f'<m:rPr>{script}</m:rPr>' if script else '')
        return f'<m:r>{props}{MATH_FONT}<m:t xml:space="preserve">{esc(text)}</m:t></m:r>'

    @staticmethod
    def space(node):
        match = re.match(r'\s*(-?[\d.]+)\s*em', node.attrs.get('width', ''))
        width = float(match.group(1)) if match else 0.0
        if width <= 0.05:
            return ''
        chars = ('  ' if width >= 1.8 else ' ' if width >= 0.9 else
                 ' ' if width >= 0.45 else ' ' if width >= 0.25 else ' ')
        return f'<m:r><m:rPr><m:sty m:val="p"/></m:rPr>{MATH_FONT}<m:t xml:space="preserve">{chars}</m:t></m:r>'

    def delimited(self, begin, end, inner):
        return (f'<m:d><m:dPr><m:begChr m:val="{esc(begin.strip())}"/><m:endChr m:val="{esc(end.strip())}"/>'
                f'</m:dPr><m:e>{self.seq(inner) or self._zwsp()}</m:e></m:d>')

    def nary(self, node, operand):
        kids = [node] if node.tag == 'mo' else node.elements()
        symbol = kids[0].text().strip()
        sub = sup = None
        if node.tag in ('msub', 'munder'):
            sub = kids[1] if len(kids) > 1 else None
        elif node.tag in ('msup', 'mover'):
            sup = kids[1] if len(kids) > 1 else None
        elif node.tag in ('msubsup', 'munderover'):
            sub, sup = (kids[1] if len(kids) > 1 else None), (kids[2] if len(kids) > 2 else None)
        under_over = node.tag.startswith('mu') or node.tag == 'mover' or (node.tag == 'mo' and symbol in '∑∏∐')
        props = (f'<m:chr m:val="{esc(symbol)}"/><m:limLoc m:val="{"undOvr" if under_over else "subSup"}"/>'
                 + ('<m:subHide m:val="1"/>' if sub is None else '')
                 + ('<m:supHide m:val="1"/>' if sup is None else ''))
        body = (self.node(operand) if operand is not None else '') or self._zwsp()
        return (f'<m:nary><m:naryPr>{props}</m:naryPr>'
                f'<m:sub>{self.node(sub) if sub is not None else ""}</m:sub>'
                f'<m:sup>{self.node(sup) if sup is not None else ""}</m:sup>'
                f'<m:e>{body}</m:e></m:nary>')

    def under_over(self, node):
        kids = node.elements()
        if not kids:
            return ''
        base = self.node(kids[0]) or self._zwsp()
        if node.tag == 'mover' and len(kids) > 1:
            mark = kids[1].text().strip()
            if mark in ACCENTS and (node.attrs.get('accent') == 'true' or kids[1].tag == 'mo'):
                return (f'<m:acc><m:accPr><m:chr m:val="{ACCENTS[mark]}"/></m:accPr>'
                        f'<m:e>{base}</m:e></m:acc>')
            return f'<m:limUpp><m:e>{base}</m:e><m:lim>{self.node(kids[1]) or self._zwsp()}</m:lim></m:limUpp>'
        if node.tag == 'munder':
            under = (self.node(kids[1]) if len(kids) > 1 else '') or self._zwsp()
            return f'<m:limLow><m:e>{base}</m:e><m:lim>{under}</m:lim></m:limLow>'
        under = (self.node(kids[1]) if len(kids) > 1 else '') or self._zwsp()
        over = (self.node(kids[2]) if len(kids) > 2 else '') or self._zwsp()
        return (f'<m:limUpp><m:e><m:limLow><m:e>{base}</m:e><m:lim>{under}</m:lim></m:limLow></m:e>'
                f'<m:lim>{over}</m:lim></m:limUpp>')

    def table(self, node):
        rows = []
        for row in node.elements():
            if row.tag not in ('mtr', 'mlabeledtr'):
                continue
            cells = [c for c in row.elements() if c.tag == 'mtd']
            rows.append(cells[1:] if row.tag == 'mlabeledtr' else cells)
        if not rows:
            return ''
        if len(rows) == 1 and len(rows[0]) == 1:
            return self.node(rows[0][0])
        align = node.attrs.get('columnalign', '').split()
        if max(map(len, rows), default=0) <= 2 or align[:2] == ['right', 'left']:
            # Układ wierszy (aligned, cases): wiersze równań wyrównane w miejscu „&”.
            return '<m:eqArr>' + ''.join(
                f'<m:e>{ALIGN_MARK.join(self.node(c) for c in cells) or self._zwsp()}</m:e>' for cells in rows) + '</m:eqArr>'
        count = max(map(len, rows))
        empty = f'<m:e>{self._zwsp()}</m:e>'
        return (f'<m:m><m:mPr><m:mcs><m:mc><m:mcPr><m:count m:val="{count}"/><m:mcJc m:val="center"/>'
                '</m:mcPr></m:mc></m:mcs></m:mPr>'
                + ''.join('<m:mr>' + ''.join(f'<m:e>{self.node(c) or self._zwsp()}</m:e>' for c in cells)
                          + empty * (count - len(cells)) + '</m:mr>' for cells in rows) + '</m:m>')


# ───────────────────────────── obrazy ─────────────────────────────

def image_size(data, kind):
    """Wymiary w pikselach z nagłówka PNG lub JPEG."""
    if kind == 'png' and data[:8] == b'\x89PNG\r\n\x1a\n':
        return struct.unpack('>II', data[16:24])
    if kind == 'jpeg':
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                height, width = struct.unpack('>HH', data[i + 5:i + 9])
                return width, height
            i += 2 + struct.unpack('>H', data[i + 2:i + 4])[0]
    return None


# ───────────────────────────── dokument ─────────────────────────────

def _field(instr, cached, rpr=''):
    return (f'<w:r>{rpr}<w:fldChar w:fldCharType="begin"/></w:r>'
            f'<w:r>{rpr}<w:instrText xml:space="preserve"> {esc(instr)} </w:instrText></w:r>'
            f'<w:r>{rpr}<w:fldChar w:fldCharType="separate"/></w:r>'
            f'<w:r>{rpr}<w:t>{esc(cached)}</w:t></w:r>'
            f'<w:r>{rpr}<w:fldChar w:fldCharType="end"/></w:r>')


def _run(text, fmt=frozenset()):
    props = []
    if 'mono' in fmt:
        props.append('<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>')
    if 'b' in fmt:
        props.append('<w:b/>')
    if 'i' in fmt:
        props.append('<w:i/>')
    if 'sub' in fmt or 'sup' in fmt:
        props.append(f'<w:vertAlign w:val="{"subscript" if "sub" in fmt else "superscript"}"/>')
    rpr = f'<w:rPr>{"".join(props)}</w:rPr>' if props else ''
    return f'<w:r>{rpr}<w:t xml:space="preserve">{esc(text)}</w:t></w:r>'


def _borders(tag, sides):
    return f'<w:{tag}>' + ''.join(
        f'<w:{side} w:val="{"single" if size else "nil"}"' + (f' w:sz="{size}" w:space="0" w:color="{color}"' if size else '') + '/>'
        for side, (size, color) in sides) + f'</w:{tag}>'


NO_BORDERS = _borders('tblBorders', [(s, (0, '')) for s in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV')])


class DocxWriter:
    def __init__(self):
        self.out = [[]]
        self.images = []
        self.counters = {'Tabela': 0, 'Rysunek': 0, 'Wzor': 0}
        self.ordered_lists = []
        self.page_break = False
        self.has_toc = False
        self.math = Omml()
        self.drawing_id = 0

    # ── emisja ──
    def emit(self, xml):
        self.out[-1].append(xml)

    def emit_table(self, xml):
        if self.page_break:
            self.emit('<w:p><w:pPr><w:spacing w:before="0" w:after="0"/></w:pPr><w:r><w:br w:type="page"/></w:r></w:p>')
            self.page_break = False
        if self.out[-1] and self.out[-1][-1].startswith('<w:tbl>'):
            # Sąsiednie tabele Word łączy w jedną; oddziela je pusty akapit o minimalnej wysokości.
            self.emit('<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="60" w:lineRule="exact"/></w:pPr></w:p>')
        self.emit(xml)

    def capture(self, fn, *args):
        self.out.append([])
        fn(*args)
        return self.out.pop()

    # ── akapity ──
    def paragraph(self, runs, ctx, style=None):
        style = style or ctx.get('style') or 'Normal'
        props = [f'<w:pStyle w:val="{style}"/>']
        if ctx.get('keep_next'):
            props.append('<w:keepNext/>')
        if self.page_break and not ctx.get('in_table'):
            props.append('<w:pageBreakBefore/>')
            self.page_break = False
        state = ctx.get('list')
        indent = ctx.get('indent')
        if state is not None and state['first']:
            props.append(f'<w:numPr><w:ilvl w:val="{state["level"]}"/><w:numId w:val="{state["num"]}"/></w:numPr>')
            state['first'] = False
        elif state is not None:
            indent = 357 * (state['level'] + 1)  # kolejny akapit tego samego punktu listy
        if indent:
            props.append(f'<w:ind w:left="{indent}"/>')
        if ctx.get('align') in ('center', 'right', 'left'):
            props.append(f'<w:jc w:val="{ctx["align"]}"/>')
        self.emit(f'<w:p><w:pPr>{"".join(props)}</w:pPr>{runs}</w:p>')

    def flush(self, items, ctx):
        if any((kind == 't' and value.strip()) or kind in ('math', 'img', 'field')
               for kind, value, *_ in items):
            self.paragraph(self.runs(items, ctx), ctx)
        items.clear()

    def runs(self, items, ctx):
        preserve = ctx.get('preserve')
        out, at_space = [], True
        # Końcową spację usuwa się tylko z tekstu, po którym nie ma już wzoru ani obrazu.
        last_text = max((i for i, it in enumerate(items) if it[0] == 't'), default=-1)
        if any(it[0] != 't' for it in items[last_text + 1:]):
            last_text = -1
        for index, (kind, value, *rest) in enumerate(items):
            if kind == 't':
                fmt = rest[0]
                if preserve:
                    lines = value.split('\n')
                    for n, line in enumerate(lines):
                        if n:
                            out.append('<w:r><w:br/></w:r>')
                        if line:
                            out.append(_run(line, fmt))
                    continue
                text = _SPACES.sub(' ', value)
                if at_space:
                    text = text.lstrip(' ')
                if index == last_text:
                    text = text.rstrip(' ')
                if text:
                    out.append(_run(text, fmt))
                    at_space = text.endswith(' ')
            elif kind == 'br':
                out.append('<w:r><w:br/></w:r>')
                at_space = True
            elif kind == 'math':
                out.append(f'<m:oMath>{self.math.convert(value)}</m:oMath>')
                at_space = False
            elif kind == 'img':
                out.append(self.image(value, ctx))
                at_space = False
            elif kind == 'field':
                out.append(_field(value, rest[0]))
                at_space = False
        return ''.join(out)

    # ── przechodzenie drzewa ──
    def walk(self, node, ctx):
        self.walk_children(node.children, ctx)

    def walk_children(self, children, ctx):
        items = []
        for child in children:
            if isinstance(child, str):
                items.append(('t', child, ctx.get('fmt', frozenset())))
            elif self.hidden(child):
                continue
            elif (display := self.display_math_node(child)) is not None:
                self.flush(items, ctx)
                self.display_math(display, ctx)
            elif child.tag in BLOCK:
                self.flush(items, ctx)
                self.block(child, ctx)
            else:
                self.inline(child, ctx.get('fmt', frozenset()), items, ctx)
        self.flush(items, ctx)

    @staticmethod
    def hidden(node):
        return (node.tag in SKIP or 'hidden' in node.attrs or 'no-print' in node.classes()
                or node.attrs.get('aria-hidden') == 'true')

    @staticmethod
    def display_math_node(node):
        if node.tag == 'math' and node.attrs.get('display') == 'block':
            return node
        if 'katex-display' in node.classes():
            return katex_math(node)
        return None

    def inline(self, node, fmt, items, ctx):
        tag, cls = node.tag, node.classes()
        if self.hidden(node):
            return
        if tag == 'br':
            items.append(('br', None))
            return
        if tag == 'math':
            items.append(('math', node))
            return
        if 'katex' in cls:
            math = katex_math(node)
            if math is not None:
                items.append(('math', math))
            return
        if tag == 'img':
            items.append(('img', node))
            return
        if tag in ('strong', 'b'):
            fmt = fmt | {'b'}
        elif tag in ('em', 'i', 'cite', 'var', 'dfn'):
            fmt = fmt | {'i'}
        elif tag in ('sub', 'sup'):
            fmt = fmt | {tag}
        elif tag in ('code', 'kbd', 'samp'):
            fmt = fmt | {'mono'}
        if 'empty-metadata' in cls and not node.text().strip():
            items.append(('t', '…………………………', fmt))
            return
        for child in node.children:
            if isinstance(child, str):
                items.append(('t', child, fmt))
            else:
                self.inline(child, fmt, items, ctx)

    def block(self, node, ctx):
        tag, cls = node.tag, node.classes()
        base = {k: v for k, v in ctx.items() if k in ('in_table', 'max_mm', 'list', 'calc')}
        if tag == 'header' and 'cover' in cls:
            self.cover(node)
        elif tag == 'nav' and 'toc' in cls:
            self.toc(node)
        elif tag in HEADINGS:
            self.walk(node, {**base, 'style': HEADINGS[tag], 'keep_next': True})
        elif tag == 'p':
            style = next((s for c, s in PARAGRAPH_CLASSES if c in cls), ctx.get('style') or 'Normal')
            self.walk(node, {**ctx, 'style': style, 'keep_next': 'calc-label' in cls or ctx.get('keep_next'),
                             'preserve': 'author-text' in cls})
        elif tag in ('ul', 'ol'):
            self.listing(node, ctx)
        elif tag == 'table':
            self.table(node, ctx)
        elif tag == 'figure':
            self.figure(node, ctx)
        elif tag in ('caption', 'figcaption'):
            self.walk(node, {**base, 'style': 'Caption'})
        elif tag == 'hr':
            self.emit('<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="4" w:space="1" w:color="AAAAAA"/>'
                      '</w:pBdr></w:pPr></w:p>')
        elif tag == 'pre':
            self.walk(node, {**ctx, 'preserve': True, 'fmt': ctx.get('fmt', frozenset()) | {'mono'}})
        elif tag == 'dt':
            self.walk(node, {**ctx, 'fmt': ctx.get('fmt', frozenset()) | {'b'}, 'keep_next': True})
        elif 'equation' in cls:
            self.equation(node, ctx)
        elif 'figure-pair' in cls:
            self.figure_pair(node, ctx)
        elif 'calc' in cls:
            self.walk(node, {**ctx, 'calc': True})
        elif 'report-appendix' in cls:
            self.page_break = True
            self.walk(node, ctx)
        elif 'bibliography' in cls:
            self.listing(node, {**ctx, 'style': 'Bibliography'})
        else:
            self.walk(node, ctx)

    # ── listy ──
    def listing(self, node, ctx, level=0):
        ordered = node.tag == 'ol'
        if ordered:
            num = 2 + len(self.ordered_lists)
            self.ordered_lists.append((num, level))
        else:
            num = 1
        style = ctx.get('style') if ctx.get('style') == 'Bibliography' else 'ListParagraph'
        for item in node.elements():
            if item.tag != 'li' or self.hidden(item):
                continue
            state = {'num': num, 'level': min(level, 8), 'first': True}
            item_ctx = {k: v for k, v in ctx.items() if k in ('in_table', 'max_mm', 'fmt')}
            item_ctx.update(style=style, list=state)
            children = []
            for child in item.children:
                if isinstance(child, Node) and child.tag in ('ul', 'ol'):
                    self.walk_children(children, item_ctx)
                    children = []
                    self.listing(child, {**item_ctx, 'list': None}, level + 1)
                else:
                    children.append(child)
            self.walk_children(children, item_ctx)

    # ── strona tytułowa i spis treści ──
    def cover(self, node):
        frame = node.find(lambda n: 'cover-frame' in n.classes()) or node
        rows = {'top': [], 'middle': [], 'bottom': []}
        place = {'cover-author': 'top', 'cover-project': 'middle', 'cover-institution': 'middle',
                 'cover-subject': 'middle', 'cover-date': 'bottom', 'cover-grade': 'bottom', 'cover-place': 'bottom'}
        for child in frame.elements():
            key = next((place[c] for c in child.classes() if c in place), 'middle')
            rows[key].append(child)
        layout = {'cover-author': ('CoverText', 'right'), 'cover-institution': ('CoverStrong', 'center'),
                  'cover-subject': ('CoverSubject', 'center'), 'cover-project': ('CoverText', 'center'),
                  'cover-date': ('CoverText', 'left'), 'cover-grade': ('CoverText', 'right'),
                  'cover-place': ('CoverText', 'center')}

        def render(children):
            for child in children:
                cls = next((c for c in child.classes() if c in layout), 'cover-project')
                style, align = layout[cls]
                ctx = {'style': style, 'align': align, 'in_table': True}
                if cls == 'cover-project':
                    for part in child.elements():
                        if part.tag in HEADINGS:
                            self.walk(part, {**ctx, 'style': 'CoverTitle'})
                        elif 'aircraft-name' in part.classes():
                            self.walk(part, {**ctx, 'style': 'CoverAircraft'})
                        else:
                            self.walk(part, {**ctx, 'style': 'CoverSmall'})
                else:
                    self.walk(child, ctx)

        height = {'top': 62, 'middle': 118, 'bottom': 62}
        valign = {'top': 'top', 'middle': 'center', 'bottom': 'bottom'}
        body = []
        for key in ('top', 'middle', 'bottom'):
            content = ''.join(self.capture(render, rows[key])) or '<w:p/>'
            body.append(f'<w:tr><w:trPr><w:cantSplit/><w:trHeight w:val="{round(height[key] * TWIP_PER_MM)}" '
                        f'w:hRule="exact"/></w:trPr><w:tc><w:tcPr><w:tcW w:w="{TEXT_WIDTH}" w:type="dxa"/>'
                        f'<w:vAlign w:val="{valign[key]}"/></w:tcPr>{content}</w:tc></w:tr>')
        frame_borders = _borders('tblBorders', [(s, (8, '222222')) for s in ('top', 'left', 'bottom', 'right')]
                                 + [(s, (0, '')) for s in ('insideH', 'insideV')])
        self.emit_table(f'<w:tbl><w:tblPr><w:tblW w:w="{TEXT_WIDTH}" w:type="dxa"/>{frame_borders}'
                        '<w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="170" w:type="dxa"/>'
                        '<w:left w:w="227" w:type="dxa"/><w:bottom w:w="170" w:type="dxa"/>'
                        '<w:right w:w="227" w:type="dxa"/></w:tblCellMar></w:tblPr>'
                        f'<w:tblGrid><w:gridCol w:w="{TEXT_WIDTH}"/></w:tblGrid>{"".join(body)}</w:tbl>')
        self.page_break = True

    def toc(self, node):
        heading = node.find(lambda n: n.tag in HEADINGS)
        if heading is not None:
            self.walk(heading, {'style': 'TOCHeading', 'keep_next': True})
        entries = [li.text().strip() for li in self._descendants(node, 'li')]
        if not entries:
            return
        self.has_toc = True
        begin = ('<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve">'
                 ' TOC \\o "1-2" \\h \\z \\u </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r>')
        end = '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
        for i, entry in enumerate(entries):
            runs = (begin if i == 0 else '') + _run(entry) + (end if i == len(entries) - 1 else '')
            self.emit(f'<w:p><w:pPr><w:pStyle w:val="TOC1"/></w:pPr>{runs}</w:p>')

    def _descendants(self, node, tag):
        for child in node.elements():
            if child.tag == tag:
                yield child
            else:
                yield from self._descendants(child, tag)

    # ── tabele ──
    def caption(self, node, label, prefix, ctx, align=None):
        self.counters[label] += 1
        items = [('t', prefix + ' ', frozenset()), ('field', f'SEQ {label} \\* ARABIC', str(self.counters[label])),
                 ('t', '. ', frozenset())]
        for child in node.children:
            if isinstance(child, str):
                items.append(('t', child, frozenset()))
            else:
                self.inline(child, frozenset(), items, ctx)
        self.paragraph(self.runs(items, ctx), {'keep_next': label == 'Tabela', 'align': align,
                                               'in_table': ctx.get('in_table')}, style='Caption')

    def table(self, node, ctx):
        caption = next((c for c in node.elements() if c.tag == 'caption'), None)
        if caption is not None:
            self.caption(caption, 'Tabela', 'Tabela', ctx)
        rows = []
        for part in node.elements():
            if part.tag in ('thead', 'tbody', 'tfoot'):
                rows += [(tr, part.tag == 'thead') for tr in part.elements() if tr.tag == 'tr']
            elif part.tag == 'tr':
                rows.append((part, False))
        rows = [(tr, head) for tr, head in rows if not self.hidden(tr)]
        if not rows:
            return
        def cells_of(tr):
            return [c for c in tr.elements() if c.tag in ('td', 'th') and not self.hidden(c)]

        def span(cell):
            value = str(cell.attrs.get('colspan') or '1').strip()
            return max(1, min(int(value), 63)) if value.isdigit() else 1

        ncols = max(sum(span(c) for c in cells_of(tr)) or 1 for tr, _ in rows)
        total = round(ctx.get('max_mm', 170) * TWIP_PER_MM) if ctx.get('in_table') else TEXT_WIDTH
        widths = self.column_widths(rows, cells_of, span, ncols, total)
        compact = 'compact-table' in node.classes() or 'iteration-table' in node.classes()
        body = []
        for index, (tr, head) in enumerate(rows):
            last = index == len(rows) - 1
            cells_xml, col = [], 0
            for cell in cells_of(tr):
                n = min(span(cell), ncols - col) or 1
                width = sum(widths[col:col + n])
                is_head = head or cell.tag == 'th' and all(c.tag == 'th' for c in cells_of(tr))
                cell_ctx = {'style': 'TableTextCompact' if compact else 'TableText', 'in_table': True,
                            'max_mm': width / TWIP_PER_MM - 4,
                            'align': 'right' if 'number' in cell.classes() else None,
                            'fmt': frozenset({'b'}) if cell.tag == 'th' else frozenset()}
                content = ''.join(self.capture(self.walk, cell, cell_ctx))
                if not content.endswith('</w:p>'):
                    content += f'<w:p><w:pPr><w:pStyle w:val="{cell_ctx["style"]}"/></w:pPr></w:p>'
                top = (8, '555555') if is_head else (0, '')
                bottom = (6, '777777') if is_head or last else (4, 'C9C9C5')
                borders = _borders('tcBorders', [('top', top), ('bottom', bottom)])
                shade = '<w:shd w:val="clear" w:color="auto" w:fill="F1F1EF"/>' if is_head else ''
                grid = f'<w:gridSpan w:val="{n}"/>' if n > 1 else ''
                cells_xml.append(f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{grid}{borders}{shade}</w:tcPr>'
                                 f'{content}</w:tc>')
                col += n
            if col < ncols:  # wiersz krótszy od siatki: pusta komórka do końca
                grid = f'<w:gridSpan w:val="{ncols - col}"/>' if ncols - col > 1 else ''
                cells_xml.append(f'<w:tc><w:tcPr><w:tcW w:w="{sum(widths[col:])}" w:type="dxa"/>{grid}</w:tcPr>'
                                 '<w:p/></w:tc>')
            header = '<w:tblHeader/>' if head else ''
            body.append(f'<w:tr><w:trPr><w:cantSplit/>{header}</w:trPr>{"".join(cells_xml)}</w:tr>')
        margin = 96 if compact else 113
        self.emit_table(f'<w:tbl><w:tblPr><w:tblW w:w="{total}" w:type="dxa"/>{NO_BORDERS}'
                        f'<w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="45" w:type="dxa"/>'
                        f'<w:left w:w="{margin}" w:type="dxa"/><w:bottom w:w="45" w:type="dxa"/>'
                        f'<w:right w:w="{margin}" w:type="dxa"/></w:tblCellMar></w:tblPr>'
                        '<w:tblGrid>' + ''.join(f'<w:gridCol w:w="{w}"/>' for w in widths) + '</w:tblGrid>'
                        + ''.join(body) + '</w:tbl>')

    def column_widths(self, rows, cells_of, span, ncols, total):
        weights = [4.0] * ncols
        for tr, _ in rows:
            col = 0
            for cell in cells_of(tr):
                if span(cell) == 1 and col < ncols:
                    weights[col] = max(weights[col], min(self.visible_length(cell), 46))
                col += span(cell)
        minimum = min(700, total // ncols)
        widths = [max(minimum, int(total * w / sum(weights))) for w in weights]
        excess = sum(widths) - total
        while excess > 0:
            widest = widths.index(max(widths))
            cut = min(excess, widths[widest] - minimum)
            if cut <= 0:
                break
            widths[widest] -= cut
            excess -= cut
        widths[-1] += total - sum(widths)
        return widths

    def visible_length(self, node):
        if isinstance(node, str):
            return len(_SPACES.sub(' ', node).strip())
        if node.tag == 'math':
            return sum(len(n.text()) for n in self._tokens(node))
        if 'katex' in node.classes() or 'katex-display' in node.classes():
            math = katex_math(node)
            return self.visible_length(math) if math is not None else 0
        if self.hidden(node):
            return 0
        return sum(self.visible_length(c) for c in node.children)

    def _tokens(self, node):
        for child in node.elements():
            if child.tag in ('mi', 'mn', 'mo', 'mtext'):
                yield child
            elif child.tag not in ('annotation', 'annotation-xml'):
                yield from self._tokens(child)

    # ── wzory ──
    def display_math(self, math, ctx):
        jc = 'left' if ctx.get('calc') else 'center'
        props = '<w:pStyle w:val="Equation"/>' + ('<w:ind w:left="227"/>' if ctx.get('calc') else '')
        self.emit(f'<w:p><w:pPr>{props}</w:pPr><m:oMathPara><m:oMathParaPr><m:jc m:val="{jc}"/></m:oMathParaPr>'
                  f'<m:oMath>{self.math.convert(math)}</m:oMath></m:oMathPara></w:p>')

    def equation(self, node, ctx):
        math = node.find(lambda n: n.tag == 'math' or 'katex' in n.classes())
        if math is not None and math.tag != 'math':
            math = katex_math(math)
        if math is None:
            self.walk(node, ctx)
            return
        self.counters['Wzor'] += 1
        total = round(ctx.get('max_mm', 170) * TWIP_PER_MM) if ctx.get('in_table') else TEXT_WIDTH
        formula = ''.join(self.capture(self.display_math, math, ctx))
        seq_field = _field(r'SEQ Wzor \* ARABIC', str(self.counters['Wzor']))
        number = f'<w:p><w:pPr><w:pStyle w:val="Equation"/><w:jc w:val="right"/></w:pPr>{_run("(")}{seq_field}{_run(")")}</w:p>'
        cell = lambda width, content: (f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>'
                                       f'<w:vAlign w:val="center"/></w:tcPr>{content}</w:tc>')
        self.emit_table(f'<w:tbl><w:tblPr><w:tblW w:w="{total}" w:type="dxa"/>{NO_BORDERS}'
                        '<w:tblLayout w:type="fixed"/><w:tblCellMar><w:left w:w="0" w:type="dxa"/>'
                        '<w:right w:w="0" w:type="dxa"/></w:tblCellMar></w:tblPr>'
                        f'<w:tblGrid><w:gridCol w:w="{total - NUMBER_COLUMN}"/><w:gridCol w:w="{NUMBER_COLUMN}"/></w:tblGrid>'
                        f'<w:tr><w:trPr><w:cantSplit/></w:trPr>{cell(total - NUMBER_COLUMN, formula)}'
                        f'{cell(NUMBER_COLUMN, number)}</w:tr></w:tbl>')

    # ── rysunki ──
    def figure(self, node, ctx):
        caption = None
        children = []
        for child in node.children:
            if isinstance(child, Node) and child.tag == 'figcaption':
                caption = child
            else:
                children.append(child)
        self.walk_children(children, {**{k: v for k, v in ctx.items() if k in ('in_table', 'max_mm')},
                                      'style': 'Figure', 'align': 'center', 'keep_next': caption is not None})
        if caption is not None:
            self.caption(caption, 'Rysunek', 'Rys.', ctx, align='center')

    def figure_pair(self, node, ctx):
        parts = [c for c in node.elements() if not self.hidden(c)]
        if not parts:
            return
        total = TEXT_WIDTH
        width = total // len(parts)
        cells = []
        for part in parts:
            content = ''.join(self.capture(self.walk, part, {'style': 'Figure', 'align': 'center', 'in_table': True,
                                                             'max_mm': width / TWIP_PER_MM - 2}))
            cells.append(f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/></w:tcPr>{content or "<w:p/>"}</w:tc>')
        self.emit_table(f'<w:tbl><w:tblPr><w:tblW w:w="{width * len(parts)}" w:type="dxa"/>{NO_BORDERS}'
                        '<w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid>'
                        + f'<w:gridCol w:w="{width}"/>' * len(parts) + '</w:tblGrid>'
                        f'<w:tr><w:trPr><w:cantSplit/></w:trPr>{"".join(cells)}</w:tr></w:tbl>')

    def image(self, node, ctx):
        match = _DATA_URL.match(node.attrs.get('src', '').strip())
        if not match:
            alt = node.attrs.get('alt', '').strip()
            return _run(f'[{alt}]') if alt else ''
        kind = 'png' if match.group(1) == 'png' else 'jpeg'
        try:
            data = base64.b64decode(match.group(2), validate=False)
        except ValueError:
            return ''
        size = image_size(data, kind)
        if not size or not all(size):
            return ''
        px_w, px_h = size
        try:
            width_mm = float(node.attrs.get('data-width-mm') or 0)
        except ValueError:
            width_mm = 0
        width_mm = min(width_mm or px_w * 25.4 / 96, ctx.get('max_mm', 170))
        height_mm = width_mm * px_h / px_w
        if height_mm > MAX_IMAGE_HEIGHT_MM:
            width_mm, height_mm = width_mm * MAX_IMAGE_HEIGHT_MM / height_mm, MAX_IMAGE_HEIGHT_MM
        self.images.append((kind, data))
        self.drawing_id += 1
        n, rid = self.drawing_id, f'rIdImg{len(self.images)}'
        cx, cy = round(width_mm * EMU_PER_MM), round(height_mm * EMU_PER_MM)
        alt = esc(node.attrs.get('alt', '') or f'Rysunek {n}')
        return (f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
                f'<wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="{n}" name="Obraz {n}" descr="{alt}"/>'
                '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
                '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
                f'<pic:pic><pic:nvPicPr><pic:cNvPr id="{n}" name="obraz{n}.{kind}"/><pic:cNvPicPr/></pic:nvPicPr>'
                f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
                f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
                '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
                '</wp:inline></w:drawing></w:r>')

    # ── pakiet ──
    def document_xml(self):
        body = ''.join(self.out[0]) or '<w:p/>'
        sect = (f'<w:sectPr><w:footerReference w:type="default" r:id="rIdFooter"/>'
                '<w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1077" w:right="1134" w:bottom="1134" '
                'w:left="1134" w:header="567" w:footer="567" w:gutter="0"/><w:titlePg/></w:sectPr>')
        return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:document {NS}><w:body>{body}{sect}</w:body></w:document>'

    def numbering_xml(self):
        def level(i, fmt, text, font=''):
            rpr = f'<w:rPr><w:rFonts w:ascii="{font}" w:hAnsi="{font}"/></w:rPr>' if font else ''
            return (f'<w:lvl w:ilvl="{i}"><w:start w:val="1"/><w:numFmt w:val="{fmt}"/><w:lvlText w:val="{text}"/>'
                    f'<w:lvlJc w:val="left"/><w:pPr><w:ind w:left="{357 * (i + 1)}" w:hanging="357"/></w:pPr>{rpr}</w:lvl>')
        bullets = ''.join(level(i, 'bullet', '•◦▪'[i % 3], 'Arial') for i in range(9))
        decimal = ''.join(level(i, 'decimal', f'%{i + 1}.') for i in range(9))
        nums = '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>' + ''.join(
            f'<w:num w:numId="{num}"><w:abstractNumId w:val="1"/><w:lvlOverride w:ilvl="{lvl}">'
            f'<w:startOverride w:val="1"/></w:lvlOverride></w:num>' for num, lvl in self.ordered_lists)
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                f'<w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="hybridMultilevel"/>{bullets}</w:abstractNum>'
                f'<w:abstractNum w:abstractNumId="1"><w:multiLevelType w:val="multilevel"/>{decimal}</w:abstractNum>'
                f'{nums}</w:numbering>')


STYLES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Georgia" w:hAnsi="Georgia" w:eastAsia="Georgia" w:cs="Times New Roman"/><w:color w:val="181818"/><w:sz w:val="21"/><w:szCs w:val="21"/><w:lang w:val="pl-PL" w:eastAsia="pl-PL" w:bidi="ar-SA"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:widowControl/><w:spacing w:after="170" w:line="331" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:after="170"/></w:pPr><w:rPr><w:b/><w:sz w:val="40"/><w:szCs w:val="40"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="9"/><w:qFormat/><w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="510" w:after="227" w:line="240" w:lineRule="auto"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="30"/><w:szCs w:val="30"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="9"/><w:unhideWhenUsed/><w:qFormat/><w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="340" w:after="142" w:line="240" w:lineRule="auto"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="9"/><w:unhideWhenUsed/><w:qFormat/><w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="227" w:after="113" w:line="240" w:lineRule="auto"/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading4"><w:name w:val="heading 4"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="9"/><w:unhideWhenUsed/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="170" w:after="85"/><w:outlineLvl w:val="3"/></w:pPr><w:rPr><w:b/><w:i/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Caption"><w:name w:val="caption"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="35"/><w:unhideWhenUsed/><w:qFormat/><w:pPr><w:spacing w:before="60" w:after="113" w:line="240" w:lineRule="auto"/></w:pPr><w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="TableText"><w:name w:val="Tekst w tabeli"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:after="0" w:line="252" w:lineRule="auto"/></w:pPr><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="TableTextCompact"><w:name w:val="Tekst w tabeli zwartej"/><w:basedOn w:val="TableText"/><w:qFormat/><w:rPr><w:sz w:val="17"/><w:szCs w:val="17"/></w:rPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="CalcLabel"><w:name w:val="Opis obliczenia"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="113" w:after="0" w:line="252" w:lineRule="auto"/></w:pPr><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:color w:val="333333"/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="CalcNote"><w:name w:val="Uwaga do obliczenia"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:after="85" w:line="252" w:lineRule="auto"/><w:ind w:left="227"/></w:pPr><w:rPr><w:color w:val="444444"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="Equation"><w:name w:val="Wzór"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:before="40" w:after="40" w:line="240" w:lineRule="auto"/></w:pPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="Figure"><w:name w:val="Rysunek"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="113" w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="Small"><w:name w:val="Tekst drobny"/><w:basedOn w:val="Normal"/><w:qFormat/><w:rPr><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListParagraph"><w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/><w:uiPriority w:val="34"/><w:qFormat/><w:pPr><w:spacing w:after="60"/><w:ind w:left="720"/><w:contextualSpacing/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Bibliography"><w:name w:val="Bibliography"/><w:basedOn w:val="Normal"/><w:uiPriority w:val="37"/><w:unhideWhenUsed/><w:pPr><w:spacing w:after="113"/></w:pPr><w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="CoverText"><w:name w:val="Strona tytułowa"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:after="40" w:line="240" w:lineRule="auto"/></w:pPr><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="CoverTitle"><w:name w:val="Strona tytułowa — tytuł"/><w:basedOn w:val="CoverText"/><w:qFormat/><w:pPr><w:spacing w:after="567" w:line="300" w:lineRule="auto"/></w:pPr><w:rPr><w:sz w:val="52"/><w:szCs w:val="52"/></w:rPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="CoverAircraft"><w:name w:val="Strona tytułowa — samolot"/><w:basedOn w:val="CoverText"/><w:qFormat/><w:pPr><w:spacing w:after="170"/></w:pPr><w:rPr><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="CoverSmall"><w:name w:val="Strona tytułowa — opis"/><w:basedOn w:val="CoverText"/><w:qFormat/><w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="CoverStrong"><w:name w:val="Strona tytułowa — uczelnia"/><w:basedOn w:val="CoverText"/><w:qFormat/><w:rPr><w:b/></w:rPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="CoverSubject"><w:name w:val="Strona tytułowa — przedmiot"/><w:basedOn w:val="CoverText"/><w:qFormat/><w:pPr><w:spacing w:line="312" w:lineRule="auto"/></w:pPr><w:rPr><w:sz w:val="50"/><w:szCs w:val="50"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="TOCHeading"><w:name w:val="TOC Heading"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="39"/><w:unhideWhenUsed/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="227" w:after="113"/></w:pPr><w:rPr><w:b/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="TOC1"><w:name w:val="toc 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="39"/><w:unhideWhenUsed/><w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9628"/></w:tabs><w:spacing w:after="60"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="TOC2"><w:name w:val="toc 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="39"/><w:unhideWhenUsed/><w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9628"/></w:tabs><w:spacing w:after="40"/><w:ind w:left="227"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Footer"><w:name w:val="footer"/><w:basedOn w:val="Normal"/><w:uiPriority w:val="99"/><w:unhideWhenUsed/><w:pPr><w:spacing w:after="0"/><w:jc w:val="center"/></w:pPr><w:rPr><w:color w:val="555555"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:style>
<w:style w:type="table" w:default="1" w:styleId="TableNormal"><w:name w:val="Normal Table"/><w:uiPriority w:val="99"/><w:semiHidden/><w:unhideWhenUsed/><w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="108" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>
</w:styles>'''

FOOTER = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
          '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
          '<w:p><w:pPr><w:pStyle w:val="Footer"/></w:pPr>' + _field('PAGE', '2') + '</w:p></w:ftr>')


def _settings(update_fields):
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
            '<w:zoom w:percent="100"/><w:defaultTabStop w:val="709"/><w:autoHyphenation/>'
            '<w:characterSpacingControl w:val="doNotCompress"/>'
            + ('<w:updateFields w:val="true"/>' if update_fields else '') +
            '<w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>'
            '<m:mathPr><m:mathFont m:val="Cambria Math"/><m:brkBin m:val="before"/><m:brkBinSub m:val="--"/>'
            '<m:smallFrac m:val="0"/><m:dispDef/><m:lMargin m:val="0"/><m:rMargin m:val="0"/>'
            '<m:defJc m:val="centerGroup"/><m:wrapIndent m:val="1440"/><m:intLim m:val="subSup"/>'
            '<m:naryLim m:val="undOvr"/></m:mathPr><w:themeFontLang w:val="pl-PL"/></w:settings>')


def build_docx(html, title='', author=''):
    """Bajty pliku DOCX dla HTML dokumentu raportu (zawartość elementu .document)."""
    writer = DocxWriter()
    writer.walk(parse_html(html), {})
    images = ''.join(
        f'<Relationship Id="rIdImg{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
        f'Target="media/obraz{i}.{"png" if kind == "png" else "jpeg"}"/>' for i, (kind, _) in enumerate(writer.images, 1))
    rel = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    created = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    parts = {
        '[Content_Types].xml': (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Default Extension="png" ContentType="image/png"/><Default Extension="jpeg" ContentType="image/jpeg"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
            '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
            '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
            '</Types>'),
        '_rels/.rels': (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{rel}/officeDocument" Target="word/document.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            f'<Relationship Id="rId3" Type="{rel}/extended-properties" Target="docProps/app.xml"/>'
            '</Relationships>'),
        'word/_rels/document.xml.rels': (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rIdStyles" Type="{rel}/styles" Target="styles.xml"/>'
            f'<Relationship Id="rIdSettings" Type="{rel}/settings" Target="settings.xml"/>'
            f'<Relationship Id="rIdNumbering" Type="{rel}/numbering" Target="numbering.xml"/>'
            f'<Relationship Id="rIdFooter" Type="{rel}/footer" Target="footer1.xml"/>'
            f'{images}</Relationships>'),
        'word/document.xml': writer.document_xml(),
        'word/styles.xml': STYLES,
        'word/settings.xml': _settings(writer.has_toc),
        'word/numbering.xml': writer.numbering_xml(),
        'word/footer1.xml': FOOTER,
        'docProps/core.xml': (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{esc(title)}</dc:title><dc:creator>{esc(author)}</dc:creator><dc:language>pl-PL</dc:language>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified></cp:coreProperties>'),
        'docProps/app.xml': (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
            '<Application>BiPOL Requiem</Application></Properties>'),
    }
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as package:
        for name, content in parts.items():
            package.writestr(name, content.encode('utf-8'))
        for i, (kind, data) in enumerate(writer.images, 1):
            package.writestr(f'word/media/obraz{i}.{"png" if kind == "png" else "jpeg"}', data, zipfile.ZIP_STORED)
    return buffer.getvalue()
