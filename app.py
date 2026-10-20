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

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False


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
    params = results["params"]
    
    student_name = request.args.get('student') or params.get('student_name') or 'Jan Kowalski'
    album_no = request.args.get('album') or params.get('album_no') or 'Nr Albumu'
    group_no = request.args.get('group') or params.get('group_no') or 'A – czwartek 8:15-9:00'
    supervisor = request.args.get('supervisor') or params.get('supervisor') or 'M.Figat'
    submission_date = request.args.get('date') or params.get('submission_date') or '14.12.2026'
    academic_year = request.args.get('academic_year') or params.get('academic_year') or '2026/27'
    return render_template(
        'report.html',
        res=results,
        params=params,
        student_name=student_name,
        album_no=album_no,
        group_no=group_no,
        supervisor=supervisor,
        submission_date=submission_date,
        academic_year=academic_year,
        selected_sections=selected_sections,
        report_assets={name: (Path(app.root_path) / path).read_text(encoding='utf-8').replace('</script', '<\\/script') for name, path in {
            'css': 'static/css/style.css',
            'core': 'static/js/studio-core.js',
            'visuals': 'static/js/studio-visuals.js',
            'didactic': 'static/js/didactic_data.js',
            'charts': 'static/js/charts.js',
        }.items()},
    )

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
    params = report_parameters()
    results = run_bipol_project(params)
    params = results["params"]
    bipol_projects = results.get("bipol_projects", {})
    
    # Dokładne 2-wierszowe nazwy projektów wg Rys. 2 i Rozdz. 2 w BIPOL1_Opis_Projektow.pdf (dr inż. M. Figat)
    project_titles = {
        "p1": ("Projekt 1", "Projekt Koncepcyjny", "Wybór konfiguracji, szkic i analiza trendów (5 pkt)"),
        "p2": ("Projekt 2", "Studium Wykonalności", "Profil misji, bilans masowy, dobór profilu i koszty (18 pkt)"),
        "p3": ("Projekt 3", "Projekt Wstępny i Analiza Masowa", "Rysunek w 3 rzutach, wyważenie i rozkład Schrenka (27 pkt)"),
        "p4": ("Projekt 4", "Charakterystyki aerodynamiczne samolotu", "Biegunowe, doskonałość i mechanizacja płata (15 pkt)"),
        "p5": ("Projekt 5", "Osiągi Samolotu", "Wykres ofertowy, zasięg i krytyczna ocena osiągów (15 pkt)"),
        "p6": ("Projekt 6", "Obwiednia Obciążeń Dopuszczalnych", "Obwiednia manewrowa, podmuchowa i pętla klapowa (20 pkt)"),
        "folder_cover": ("Informacja na teczkę", "Budowa i Projektowanie Obiektów Latających I", "Informacja na teczkę projektową wg Rys. 1 MEiL PW")
    }
    
    if p_id not in project_titles:
        abort(404)
    p_meta = project_titles.get(p_id, ("Projekt 1", "Projekt Koncepcyjny", "Sprawozdanie projektowe"))
    p_data = bipol_projects.get(p_id, {})
    
    student_name = request.args.get('student') or params.get('student_name') or 'Jan Kowalski'
    album_no = request.args.get('album') or params.get('album_no') or 'Nr Albumu'
    group_no = request.args.get('group') or params.get('group_no') or 'A – czwartek 8:15-9:00'
    supervisor = request.args.get('supervisor') or params.get('supervisor') or 'M.Figat'
    submission_date = request.args.get('date') or params.get('submission_date') or '14.12.2026'
    academic_year = request.args.get('academic_year') or params.get('academic_year') or '2026/27'
    aircraft_name = params.get('name', 'Nazwa Projektu')
    topic_id = params.get('topic_id', 33)
    
    return render_template(
        'project_report.html',
        p_id=p_id,
        project_line_1=p_meta[0],
        project_line_2=p_meta[1],
        project_title=f"{p_meta[0]}: {p_meta[1]}",
        project_subtitle=p_meta[2],
        p_data=p_data,
        res=results,
        params=params,
        student_name=student_name,
        album_no=album_no,
        group_no=group_no,
        supervisor=supervisor,
        submission_date=submission_date,
        academic_year=academic_year,
        aircraft_name=aircraft_name,
        topic_id=topic_id
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Startowanie serwera BIPOL Studio na porcie {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)
