"""Shared navigation helpers for the focused workspace UI."""
def reveal_details(locator):
    for details in locator.locator('xpath=ancestor::details').all():
        if details.get_attribute('open') is None:
            details.locator(':scope > summary').click()


def navigate(page, target):
    menu=page.locator('#studioMenuToggle')
    if page.viewport_size['width']<=1100 and menu.get_attribute('aria-expanded')!='true':
        menu.click()
    button=page.locator(f'[data-studio-nav="{target}"]')
    reveal_details(button)
    button.click()


def edit_inputs(page, field):
    navigate(page,'tab-inputs')
    locator=page.locator('#'+field)
    bodies=locator.locator('xpath=ancestor::div[contains(@class,"module-body")]')
    if bodies.count() and 'collapsed' in (bodies.first.get_attribute('class') or ''):
        bodies.first.locator('xpath=preceding-sibling::*[1]').click()
    if not locator.is_visible():page.locator('#modeAdvancedBtn').click()
    return locator
