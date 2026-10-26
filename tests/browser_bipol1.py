"""Real browser: mass controls, drop, saved project, graph and mobile layout."""
import argparse
from playwright.sync_api import sync_playwright
from browser_helpers import navigate, reveal_details

parser=argparse.ArgumentParser()
parser.add_argument('--base-url',default='http://127.0.0.1:5011')
parser.add_argument('--browser-path',default='C:/Program Files/Google/Chrome/Application/chrome.exe')
args=parser.parse_args()

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=args.browser_path,headless=True)
    page=browser.new_page(viewport={'width':1400,'height':1000})
    page.add_init_script("sessionStorage.setItem('bipol_session_initialized','true')")
    errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto(args.base_url)
    page.wait_for_function('typeof currentResults!=="undefined" && currentResults?.mass?.mission_phases',timeout=45000)
    navigate(page,'tab-trends')
    page.locator('#empty_mass_model').select_option('coefficients')
    page.locator('#empty_mass_a').fill('0.95')
    page.locator('#empty_mass_c').fill('-0.05')
    page.locator('#bipol1Calculate').click()
    page.wait_for_function('currentResults?.mass?.empty_mass_law?.mode === "coefficients"')
    page.locator('#mass_method').select_option('iterative')
    page.locator('#payload_drop_kg').fill('20')
    page.evaluate("formBaseParams.m_cargo=100;document.getElementById('m_cargo').value=100")
    page.locator('#return_range_km').fill('100')
    page.locator('#bipol1Calculate').click()
    page.wait_for_function('currentResults.mass.m_payload_dropped===20')
    assert 'Zrzut' in page.locator('#bipol1Results').inner_text()
    page.reload()
    page.wait_for_function('currentResults?.mass?.m_payload_dropped===20')
    assert page.locator('#payload_drop_kg').input_value()=='20'
    navigate(page,'tab-trends')
    reveal_details(page.locator('#preliminary_polar_mode'))
    page.locator('#preliminary_polar_mode').select_option('reading')
    page.locator('#raymer_kmax').fill('14')
    page.locator('#bipol1Calculate').click()
    page.wait_for_function('currentResults.mass.preliminary_polar.mode==="reading"')
    assert page.evaluate('currentResults.mass.mission_assumptions.k_max_preliminary')==14
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth')<=395
    assert page.request.get(args.base_url+'/static/images/bipol1-raymer.png').ok
    assert page.request.get(args.base_url+'/static/images/bipol1-corke.png').ok
    assert not errors, errors
    print('PASS: coefficients, cargo drop, persistence, Raymer input, mobile, graph sources, JS errors')
    browser.close()
