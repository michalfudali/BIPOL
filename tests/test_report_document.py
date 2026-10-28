"""Submission prose must reflect results, preserve authorship, and share one format."""
from datetime import date
from copy import deepcopy
import pytest
from app import app
from calculations import run_bipol_project
from calculations.presets import AIRCRAFT_PRESETS
from calculations.report_document import report_document, report_metadata, report_number, tex_number


@pytest.fixture(scope='module')
def result():
    return run_bipol_project(dict(AIRCRAFT_PRESETS['pzl_kos']))


def test_metadata_uses_real_input_and_date_instead_of_example_identity():
    fields = {f['key']: f['value'] for f in report_metadata({}, today=date(2027, 9, 30))}
    assert fields['student_name'] == fields['album_no'] == fields['supervisor'] == ''
    assert fields['submission_date'] == '30.09.2027'
    assert fields['academic_year'] == '2026/27'
    fields = {f['key']: f['value'] for f in report_metadata({'student_name': 'Anna Nowak'}, {'student': 'Jan Nowak'}, date(2027, 10, 1))}
    assert fields['student_name'] == 'Jan Nowak'
    assert fields['academic_year'] == '2027/28'


def test_conclusions_report_failed_criteria_and_governing_gusts(result):
    changed = deepcopy(result)
    changed['balance']['stability']['static_margin_aft_pct'] = 2
    changed['performance']['climb']['wy_max_ms'] = 0
    changed['geometry']['control_surfaces']['ailerons']['roll_authority_ok'] = False
    # Define the gust-governing scenario explicitly; a preset need not have it.
    limits = changed['envelope']['limits']
    limits['n_gust_max'] = limits['n_max'] + 1
    doc = report_document(changed, ['p3','p4','p5','p6'])
    assert 'nie jest spełnione' in ' '.join(doc['conclusions']['p3'])
    assert 'nie jest spełniony' in ' '.join(doc['conclusions']['p5'])
    assert 'mniejsza od przyjętego kryterium' in ' '.join(doc['conclusions']['p4'])
    assert 'Wymiarujące są również obciążenia podmuchowe' in ' '.join(doc['conclusions']['p6'])
    assert any('lotek' in c['parameter'] for c in doc['failed'])


def test_glider_prose_does_not_claim_engine_climb_or_breguet_range():
    r = run_bipol_project(dict(AIRCRAFT_PRESETS['glider_pw5']))
    doc = report_document(r, ['p2','p5'])
    assert 'Dla szybowca pominięto dobór mocy' in ' '.join(doc['conclusions']['p2'])
    assert 'Wznoszenia z napędem i samodzielnego startu nie rozpatrywano' in ' '.join(doc['conclusions']['p5'])


def test_numbers_are_polish_and_tex_decimal_comma_is_not_punctuation():
    assert report_number(1234.56) == '1\u202f234,56'
    assert tex_number(1234.56) == r'1\,234{,}56'
    assert report_number(None) == report_number(float('nan')) == '—'


def test_individual_and_combined_exports_share_findings_and_author_notes(result):
    params = {**result['params'], 'student_name': 'Anna Nowak', 'album_no': '123456',
              'report_notes': '<b>Moje wnioski</b>', 'source_notes': 'Instrukcja użytkowania, s. 12'}
    with app.test_client() as client:
        for url in ('/report?sections=p4', '/report/project/p4'):
            response = client.post(url, json=params)
            assert response.status_code == 200
            html = response.get_data(as_text=True)
            assert 'Anna Nowak' in html and '123456' in html
            assert '&lt;b&gt;Moje wnioski&lt;/b&gt;' in html
            assert 'Instrukcja użytkowania, s. 12' in html
            assert 'Inż. Projektant BIPOL' not in html and 'Jan Kowalski' not in html
            assert 'gwarantuje spełnienie' not in html and '✔' not in html
            assert '<caption>' in html and '<figcaption>' in html
            assert 'Podsumowanie i zgodność' in html and 'Bibliografia' in html
            assert '<script src=' not in html
