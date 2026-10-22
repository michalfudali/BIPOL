"""Uruchom po starcie serwera; wymaga requirements-browser.txt i Chromium."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

from browser_helpers import navigate, edit_inputs, reveal_details

import argparse
parser=argparse.ArgumentParser(description='Test integracyjny BIPOL Studio w rzeczywistej przeglądarce.')
parser.add_argument('--base-url',default='http://127.0.0.1:5000')
parser.add_argument('--browser-path',default=None)
parser.add_argument('--output',default='work/studio-qa')
args=parser.parse_args()
BASE=args.base_url.rstrip('/')
OUT=Path(args.output);OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=args.browser_path,headless=True,args=['--no-sandbox'])
 context=browser.new_context(viewport={'width':1600,'height':1000},accept_downloads=True)
 context.add_init_script("sessionStorage.setItem('bipol_session_initialized','true')")
 page=context.new_page();errors=[];warnings=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('console',lambda msg:warnings.append(msg.text) if msg.type in ('error','warning') else None)
 page.goto(BASE);page.wait_for_timeout(800);print('INITIAL STATUS',page.locator('#calculationStatus').inner_text());page.wait_for_function('currentResults !== null')
 assert 'Mój projekt samolotu' in page.locator('#studioProjectName').inner_text()
 assert page.locator('.quick-preset-chip').count()==0
 # Zapis wariantów jest niezależny od późniejszej edycji parametrów.
 navigate(page, 'tab-variants')
 page.locator('#studioVariantName').fill('Bazowy')
 page.locator('#studioVariantForm button[type=submit]').click()
 page.wait_for_function("projectStore.read('bipol_studio_variants_v1',[]).length === 1")
 original=page.evaluate("projectStore.read('bipol_studio_variants_v1',[])[0].params.aspect_ratio")
 navigate(page, 'tab-p3')
 edit_inputs(page,'aspect_ratio').fill('9.5');page.locator('#calcBtn').click()
 page.wait_for_function('currentResults.params.aspect_ratio === 9.5')
 navigate(page, 'tab-variants')
 page.locator('#studioVariantName').fill('Większe wydłużenie')
 page.locator('#studioVariantForm button[type=submit]').click()
 page.wait_for_function("projectStore.read('bipol_studio_variants_v1',[]).length === 2")
 assert page.evaluate("projectStore.read('bipol_studio_variants_v1',[])[1].params.aspect_ratio")==original
 assert page.locator('#studioComparison table').count()==1
 projects_before=page.evaluate('getProjectsList().length')
 page.locator('[data-load-variant]').last.click()
 page.wait_for_function('getProjectsList().length > '+str(projects_before))
 page.wait_for_function('currentResults.params.name === "Bazowy"')
 print('VARIANTS, RESTORE OK')
 # Eksporty muszą zawierać prawdziwe dane i działać jako niezależne pliki.
 navigate(page, 'tab-reports')
 reveal_details(page.locator('#studioMeta_student_name'));page.locator('#studioMeta_student_name').fill('Anna Testowa')
 assert page.evaluate('getActiveProject().params.student_name')=='Anna Testowa'
 reveal_details(page.locator('#studioNotes'));page.locator('#studioNotes').fill('Wnioski: <script>alert("test")</script> — sprawdzić trymowanie.')
 page.locator('#studioSources').fill('Źródło własne: instrukcja, s. 21')
 assert page.evaluate('getActiveProject().editorial.notes').startswith('Wnioski:')
 for checkbox in page.locator('[name=studio-report-section]').all(): checkbox.set_checked(checkbox.input_value() in ['p3','p5'])
 with page.expect_download() as download_info:page.locator('[data-studio-action=download-report]').click()
 download=download_info.value;download.save_as(OUT/'raport.html')
 html=(OUT/'raport.html').read_text(encoding='utf-8')
 assert 'data-report-section="p3"' in html and 'data-report-section="p5"' in html
 assert 'data-report-section="p4"' not in html and '<script src=' not in html and '<link rel="stylesheet"' not in html
 assert '&lt;script&gt;alert' in html
 assert 'Anna Testowa' in html
 with page.expect_popup() as popup_info:page.locator('[data-studio-action=preview-report]').click()
 report=popup_info.value;report.on('pageerror',lambda e:errors.append('REPORT: '+str(e)))
 report.wait_for_function("document.getElementById('repGlideChart')?.querySelector('svg')")
 assert report.locator('#author-notes').count()==1
 report.close()
 reveal_details(page.locator('[data-studio-action=export-csv]'))
 with page.expect_download() as download_info:page.locator('[data-studio-action=export-csv]').click()
 download_info.value.save_as(OUT/'wyniki.csv')
 assert (OUT/'wyniki.csv').read_bytes().startswith(b'\xef\xbb\xbf')
 assert 'Szybowanie' in (OUT/'wyniki.csv').read_text(encoding='utf-8')
 with page.expect_download() as download_info:page.locator('[data-studio-action=export-json]').click()
 download_info.value.save_as(OUT/'projekt.json')
 assert 'Wnioski:' in json.loads((OUT/'projekt.json').read_text(encoding='utf-8'))['project']['editorial']['notes']
 navigate(page, 'tab-overview')
 page.locator('[data-aircraft-view=top]').click()
 with page.expect_download() as download_info:page.locator('[data-studio-action=export-svg]').click()
 download_info.value.save_as(OUT/'samolot.svg')
 svg=(OUT/'samolot.svg').read_text(encoding='utf-8');assert 'xmlns="http://www.w3.org/2000/svg"' in svg and 'RZUT Z GÓRY' in svg
 print('EXPORT CSV, SVG, HTML, JSON, PREVIEW OK')
 # Raport HTML bez aplikacji i bez żądań sieciowych.
 offline=browser.new_context(offline=True)
 offline_page=offline.new_page();offline_page.on('pageerror',lambda e:errors.append('OFFLINE: '+str(e)))
 offline_page.set_content(html, wait_until='load')
 offline_page.wait_for_function("document.getElementById('repGlideChart')?.querySelector('svg')")
 assert offline_page.locator('#repBlueprint svg').count()>0
 offline.close();print('OFFLINE REPORT OK')
 # Nowa obsługa szybowca z upstream, także po przełączeniu z powrotem.
 navigate(page, 'tab-p3')
 edit_inputs(page,'aircraft_type').select_option('glider')
 page.wait_for_function("currentResults.params.engine_type === 'none'")
 assert page.locator('#sfc').input_value()=='0'
 assert page.locator('#takeoff_run_m').input_value()=='0'
 navigate(page, 'tab-overview')
 assert 'Bez napędu' in page.locator('#studioProjectDescription').inner_text()
 navigate(page, 'tab-glide')
 assert page.locator('#studioGlideChart svg').count()==1
 for target in ['tab-p1-p2','tab-p3','tab-p4','tab-p5','tab-p6','tab-cad']:
  navigate(page,target);page.wait_for_timeout(80)
 navigate(page, 'tab-variants')
 assert page.locator('#studioComparison tbody tr').filter(has_text='Vmax').locator('td').nth(1).inner_text()=='—'
 navigate(page, 'tab-p3')
 edit_inputs(page,'aircraft_type').select_option('piston_ga')
 page.wait_for_function("currentResults.params.engine_type === 'prop' && currentResults.params.aircraft_type === 'piston_ga'")
 print('UPSTREAM GLIDER COMPATIBILITY OK')
 # Pozostałe moduły, tryb semestralny i responsywność.
 for target in page.locator('[data-studio-nav]').evaluate_all('(nodes) => nodes.map(n => n.dataset.studioNav)'):navigate(page,target);page.wait_for_timeout(100)
 reveal_details(page.locator('#btnModeProjects'));page.locator('#btnModeProjects').click()
 page.locator('#pill-p6').click()
 assert page.locator('#panel-p6').is_visible()
 navigate(page, 'tab-overview')
 for width in [1600,1280,768,390,320]:
  page.set_viewport_size({'width':width,'height':950})
  page.wait_for_timeout(120)
  if width<1100:
   page.locator('#studioMenuToggle').click()
   assert page.locator('#studioMenuToggle').get_attribute('aria-expanded')=='true'
   navigate(page, 'tab-reports')
   assert 'studio-nav-open' not in page.locator('body').get_attribute('class')
   page.locator('#studioMenuToggle').click();navigate(page, 'tab-overview')
  page.screenshot(path=str(OUT/f'kokpit-{width}.png'),animations='disabled')
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
 print('NAVIGATION, SEMESTER, WIDTHS OK')
 page.reload();page.wait_for_function('currentResults !== null')
 page.locator('#studioMenuToggle').click();navigate(page, 'tab-reports')
 assert 'Wnioski:' in page.locator('#studioNotes').input_value()
 print('PERSISTENCE OK')
 page.locator('#studioMenuToggle').click();navigate(page, 'tab-variants')
 for count in range(3,9):
  page.locator('#studioVariantName').fill(f'Wariant {count}')
  page.locator('#studioVariantForm button[type=submit]').click()
  page.wait_for_function(f"projectStore.read('bipol_studio_variants_v1',[]).length === {count}")
 page.locator('#studioVariantForm button[type=submit]').click()
 page.wait_for_function("document.getElementById('studioMessage').textContent.includes('8 wariantów')")
 assert page.evaluate("projectStore.read('bipol_studio_variants_v1',[]).length")==8
 page.locator('[data-delete-variant]').first.click()
 assert page.evaluate("projectStore.read('bipol_studio_variants_v1',[]).length")==7
 print('EIGHT VARIANT LIMIT OK')
 print('ERRORS',errors);print('WARNINGS',warnings)
 assert not errors
 context.close()
 # Niedostępny localStorage nie może wyświetlać informacji o poprawnym trwałym zapisie.
 blocked=browser.new_context(viewport={'width':1280,'height':900})
 blocked.add_init_script("sessionStorage.setItem('bipol_session_initialized','true');Object.defineProperty(window,'localStorage',{get(){throw new DOMException('blocked','SecurityError')}})")
 q=blocked.new_page();q.on('pageerror',lambda e:errors.append('STORAGE: '+str(e)))
 q.goto(BASE);q.wait_for_function('currentResults !== null')
 assert 'Tylko pamięć' in q.locator('#projectAutoSaveStatus').inner_text()
 q.locator('[data-studio-nav=tab-variants]').click();q.locator('#studioVariantForm button[type=submit]').click()
 q.wait_for_function("projectStore.read('bipol_studio_variants_v1',[]).length===1")
 print('BLOCKED STORAGE FALLBACK OK');assert not errors
 blocked.close();browser.close()
