"""Raport wybranych parametrów w przeglądarce. Uruchom po starcie serwera (requirements-browser.txt)."""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

from browser_helpers import navigate

parser = argparse.ArgumentParser(description='Karta obliczeń wybranych parametrów: wybór, podgląd i pobranie.')
parser.add_argument('--base-url', default='http://127.0.0.1:5000')
parser.add_argument('--browser-path', default=None)
parser.add_argument('--browser-channel', default=None, help='np. chrome, gdy nie zainstalowano Chromium Playwright')
parser.add_argument('--output', default='work/parameter-report-qa')
args = parser.parse_args()
BASE = args.base_url.rstrip('/')
OUT = Path(args.output)
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.browser_path, channel=args.browser_channel, headless=True, args=['--no-sandbox'])
    context = browser.new_context(viewport={'width': 1600, 'height': 1000}, accept_downloads=True)
    context.add_init_script("sessionStorage.setItem('bipol_session_initialized','true')")
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(BASE)
    page.wait_for_function('currentResults !== null')
    navigate(page, 'tab-reports')
    page.wait_for_selector('#paramCatalog details.param-project')
    assert page.locator('#paramCatalog .katex').count() > 20, 'Symbole i wartości powinny być złożone przez KaTeX.'

    # Wyszukiwanie po polskiej nazwie bez znaków diakrytycznych.
    page.locator('#paramSearch').fill('wydluzenie')
    assert page.locator('#paramCatalog .param-item').count() >= 1
    page.locator('#paramSearch').fill('')
    page.locator('[data-param-quick=aspect]').click()
    page.locator('[data-param-quick=mass]').click()
    status = page.locator('#paramSelectionStatus').inner_text()
    assert 'Wybrano 2' in status and 'Schemat iteracji masy' in status, status
    page.screenshot(path=str(OUT / 'panel.png'), full_page=False)

    with page.expect_popup() as popup_info:
        page.locator('[data-studio-action=preview-param-report]').click()
    report = popup_info.value
    report.on('pageerror', lambda e: errors.append('REPORT: ' + str(e)))
    report.wait_for_selector('[data-mass-iteration] figure.flow svg')
    report.wait_for_function("document.querySelectorAll('.formula .katex').length > 20")
    assert report.locator('.katex-error').count() == 0
    assert report.locator('[data-calc="AR"], [data-given="AR"]').count() >= 1
    assert report.locator('.iteration-heading').count() >= 2, 'Pełny zapis każdej iteracji.'
    report.close()

    # Sam wzór bez toku obliczeń, wybór całej sekcji i pobranie samodzielnego pliku.
    page.locator('#paramClear').click()
    page.locator('#paramSearch').fill('Geometria skrzydla')
    page.locator('[data-param-section="p3.wing"]').check()
    page.locator('[name=param-chain][value="0"]').check()
    with page.expect_download() as download_info:
        page.locator('[data-studio-action=download-param-report]').click()
    download_info.value.save_as(OUT / 'karta.html')
    html = (OUT / 'karta.html').read_text(encoding='utf-8')
    assert 'data-sheet-section="p3.wing"' in html and 'data-mass-iteration' not in html
    assert '<script src=' not in html and 'data-ref=' in html
    assert not errors, errors
    browser.close()
print('PARAMETER REPORT OK')
