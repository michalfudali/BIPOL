"""Real browser: every parameter field has an (i) card that contains its didactic hint."""
import argparse
from playwright.sync_api import sync_playwright
from browser_helpers import serve_in_process

parser=argparse.ArgumentParser()
parser.add_argument('--base-url',default='http://127.0.0.1:5011')
parser.add_argument('--browser-path',default='C:/Program Files/Google/Chrome/Application/chrome.exe')
parser.add_argument('--in-process',action='store_true',help='serve the Flask app inside the test, without a server')
args=parser.parse_args()

AUDIT="""(() => {
  const scopes = '#designForm, #projectWizardBackdrop, #bipol1Panel, #trendControls, #tab-trends, #aircraftEditorFields, #semesterWorkstation, #tab-reports';
  const missing = [], bad = [];
  document.querySelectorAll(scopes).forEach(scope => scope.querySelectorAll('input[id], select[id], textarea[id]').forEach(field => {
    if (['hidden', 'checkbox', 'file'].includes(field.type) || !PARAMETER_ENCYCLOPEDIA[BipolDidactic.keyFor(field.id)]) return;
    const group = field.closest('.input-group, .form-group, .wizard-field, .assumption-input-card') || field.closest('label');
    const label = document.querySelector(`label[for="${CSS.escape(field.id)}"]`) || group?.querySelector('label') || field.closest('label');
    if (!label?.querySelector('.info-circle-icon')) missing.push(field.id);
  }));
  const icons = [...document.querySelectorAll('.info-circle-icon[data-param]')];
  for (const icon of icons) {
    showDidacticPopover(icon.dataset.param, icon);
    const card = document.getElementById('popBody');
    const text = card.textContent;
    const hint = (icon.closest('.input-group, .form-group, .wizard-field, .assumption-input-card') || icon.closest('label'))
      ?.querySelector('.param-didactic-hint[data-hint-for]');
    const problems = ['Prosto mówiąc', 'Typowo'].filter(s => !text.includes(s));
    if (!/Gdy zwiększysz|Gdy zmienisz|Do czego służy|Wpływ na projekt/.test(text)) problems.push('skutek');
    if (/>\\s*[—–-]\\s*</.test(card.innerHTML)) problems.push('pusta sekcja');
    const plain = hint?.querySelector('strong')?.nextSibling?.textContent.trim();
    if (plain && !text.includes(plain)) problems.push('brak objaśnienia spod pola');
    if (problems.length) bad.push(`${icon.dataset.param}: ${problems.join(', ')}`);
  }
  scheduleHideDidacticPopover();
  return {missing, bad, icons: icons.length};
})()"""

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=args.browser_path,headless=True)
    page=browser.new_page(viewport={'width':1400,'height':1000})
    if args.in_process:serve_in_process(page,args.base_url)
    page.add_init_script("sessionStorage.setItem('bipol_session_initialized','true')")
    errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto(args.base_url)
    page.wait_for_function('typeof currentResults!=="undefined" && currentResults!==null',timeout=45000)
    page.wait_for_timeout(500)
    audit=page.evaluate(AUDIT)
    assert audit['icons']>150,audit
    assert not audit['missing'],audit['missing']
    assert not audit['bad'],audit['bad']

    # Kartoteka mówi, skąd wzięła się wartość parametru w bieżącym projekcie.
    state=page.evaluate("""(() => { const i = document.querySelector('#designForm .info-circle-icon[data-param="wing_area_m2"]');
      showDidacticPopover('wing_area_m2', i); return document.getElementById('popBody').textContent; })()""")
    assert 'W Twoim projekcie' in state and 'wyliczona przez program' in state,state

    # Pola rekordu bazy: ikonka przy nazwie, kartoteka nad oknem modalnym.
    page.evaluate('BipolAircraftEditor.open(null, {})')
    page.wait_for_function("document.getElementById('trendAircraftModal').open")
    icon=page.locator('label[for="ac_m0"] .info-circle-icon')
    assert icon.bounding_box()['y']<page.locator('#ac_m0').bounding_box()['y']
    icon.hover()
    page.wait_for_function("document.getElementById('didacticPopover').classList.contains('visible')")
    box=page.locator('#didacticPopover').bounding_box()
    assert page.evaluate(f"!!document.elementFromPoint({box['x']+box['width']/2},{box['y']+box['height']/2}).closest('#didacticPopover')")
    assert 'Do czego służy' in page.locator('#popBody').inner_text()
    page.keyboard.press('Escape')

    assert not errors,errors
    browser.close()
    print(f"OK: {audit['icons']} kartotek z objaśnieniami")
