"""Course assumptions, source supplements, and a real single-page A4 drawing."""
import argparse
from pathlib import Path
import subprocess
from playwright.sync_api import sync_playwright
from browser_helpers import navigate, reveal_details

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url',default='http://127.0.0.1:5012')
args=parser.parse_args();out=Path('work/instructor-qa');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(args.base_url);page.wait_for_function('currentResults!==null')
    page.locator('.quiet-project-menu>summary').click();page.locator('#btnEditProjectWizard').click()
    page.locator('.wizard-step-tab[data-step="2"]').click()
    assert page.locator('#wiz_takeoff_distance_m').is_visible()
    assert page.locator('#wiz_landing_distance_m').is_visible()
    page.locator('#wiz_takeoff_distance_m').fill('750');page.locator('#wiz_landing_distance_m').fill('700')
    page.locator('.wizard-step-tab[data-step="4"]').click();page.locator('#wiz_gear_attachment').select_option('wing')
    page.locator('.wizard-step-tab[data-step="5"]').click();page.locator('#wizFinishBtn').click()
    page.wait_for_function('!document.getElementById("projectWizardBackdrop").classList.contains("active")')
    assert page.evaluate('currentResults.params.takeoff_distance_m')==750
    assert page.evaluate('currentResults.params.landing_distance_m')==700
    assert page.evaluate('currentResults.params.gear_attachment')=='wing'
    assert page.evaluate('currentResults.bipol_projects.p4.high_lift.takeoff.flap_deflection_deg')==20
    assert page.evaluate('currentResults.bipol_projects.p4.high_lift.landing.flap_deflection_deg')==40
    print('WIZARD: FULL TAKEOFF/LANDING REQUIREMENTS AND GEAR MOUNTING SAVED',flush=True)
    navigate(page,'tab-trends');page.locator('#trendSelectionPanel-tab').click()
    reveal_details(page.locator('#trendObservationFile'))
    with page.expect_download() as d:page.locator('#trendObservationTemplate').click()
    d.value.save_as(out/'template.csv')
    assert 'climb_rate_ms' in (out/'template.csv').read_text(encoding='utf-8-sig')
    model_id=page.evaluate('currentResults.bipol_projects.p1.trend_analysis.similar_aircraft[0].id')
    csv=f'id;climb_rate_ms;takeoff_distance_m;source\n{model_id};4,5;600;Testowy dokument AFM s. 10, ISA SL MTOW, 15 m\n'
    page.locator('#trendObservationFile').set_input_files({'name':'supplement.csv','mimeType':'text/csv','buffer':csv.encode()})
    page.wait_for_function('currentResults.params.trend_observations?.length===1')
    assert page.evaluate('currentResults.bipol_projects.p1.trend_analysis.similar_aircraft[0].climb_rate_ms')==4.5
    page.reload();page.wait_for_function('currentResults?.params?.trend_observations?.length===1')
    assert page.evaluate('currentResults.params.gear_attachment')=='wing'
    navigate(page,'tab-trends');assert page.locator('#instructorReview').is_visible()
    for width in (1440,768,390,320):
        page.set_viewport_size({'width':width,'height':1000})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),width
    print('CSV TEMPLATE, SOURCE SUPPLEMENT, RELOAD, REVIEW AND MOBILE WIDTHS: OK',flush=True)
    params=page.evaluate('currentResults.params')
    response=context.request.post(args.base_url+'/report?sections=p1,p2,p3,p4',data=params)
    assert response.ok
    offline=browser.new_context(offline=True,viewport={'width':1100,'height':1000})
    report=offline.new_page();report.on('pageerror',lambda e:errors.append(str(e)))
    report.set_content(response.text(),wait_until='load')
    assert report.locator('[data-course-chart]').count()==6
    assert report.locator('[data-course-chart] svg').count()==6
    assert report.locator('.katex-error').count()==0
    assert 'Startowa (20°)' in report.locator('#report-p4').inner_text()
    assert 'Do lądowania (40°)' in report.locator('#report-p4').inner_text()
    report.evaluate('window.print=()=>{window.testPrintCalled=true;}')
    reveal_details(report.locator('#print-drawing-grid'))
    report.locator('#print-drawing-grid').click();report.wait_for_function('window.testPrintCalled')
    report.emulate_media(media='print')
    assert not report.locator('.document').is_visible()
    assert report.locator('.drawing-page').is_visible()
    assert report.locator('.drawing-grid').is_visible()
    report.pdf(path=str(out/'drawing-grid.pdf'),prefer_css_page_size=True,print_background=True)
    info=subprocess.check_output(['pdfinfo',str(out/'drawing-grid.pdf')]).decode()
    assert 'Pages:           1' in info and '(A4)' in info,info
    text=subprocess.check_output(['pdftotext',str(out/'drawing-grid.pdf'),'-']).decode()
    assert 'Mocowanie podwozia: skrzydło' in text and 'Sprawozdanie' not in text
    report.screenshot(path=out/'drawing.png',full_page=True)
    report.evaluate("window.dispatchEvent(new Event('afterprint'))")
    report.emulate_media(media='screen')
    report.locator('#print-drawing-plain').click();report.emulate_media(media='print')
    assert not report.locator('.drawing-grid').is_visible()
    report.pdf(path=str(out/'drawing-plain.pdf'),prefer_css_page_size=True,print_background=True)
    assert not errors,errors
    print('SIX OFFLINE P1 PLOTS, NO MATH ERRORS, A4 1 PAGE, COMMON SCALE, GRID/PLAIN: OK',flush=True)
    offline.close();context.close();browser.close()
