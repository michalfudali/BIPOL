"""Unit and integration tests for editable Word (DOCX) export and in-window report editor."""
import base64
import re
import struct
import xml.etree.ElementTree as ET
import zlib
import zipfile
from io import BytesIO

from app import app
from calculations.report_docx import build_docx

W_NS = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
M_NS = '{http://schemas.openxmlformats.org/officeDocument/2006/math}'


def _tiny_png(width=40, height=20):
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    raw = b''.join(b'\x00' + b'\xff\xff\xff' * width for _ in range(height))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')


def test_build_docx_produces_valid_ooxml_package_with_omml_and_seq_fields():
    png_b64 = base64.b64encode(_tiny_png(120, 60)).decode('ascii')
    html = f"""
    <header class="cover"><div class="cover-frame">
      <div class="cover-author"><div>Jan Testowy</div><div>Nr albumu: 321654</div></div>
      <div class="cover-project"><h1>Projekt 1<br>Projekt koncepcyjny</h1><p class="aircraft-name">PZL-102B Kos</p></div>
      <div class="cover-date">Data oddania projektu: 27.10.2026</div><div class="cover-grade">Ocena: ………………</div>
    </div></header>
    <nav class="toc"><h2>Spis treści</h2><ol><li>P1. Projekt koncepcyjny</li></ol></nav>
    <section class="report-part" id="report-p1">
      <h2>P1. Projekt koncepcyjny</h2>
      <p>Poprawiona treść z indeksem <math><msub><mi>C</mi><mi>z</mi></msub></math> oraz kątem <math><mn>20</mn><msup><mrow></mrow><mo>∘</mo></msup></math>.</p>
      <table><caption>Założenia wyjściowe</caption><thead><tr><th>Parametr</th><th class="number">Wartość</th></tr></thead>
      <tbody><tr><td>Zasięg</td><td class="number">650,0</td></tr></tbody></table>
      <table><caption>Druga tabela</caption><tbody><tr><td>Masa</td><td class="number">630,0</td></tr></tbody></table>
      <div class="calc">
        <p class="calc-label">Pochodna stateczności <span class="calc-source">[BIPOL_3]</span></p>
        <div class="equation"><div class="formula">
          <math display="block"><mtable columnalign="right left">
            <mtr><mtd><msub><mrow><mfrac><mrow><mi mathvariant="normal">d</mi><msub><mi>C</mi><mi>m</mi></msub></mrow><mrow><mi mathvariant="normal">d</mi><msub><mi>C</mi><mi>z</mi></msub></mrow></mfrac><mo fence="true">∣</mo></mrow><mi>p</mi></msub></mtd><mtd><mo>=</mo><msqrt><mfrac><msub><mi>S</mi><mi>H</mi></msub><mi>S</mi></mfrac></msqrt></mtd></mtr>
          </mtable></math>
        </div></div>
        <p class="calc-note">Uwaga do obliczenia.</p>
      </div>
      <figure><img src="data:image/png;base64,{png_b64}" data-width-mm="150" alt="Schemat"/><figcaption>Schemat w trzech rzutach.</figcaption></figure>
    </section>
    """
    docx_bytes = build_docx(html, title='PZL-102B Kos — Projekt 1', author='Jan Testowy')
    with zipfile.ZipFile(BytesIO(docx_bytes)) as zf:
        names = set(zf.namelist())
        assert 'word/document.xml' in names
        assert 'word/media/obraz1.png' in names
        for name in names:
            if name.endswith(('.xml', '.rels')):
                ET.fromstring(zf.read(name))
        doc_xml = zf.read('word/document.xml').decode('utf-8')
        settings_xml = zf.read('word/settings.xml').decode('utf-8')

    assert 'SEQ Tabela \\* ARABIC' in doc_xml
    assert 'SEQ Rysunek \\* ARABIC' in doc_xml
    assert 'SEQ Wzor \\* ARABIC' in doc_xml
    assert 'TOC \\o "1-2"' in doc_xml
    assert '<w:updateFields w:val="true"/>' in settings_xml
    assert '<m:eqArr>' in doc_xml
    assert '<m:rad>' in doc_xml
    assert '<m:f>' in doc_xml
    assert '<m:endChr m:val="∣"/>' in doc_xml
    assert '°' in doc_xml
    assert not re.search(r'<m:e/>|<m:e></m:e>', doc_xml)


def test_report_docx_endpoint_and_editor_controls():
    with app.test_client() as client:
        r = client.get('/report?sections=p1')
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert 'id="edit-report"' in html
        assert 'id="download-docx"' in html
        assert 'BipolReportEditor' in html

        bad = client.post('/report/docx', json={'html': '   '})
        assert bad.status_code == 400

        res = client.post('/report/docx', json={
            'html': '<section><h2>P1</h2><p>Własny tekst autora.</p></section>',
            'title': 'Test Raport',
            'author': 'Anna Nowak',
        })
        assert res.status_code == 200
        assert res.mimetype == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        with zipfile.ZipFile(BytesIO(res.data)) as zf:
            doc_xml = zf.read('word/document.xml').decode('utf-8')
            core_xml = zf.read('docProps/core.xml').decode('utf-8')
            assert 'Własny tekst autora.' in doc_xml
            assert 'Anna Nowak' in core_xml

