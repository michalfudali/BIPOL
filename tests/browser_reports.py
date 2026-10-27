"""Offline submission reports: typesetting, author editing and real A4 output."""
import argparse
from pathlib import Path
import subprocess
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--base-url', default='http://127.0.0.1:5008')
parser.add_argument('--browser-path', default='/usr/bin/chromium')
args = parser.parse_args()
out = Path('work/report-checks'); out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.browser_path, headless=True, args=['--no-sandbox'])
    online = browser.new_context()
    params = online.request.get(args.base_url + '/api/presets').json()['pzl_kos']
    params.update(student_name='Anna Nowak', album_no='123456', group_no='A', supervisor='Prowadzący',
                  submission_date='22.10.2026', academic_year='2026/27', report_notes='Wariant do dalszego opracowania.')
    errors = []
    for part in ('p1','p2','p3','p4','p5','p6','full'):
        url = '/report' if part == 'full' else '/report/project/' + part
        response = online.request.post(args.base_url + url, data=params)
        assert response.ok, (part, response.status)
        html = response.text()
        offline = browser.new_context(offline=True, viewport={'width':1100,'height':900})
        page = offline.new_page(); page.on('pageerror', lambda error: errors.append(str(error)))
        page.set_content(html, wait_until='load'); page.evaluate('document.fonts.ready')
        assert not page.locator('.katex-error').count(), part
        assert page.locator('figure svg').count() > 0, part
        assert page.locator('[data-report-section]').count() == (6 if part == 'full' else 1)
        assert 'Anna Nowak' in page.locator('.cover').inner_text()
        assert 'Dane na stronie tytułowej są uzupełnione' in page.locator('#metadata-status').inner_text()
        page.locator('.report-toolbar summary').first.click()
        page.locator('[data-report-meta-input=student_name]').fill('Jan Nowak')
        assert 'Jan Nowak' in page.locator('.cover').inner_text()
        overflow = page.evaluate('''() => [...document.querySelectorAll('table,figure,.equation')].some(el=>{
          const r=el.getBoundingClientRect(),doc=document.querySelector('.document').getBoundingClientRect();
          return r.right>doc.right-25 || r.left<doc.left;
        })''')
        assert not overflow, part
        page.emulate_media(media='print')
        assert not page.locator('.report-toolbar').is_visible()
        pdf = out / (part + '.pdf')
        page.pdf(path=str(pdf), prefer_css_page_size=True, print_background=True)
        text = subprocess.check_output(['pdftotext','-enc','UTF-8','-layout',str(pdf),'-']).decode()
        pages = [s.strip() for s in text.split('\f') if s.strip()]
        assert 'Jan Nowak' in pages[0]
        assert 'Drukuj / zapisz PDF' not in text and 'Przed oddaniem uzupełnij' not in text
        assert all(len(s) > 180 for s in pages[1:]), (part, [len(s) for s in pages])
        print(f'{part.upper()}: {len(pages)} stron A4, wzory i wykresy offline, dane autora i czysty wydruk OK')
        offline.close()
    assert not errors, errors
    online.close(); browser.close()
