"""Actual browser: grade planner, isolated notes, freshness, report and iteration."""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright
from browser_helpers import navigate, edit_inputs

parser = argparse.ArgumentParser()
parser.add_argument('--base-url', default='http://127.0.0.1:5012')
parser.add_argument('--browser-path', default='C:/Program Files/Google/Chrome/Application/chrome.exe')
args = parser.parse_args()

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.browser_path, headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    page.add_init_script("sessionStorage.setItem('bipol_session_initialized','true')")
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(args.base_url)
    page.wait_for_function('currentResults?.submission_review?.signature', timeout=45000)
    source_id = page.evaluate('getActiveProjectId()')
    navigate(page, 'tab-coursework')
    for key, maximum in [('p1', 5), ('p2', 18), ('p3', 27), ('p4', 15), ('p5', 15), ('p6', 20)]:
        page.locator('#courseworkScore_' + key).fill(str(maximum))
    page.locator('#courseworkQuizPoints').fill('91')
    page.locator('#courseworkQuizzesPassed').select_option('yes')
    page.wait_for_function("document.getElementById('courseworkGrade').textContent.includes('5,0') && document.getElementById('courseworkGrade').textContent.includes('191,0')")
    page.locator('#courseworkScore_p1').fill('0')
    page.wait_for_function("document.getElementById('courseworkGrade').textContent.includes('2,0')")
    page.locator('#courseworkScore_p1').fill('5')
    page.locator('#courseworkFilter').select_option('all')
    item = page.locator('#courseworkItem_p3_1')
    item.locator('summary').click()
    note = item.locator('textarea')
    note.fill('Arkusz P3, trzy rzuty i profil 200 mm; uzasadnienie autora.')
    assert item.locator('.coursework-state').inner_text() == 'Do przeglądu'
    before_signature = page.evaluate('currentResults.submission_review.signature')
    page.reload()
    page.wait_for_function('currentResults?.submission_review?.signature', timeout=45000)
    navigate(page, 'tab-coursework')
    page.locator('#courseworkFilter').select_option('all')
    item = page.locator('#courseworkItem_p3_1')
    assert item.locator('.coursework-state').inner_text() == 'Do przeglądu'
    assert page.evaluate('currentResults.submission_review.signature') == before_signature
    assert page.locator('#courseworkScore_p1').input_value() == '5'

    field = edit_inputs(page, 'range_km')
    field.fill(str(float(field.input_value()) + 10))
    navigate(page, 'tab-coursework')
    assert page.locator('#courseworkIterate').is_disabled()
    assert page.locator('#courseworkEvidence_p3_1').is_disabled()
    page.locator('#tab-coursework [data-studio-action="recalculate"]').click()
    page.wait_for_function(f'currentResults?.submission_review?.signature !== {before_signature!r} && !document.getElementById("courseworkIterate").disabled')
    page.locator('#courseworkFilter').select_option('all')
    item = page.locator('#courseworkItem_p3_1')
    assert item.locator('.coursework-state').inner_text() == 'Sprawdź po zmianie wariantu'
    item.locator('summary').click()
    item.locator('[data-coursework-confirm]').click()
    assert item.locator('.coursework-state').inner_text() == 'Do przeglądu'

    # Report generation recalculates, so check freshness across that boundary too.
    response = page.request.post(args.base_url + '/report?sections=p3', data=page.evaluate('collectFormData()'))
    assert response.ok
    html = response.text()
    assert 'Arkusz P3, trzy rzuty' in html and 'Odniesienie pochodzi z innego wariantu' not in html
    assert 'Ocena według wpisanych punktów' not in html
    report = browser.new_page(viewport={'width': 1000, 'height': 900})
    report.set_content(html, wait_until='networkidle')
    report.wait_for_function('document.querySelectorAll("figure svg").length>0')
    assert not report.locator('.katex-error').count()
    assert report.locator('#submission-review').is_visible()
    output = Path('work/coursework-review')
    output.mkdir(parents=True, exist_ok=True)
    report.pdf(path=str(output / 'p3.pdf'), format='A4', print_background=True)
    report.close()

    # A new variant cannot inherit awarded grades from a different project.
    page.locator('#courseworkIterate').click()
    page.wait_for_function(f'getActiveProjectId() !== {source_id!r}', timeout=45000)
    page.wait_for_function('currentResults?.params?.name?.includes("P2←P4") && !document.getElementById("courseworkIterate").disabled', timeout=45000)
    assert page.locator('#courseworkScore_p1').input_value() == ''
    assert page.evaluate(f'getProjectsList().find(p => p.id === {source_id!r}).params.coursework.scores.p1') == 5
    assert page.evaluate('getActiveProject().iteration.source_project_id') == source_id

    for width in (1440, 390, 320):
        page.set_viewport_size({'width': width, 'height': 950})
        assert page.evaluate('document.documentElement.scrollWidth') <= width + 1
    page.screenshot(path=str(output / 'mobile.png'), full_page=True)
    page.set_viewport_size({'width': 1440, 'height': 1000})
    page.screenshot(path=str(output / 'desktop.png'), full_page=True)
    assert not errors, errors
    browser.close()
    print('PASS: grade 191/200, zero-project gate, saved evidence, stale basis, report/PDF, isolated iteration, desktop/mobile, no JS errors')
