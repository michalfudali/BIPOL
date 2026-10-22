"""
Aplikacja Webowa BIPOL Studio - Wstępne Projektowanie Samolotów
Wydział Mechaniczny Energetyki i Lotnictwa Politechniki Warszawskiej (MEiL PW)
Zakład Samolotów i Śmigłowców (ZSiS)
"""
import os
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, abort
from werkzeug.exceptions import BadRequest
from calculations import run_bipol_project, AIRCRAFT_PRESETS
from calculations.official_topics import ALL_TOPICS, OFFICIAL_CATEGORIES
from calculations.polish_law import catalog_for_frontend
from calculations.trends import reference_catalog, SOURCES, DATA
from calculations.trend_report import trend_chart
from calculations.report_assets import math_assets
from calculations.report_document import report_document, report_number, report_metadata, tex_number
from calculations.report_sketch import report_sketch
from calculations.drawing_sheet import drawing_sheet

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
app.jinja_env.globals['trend_chart'] = trend_chart
app.jinja_env.globals['math_assets'] = math_assets
app.jinja_env.filters['reportnum'] = report_number
app.jinja_env.filters['texnum'] = tex_number
app.jinja_env.filters['trendnum'] = lambda v, digits=3: f'{v:.{digits}f}' if isinstance(v, (int, float)) else '—'
app.jinja_env.globals['report_metadata'] = report_metadata
app.jinja_env.globals['report_sketch'] = report_sketch
app.jinja_env.globals['drawing_sheet'] = drawing_sheet


@app.context_processor
def designer_defaults():
    return {'designer_defaults': {f['key']: f['value'] for f in report_metadata({})}}


def report_parameters():
    if request.method == 'POST':
        return request.get_json(force=True)
    if request.args.get('params_json'):
        try:
            return json.loads(request.args['params_json'])
        except (TypeError, ValueError):
            raise ValueError('Nieprawidłowy JSON parametrów raportu.') from None
    preset_id = request.args.get('preset', 'pzl_kos')
    if preset_id not in AIRCRAFT_PRESETS:
        raise ValueError('Nieznany preset raportu.')
    return dict(AIRCRAFT_PRESETS[preset_id])


@app.errorhandler(ValueError)
@app.errorhandler(BadRequest)
def invalid_parameters(error):
    return jsonify(status='error', message=str(error)), 400

@app.route('/')
def index():
    return render_template(
        'index.html',
        presets=AIRCRAFT_PRESETS,
        categories=OFFICIAL_CATEGORIES,
        topics=ALL_TOPICS
    )

@app.route('/api/presets', methods=['GET'])
def get_presets():
    return jsonify(AIRCRAFT_PRESETS)

@app.route('/api/aircraft-classification', methods=['GET'])
def get_aircraft_classification():
    """Klasyfikacja statków powietrznych wg Dz. U. 2025 poz. 1137 (Tabele nr 1-3)."""
    return jsonify(catalog_for_frontend())

@app.route('/api/topics', methods=['GET'])
def get_topics():
    return jsonify({
        "categories": OFFICIAL_CATEGORIES,
        "topics": ALL_TOPICS
    })

@app.route('/api/constraints/suggestions', methods=['GET'])
def get_constraint_suggestions():
    category = request.args.get('category', 'cs23_level2')
    aircraft_type = request.args.get('aircraft_type', 'piston_ga')
    from calculations.constraints import get_initial_constraint_suggestions, WING_PLANFORMS, LOCKABLE_PARAMETERS
    return jsonify({
        'success': True,
        'suggestions': get_initial_constraint_suggestions(category, aircraft_type),
        'planforms': WING_PLANFORMS,
        'lockable_parameters': LOCKABLE_PARAMETERS
    })

@app.route('/api/aircraft', methods=['GET'])
def aircraft_catalog():
    return jsonify(reference_catalog())


@app.post('/api/trends/import')
def import_trend_observations():
    from calculations.trend_observations import import_observations
    try:
        if request.content_length and request.content_length > 1_100_000:
            raise ValueError('Plik uzupełnień może mieć maksymalnie 1 MB.')
        upload = request.files.get('file')
        if not upload:
            raise ValueError('Wybierz plik CSV wyeksportowany z arkusza.')
        text = upload.read(1_000_001).decode('utf-8-sig')
        if not text.strip():
            raise ValueError('Plik CSV jest pusty.')
        return jsonify(observations=import_observations(text))
    except (ValueError, UnicodeError) as error:
        return jsonify(error=str(error)), 400


@app.route('/download/aircraft/<source>/<kind>')
def aircraft_source_download(source, kind):
    if source not in SOURCES or kind not in ('data', 'license'):
        abort(404)
    if kind == 'license':
        return send_from_directory(DATA / 'licenses', SOURCES[source]['license_file'], as_attachment=True)
    return send_from_directory(DATA, source + '.json', as_attachment=True)

@app.route('/api/scraped-files', methods=['GET'])
def list_scraped_files():
    danilecki_dir = "scraped_materials/danilecki"
    bipol_dir = "scraped_materials/bipol"
    ml_dir = "scraped_materials/mechanika_lotu"
    zpk_dir = "scraped_materials/zpk_cad"
    
    def scan_dir(d, folder_key):
        items = []
        d = os.path.join(app.root_path, d)
        if os.path.exists(d):
            for f in sorted(os.listdir(d)):
                if f.lower().endswith('.pdf'):
                    items.append({
                        "name": f,
                        "path": f"/download/scraped/{folder_key}/{f}",
                        "size": os.path.getsize(os.path.join(d, f))
                    })
        return items

    danilecki_files = scan_dir(danilecki_dir, "danilecki")
    bipol_files = scan_dir(bipol_dir, "bipol")
    ml_files = scan_dir(ml_dir, "mechanika_lotu")
    zpk_files = scan_dir(zpk_dir, "zpk_cad")
    total = len(danilecki_files) + len(bipol_files) + len(ml_files) + len(zpk_files)

    return jsonify({
        "danilecki": danilecki_files,
        "bipol": bipol_files,
        "mechanika_lotu": ml_files,
        "zpk_cad": zpk_files,
        "total_count": total
    })

@app.route('/download/scraped/<folder>/<path:filename>')
def download_scraped(folder, filename):
    allowed = {
        "bipol": "bipol",
        "mechanika_lotu": "mechanika_lotu",
        "zpk_cad": "zpk_cad",
        "danilecki": "danilecki"
    }
    if folder not in allowed:
        abort(404)
    safe_folder = allowed[folder]
    directory = os.path.join(app.root_path, "scraped_materials", safe_folder)
    return send_from_directory(directory, filename, as_attachment=False)

@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.get_json(force=True)
    return jsonify(run_bipol_project(data))

@app.route('/report', methods=['GET', 'POST'])
def report():
    allowed_sections = ('p1', 'p2', 'p3', 'p4', 'p5', 'p6')
    requested = request.args.get('sections')
    selected_sections = list(allowed_sections) if requested is None else list(dict.fromkeys(requested.split(',')))
    if not selected_sections or any(section not in allowed_sections for section in selected_sections):
        raise ValueError('Wybierz poprawny zakres raportu: P1–P6.')
    params = report_parameters()
    results = run_bipol_project(params)
    return render_template('report.html', **document_context(results, selected_sections))


def document_context(results, sections, folder_cover=False):
    assets = {
        'css': 'static/css/report.css',
        'core': 'static/js/studio-core.js',
        'visuals': 'static/js/studio-visuals.js',
        'document': 'static/js/report.js',
    }
    return dict(res=results, params=results['params'], selected_sections=sections,
                doc=report_document(results, sections, request.args, folder_cover),
                report_assets={name: (Path(app.root_path) / path).read_text(encoding='utf-8')
                               .replace('</script', '<\\/script') for name, path in assets.items()})

@app.route('/holistic')
def holistic_portal():
    return render_template(
        'index.html',
        presets=AIRCRAFT_PRESETS,
        categories=OFFICIAL_CATEGORIES,
        topics=ALL_TOPICS,
        initial_portal_mode='holistic'
    )

@app.route('/projekty')
def projects_portal():
    return render_template(
        'index.html',
        presets=AIRCRAFT_PRESETS,
        categories=OFFICIAL_CATEGORIES,
        topics=ALL_TOPICS,
        initial_portal_mode='projects'
    )

@app.route('/report/project/<p_id>', methods=['GET', 'POST'])
def project_report(p_id):
    if p_id not in ('p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'folder_cover'):
        abort(404)
    results = run_bipol_project(report_parameters())
    sections = [] if p_id == 'folder_cover' else [p_id]
    return render_template('project_report.html',
                           **document_context(results, sections, p_id == 'folder_cover'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Startowanie serwera BIPOL Studio na porcie {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)
