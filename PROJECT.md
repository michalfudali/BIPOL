# Project: BIPOL Studio Trend Analysis Integration & Aircraft Database Editor

## Architecture
BIPOL Studio is an aircraft preliminary design platform with a Flask backend and a reactive single-page frontend.
The Trend Analysis Integration consists of four main architectural subsystems:
1. **Statistical Suggestions Engine (`calculations/trends.py`, `app.py`)**:
   - Computes empirical parameter suggestions across all 7 aircraft classes (`piston_ga`, `turboprop_regional`, `jet_business`, `jet_transport`, `glider`, `motoglider`, `uav`).
   - Supports power-law ($\ln y = \ln A + C \ln x$) and linear regressions using Weighted Ordinary Least Squares with centered sums ($S_{xx}, S_{yy}$).
   - Exposes `GET /api/trends/suggestions` returning dynamic predictions, LaTeX equations, $R^2$, sample counts $N$, distributions, and literature ranges.
2. **Server-Side Aircraft Database & CRUD Persistence (`calculations/aircraft_store.py`, `calculations/aircraft_db.py`, `app.py`, `data/aircraft/aircraft.sqlite3`)**:
   - Manages 870+ reference aircraft records in a SQLite database (tables `sources`, `aircraft`; source per record via foreign key).
   - Every Create, Update, Delete is one SQLite transaction; `STRICT` tables and `CHECK` constraints repeat the validation rules.
   - Enforces physical and structural validation rules ($0 < m_e < m_0$, $S > 0$, $b > 0$, required identifiers, engine type mutual exclusivity).
   - `load_aircraft()` reloads the catalogue whenever `catalog_state.revision` changes (set by triggers on every write), so recalculation reflects edits from any process.
3. **Dual-Location UI Integration (`templates/`, `static/js/`)**:
   - **Location 1 (Module 1 P1 Mission Inputs & Project Wizard)**: Trend suggestion recommendation cards and "Zastosuj z trendów" action buttons that populate inputs, synchronize `BipolDesignBasis.sync()`, and trigger `performCalculation()`.
   - **Location 2 (Baza i trendy Transfer Panel)**: Dedicated panel `#trendTransferPanel` in the Results sub-panel comparing regression predictions $y_{trend}$ with active project values $y_{proj}$, showing delta badges and one-click injection.
   - **Database Editor UI**: In `#trendSelectionPanel`, a searchable, filterable table with modal dialog (`#aircraftEditorModal`) for Add/Edit and Delete confirmations, connected to REST endpoints with live chart redrawing.
4. **Automated Testing & Python 3.11 Compatibility (`tests/`, `pytest.ini`, `.github/workflows/tests.yml`)**:
   - Automated unit, integration, and regression test suites.
   - Python 3.11 verification with 100% pass rate in `pytest tests/`, run in CI on every push.

## Code Layout
- `calculations/trends.py` — Core trend analysis and regression algorithms.
- `calculations/aircraft_db.py` — Database service for atomic CRUD operations and validation.
- `app.py` — Flask application exposing REST endpoints (`/api/trends/suggestions`, `/api/aircraft`, `/api/aircraft/<id>`).
- `calculations/aircraft_store.py` — SQLite schema, connections, transactions and row mapping.
- `data/aircraft/aircraft.sqlite3` — Persistent aircraft storage (sources: `fast`, `cado`, `motogliders`, `geometry_trends`).
- `tools/aircraft_db.py` — Database check, SQL dump and per-source JSON export.
- `templates/inputs_panel.html` — Module 1 UI template containing trend suggestions container.
- `templates/trends_panel.html` — Trends tab template containing Transfer Panel and Editor elements.
- `templates/wizard_basis.html` & `templates/index.html` — Project Wizard templates for trend default adoption.
- `static/js/trends.js` — Trends visualization, SVG charting, Transfer Panel, and CRUD editor client logic.
- `static/js/constraints-ui.js` & `static/js/app.js` — Module 1 suggestions rendering, action button binding, and reactive recalculation pipeline.
- `pytest.ini` — Root pytest configuration setting `pythonpath = .`.
- `tests/test_trend_suggestions.py` — Unit tests for R1 statistical suggestions engine and API.
- `tests/test_aircraft_crud.py` — Unit & integration tests for R3 CRUD operations, validation, and persistence.
- `tests/test_trend_e2e.py` — End-to-end integration tests verifying dual-location adoption and reactive recalculation.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Empirical Parameter Regressions | Compute $W/S$, $\Lambda$, $m_e/m_0$, $P/W$, $T/W$, $V_H$, aileron, elevator, rudder ratios across 7 classes | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Suggestions REST Endpoint | `GET /api/trends/suggestions` returning values, equations, $N$, $R^2$, and distributions | M1 | ORIGINAL_REQUEST §R1 |
| 3 | Small Cohort Fallback Handling | Statistical fallback (mean/median/literature) for small classes ($N < 3$) such as UAV/glider | M1 | ORIGINAL_REQUEST §R1 & Survey |
| 4 | Atomic CRUD Engine | Transactional SQLite writes to `data/aircraft/aircraft.sqlite3` (originally atomic JSON file replacement) | M2 | ORIGINAL_REQUEST §R3 |
| 5 | CRUD REST Endpoints | `POST /api/aircraft`, `GET /api/aircraft/<id>`, `PUT /api/aircraft/<id>`, `DELETE /api/aircraft/<id>` | M2 | ORIGINAL_REQUEST §R3 |
| 6 | Database Input Validation | Reject negative masses, zero wing areas, missing required identifiers, duplicate IDs | M2 | ORIGINAL_REQUEST §R3 & Acceptance Criteria |
| 7 | In-Memory Cache Invalidation | Live cache clearing via `load_aircraft.cache_clear()` on every CRUD mutation | M2 | ORIGINAL_REQUEST §R3 |
| 8 | Module 1 Trend Suggestions UI | Recommendation cards & "Zastosuj z trendów" action buttons in Module 1 (P1 mission inputs) | M3 | ORIGINAL_REQUEST §R2 |
| 9 | Project Wizard Trend Adoption | One-click trend suggestion adoption buttons in Project Wizard steps (1, 2, 4) | M3 | ORIGINAL_REQUEST §R2 |
| 10 | Baza i trendy Transfer Panel | Dedicated comparison panel ($y_{trend}$ vs $y_{proj}$) with delta badges and push-to-project buttons | M3 | ORIGINAL_REQUEST §R2 |
| 11 | Reference Aircraft Editor UI | Searchable, filterable table with modal dialog (`#aircraftEditorModal`) for Add/Edit/Delete | M3 | ORIGINAL_REQUEST §R3 |
| 12 | Reactive Client Recalculation | Instant redrawing of SVG trend plots and recalculation without page reload | M3 | ORIGINAL_REQUEST §R3 |
| 13 | Pytest Configuration & 100% Pass Rate | `pytest.ini` with `pythonpath = .` ensuring 100% pass rate in `pytest tests/` on Python 3.11 | M4 | ORIGINAL_REQUEST §R4 |
| 14 | Regression Script Pass Rate | Fix cargo/baggage parameter discrepancy (one-off script, removed with `scratch/`) | M4 | ORIGINAL_REQUEST §R4 |
| 15 | E2E Regression & CRUD Test Suite | Comprehensive opaque-box test suite verifying all CRUD, suggestion, and adoption workflows | M4 | ORIGINAL_REQUEST §R4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Statistical Parameter Suggestions Engine | Engine logic in `calculations/trends.py`, endpoint `GET /api/trends/suggestions` in `app.py`, unit tests | None | DONE |
| M2 | Aircraft Database CRUD & Recalculation | Service `calculations/aircraft_db.py`, endpoints in `app.py`, validation, cache clearing, CRUD tests | None | IN_PROGRESS |
| M3 | Dual-Location UI Integration & Editor | Module 1 & Wizard buttons, Baza i trendy Transfer Panel, Modal Editor, reactive SVG refresh | M1, M2 | PLANNED |
| M4 | E2E Test Suite Pass & Hardening | Full E2E test verification (Tiers 1-4), pytest compatibility, Tier 5 hardening | M1, M2, M3 | PLANNED |

## Interface Contracts

### M1: Suggestions API (`/api/trends/suggestions`)
- **Request**: `GET /api/trends/suggestions?aircraft_type=<class>&m0=<float>&wing_configuration=<str>`
- **Query Parameters**:
  - `aircraft_type`: Required string (`piston_ga`, `turboprop_regional`, `jet_business`, `jet_transport`, `glider`, `motoglider`, `uav`).
  - `m0`: Optional float ($m_0 \ge 0$, kg). If supplied, dynamic regression evaluation is performed.
  - `wing_configuration`: Optional string (`cantilever`, `strut_braced`).
- **Response Format**:
  ```json
  {
    "status": "ok",
    "aircraft_type": "piston_ga",
    "m0": 1150.0,
    "suggestions": {
      "ws": {
        "key": "ws",
        "name": "Wing Loading",
        "symbol": "W/S",
        "unit": "kg/m²",
        "suggested_value": 88.5,
        "model_type": "power",
        "equation": "W/S = 3.12 · m0^0.47",
        "r2": 0.7387,
        "n": 67,
        "stats": {"min": 45.0, "max": 160.0, "mean": 86.2, "median": 85.0},
        "typical_range": [60.0, 130.0]
      },
      "ar": { ... },
      "me_m0": { ... },
      "pw": { ... },
      "tw": { ... },
      "vh": { ... },
      "b_ail_ratio": { ... },
      "c_ail_ratio": { ... },
      "c_e_ratio": { ... },
      "c_r_ratio": { ... },
      "dihedral_deg": { ... }
    }
  }
  ```
- **Error Responses**:
  - HTTP 400: `{"status": "error", "message": "Unknown aircraft_type: ..."}`

### M2: Aircraft Database Service & REST API
- **Endpoints**:
  - `GET /api/aircraft`: returns reference catalog with array of aircraft and metadata.
  - `GET /api/aircraft/<id>`: returns single aircraft JSON object.
  - `POST /api/aircraft`: creates new aircraft record.
    - Status 201 Created on success: `{"status": "ok", "message": "Aircraft created", "record": {...}}`
    - Status 400 Bad Request if validation fails: `{"status": "error", "message": "Validation failed: ..."}`
    - Status 409 Conflict if ID already exists: `{"status": "error", "message": "Aircraft with id '...' already exists"}`
  - `PUT /api/aircraft/<id>`: updates existing aircraft record.
    - Status 200 OK on success: `{"status": "ok", "message": "Aircraft updated", "record": {...}}`
    - Status 400 Bad Request on validation failure.
    - Status 404 Not Found if record does not exist.
  - `DELETE /api/aircraft/<id>`: deletes aircraft record from disk.
    - Status 200 OK on success: `{"status": "ok", "message": "Aircraft deleted", "id": "..."}`
    - Status 404 Not Found if record does not exist.
- **Validation Rules**:
  - `id`: Non-empty string, unique across all files, safe filename/alphanumeric chars.
  - `model`: Non-empty string.
  - `manufacturer`: Non-empty string.
  - `aircraft_type`: One of the 7 valid classes.
  - `m0`: Number > 0.
  - `me`: Optional number; if provided, must satisfy $0 < m_e < m_0$.
  - `s`: Optional number; if provided, must be > 0.
  - `b`: Optional number; if provided, must be > 0.
  - `engine_type`: Must match propulsion fields (jet requires `t_kn` or null `p_kw`; prop requires `p_kw` or null `t_kn`).
- **Cache Clearing**:
  - Any mutating operation (`POST`, `PUT`, `DELETE`) invokes `load_aircraft.cache_clear()` inside `calculations/trends.py`.

### M3: UI Integration Contracts
- **Module 1 & Wizard**:
  - Suggestions Container: `#trendSuggestionsPanel` in `templates/inputs_panel.html`.
  - Event listener on aircraft type change / MTOW change calls `/api/trends/suggestions`.
  - One-click buttons with class `.apply-trend-btn` write values to `#wing_loading`, `#aspect_ratio`, `#v_stall_kmh`, `#empty_mass_fraction`, `#engine_power_kw`, etc.
  - Invokes `BipolDesignBasis.sync()` and `performCalculation()`.
- **Transfer Panel in "Baza i trendy"**:
  - Container `#trendTransferPanel` in `#trendResultsPanel`.
  - Shows table comparing $y_{trend}$ vs $y_{proj}$ with $\Delta$ badge.
  - Action buttons: individual transfer per parameter and batch transfer `[⚡ Zastosuj rekomendacje]`.
- **Database Editor Modal**:
  - Modal `#aircraftEditorModal` in `templates/trends_panel.html`.
  - Form validation on client before submit; error display container for server-returned errors.
  - On save or delete, invalidates client catalog cache, re-fetches `/api/aircraft`, and invokes `performCalculation()`.
