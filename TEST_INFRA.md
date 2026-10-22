# BIPOL Studio Test Infrastructure & E2E Testing Framework

**Document**: `TEST_INFRA.md`  
**Target Project**: BIPOL Studio Trend Analysis Integration & Reference Aircraft Database Editor  
**Target Environment**: Python 3.11.9, pytest 9.x, Windows / Cross-Platform  
**Status**: ACTIVE  

---

## 1. Testing Methodology

This test infrastructure is designed using **opaque-box (black-box) specification-driven verification** principles. Tests evaluate backend APIs, persistent storage mechanisms, aerodynamic parameter derivations, and client-server interface contracts strictly against documented specifications (`PROJECT.md` § Interface Contracts and `ORIGINAL_REQUEST.md`) without coupling to private internal implementation details.

### 1.1 Multi-Tier Test Pyramid

The E2E test suite is organized into four systematic verification tiers:

```
                  ▲
                 / \
                /   \     Tier 4: Real-World Application Scenarios (>=5 Workflows)
               / Tier\    [Student GA Trainer, Regional Turboprop, Fleet Admin, etc.]
              /   4   \
             /─────────\
            /  Tier 3   \  Tier 3: Cross-Feature Combinations & Pairwise Interactions
           /─────────────\ [CRUD Mutation -> Cache Invalidation -> Dynamic Suggestions Recomputation]
          /    Tier 2     \ Tier 2: Boundary, Negative & Numerical Stability Cases
         /─────────────────\ [Empty inputs, non-positive mass, division by zero, small cohorts]
        /      Tier 1       \ Tier 1: Core Feature Coverage (>=5 test cases per feature R1–R4)
       /─────────────────────\ [Complete API parameter sets, JSON contracts, response formats]
```

1. **Tier 1 — Core Feature Coverage**:
   - Comprehensive validation of requirements R1 through R4.
   - At least 5 distinct test cases per feature covering all 7 aircraft classes (`piston_ga`, `turboprop_regional`, `jet_business`, `jet_transport`, `glider`, `motoglider`, `uav`), required estimation parameters ($W/S$, $AR$, $m_e/m_0$, $P/W$, $T/W$, $V_H$, control surface ratios, dihedral), and full CRUD lifecycle endpoints.
2. **Tier 2 — Boundary, Negative & Numerical Stress Cases**:
   - Verification of defensive input validation and edge-case resilience.
   - At least 5 boundary test cases per feature: empty inputs, zero/negative masses, inverted mass invariants ($m_e \ge m_0$), missing required identifiers, non-positive wing area ($S \le 0$), propulsion type mismatch, extreme aspect ratios, and numerical singularity prevention for small cohorts ($N < 3$).
3. **Tier 3 — Cross-Feature Pairwise Interactions**:
   - Verification of reactive interactions between subsystems.
   - Adding a new custom aircraft model via `POST /api/aircraft`, checking disk persistence, clearing in-memory cache, and verifying that `GET /api/trends/suggestions` dynamically incorporates the new data point ($N$ incremented, regression updated).
   - Modifying aircraft parameters via `PUT /api/aircraft/<id>` and verifying live recomputation without server restart.
   - Deleting aircraft via `DELETE /api/aircraft/<id>` and verifying clean regression revert.
4. **Tier 4 — Real-World Application Scenarios**:
   - Complete end-to-end user workflows emulating student and professional engineering sessions:
     - *Scenario 1*: Undergraduate student designing a GA trainer ($m_0 = 1150$ kg) adopting trend suggestions and evaluating full P1 preliminary sizing.
     - *Scenario 2*: Regional turboprop preliminary design session ($m_0 = 22\,000$ kg) comparing power loading and wing loading trends against reference cohorts.
     - *Scenario 3*: Aircraft fleet database manager updating reference data with a newly certified light electric/hybrid plane, modifying specs, and decommissioning.
     - *Scenario 4*: Business jet high-speed cruise design session optimizing wing loading and thrust-to-weight loading against transport categories.
     - *Scenario 5*: Specialized CS-22 motoglider / glider low-speed soaring sizing session testing high aspect ratio wings ($\Lambda > 15$) and small cohort statistics.

---

## 2. Test Execution Commands & Runner Guide

All tests run through standard `pytest` under **Python 3.11**. The project includes a root `pytest.ini` with `pythonpath = .`.

### 2.1 Complete Test Suite Execution

Run the complete test suite including baseline unit tests and E2E suites:

```powershell
pytest -o pythonpath=. tests/
```

### 2.2 Running E2E Test Suites by Track

Run specific E2E test files independently:

```powershell
# 1. Statistical Parameter Suggestions Engine API (R1 & R4)
pytest -o pythonpath=. tests/test_e2e_trends_api.py -v

# 2. Reference Aircraft Database CRUD & Atomic Persistence (R3 & R4)
pytest -o pythonpath=. tests/test_e2e_aircraft_db.py -v

# 3. UI Contracts, Pairwise Interactions & Real-World Scenarios (R2, Tier 3 & Tier 4)
pytest -o pythonpath=. tests/test_e2e_workflows.py -v
```

### 2.3 Running Specific Test Tiers by Filter

Tests are structured with descriptive naming conventions and pytest markers:

```powershell
# Run Tier 1 Feature Coverage tests
pytest -o pythonpath=. -k "tier1"

# Run Tier 2 Boundary & Corner tests
pytest -o pythonpath=. -k "tier2"

# Run Tier 3 Cross-Feature Combination tests
pytest -o pythonpath=. -k "tier3"

# Run Tier 4 Real-World Scenario tests
pytest -o pythonpath=. -k "tier4"
```

---

## 3. Database Isolation & Concurrency Safety

Testing mutations on disk-backed datasets (`data/aircraft/*.json`) requires strict isolation to avoid data corruption or repo contamination.

### 3.1 Fixture-Level Snapshot and Restore

All mutating test suites utilize an automatic snapshot-and-restore fixture:
- Before test execution, the exact state of all 4 JSON files (`cado.json`, `fast.json`, `geometry_trends.json`, `motogliders.json`) is captured in memory.
- During test execution, create/update/delete operations act on disk.
- In the `finally` / teardown block, all original files are restored with byte-level fidelity, any auxiliary test files are pruned, and `load_aircraft.cache_clear()` is executed.
- This ensures test independence: test ordering does not affect outcomes, and tests leave the repository completely pristine (`git status` remains clean).

---

## 4. Coverage Thresholds & Quality Gates

| Metric | Target / Requirement | Verification Method |
| :--- | :--- | :--- |
| **Python Version** | Python 3.11.x (tested on 3.11.9) | Pytest environment check |
| **Pass Rate** | 100% pass across all tests | Automated test runner |
| **Tier 1 Coverage** | $\ge 5$ test cases per feature (R1–R4) | Test inventory audit |
| **Tier 2 Coverage** | $\ge 5$ boundary cases per feature (R1–R4) | Boundary test audit |
| **Tier 3 Coverage** | $\ge 6$ pairwise interaction sequences | Interaction audit |
| **Tier 4 Coverage** | $\ge 5$ complete real-world scenarios | Scenario index audit |
| **Database Safety** | Zero persistent mutations to reference JSONs | Pre/post SHA-256 hash checks |
| **Response Latency** | $< 500$ ms per API transaction | Performance assertion in E2E tests |

---

## 5. Test Scenario Index

### 5.1 Suggestions API Suite (`tests/test_e2e_trends_api.py`)

- `test_tier1_r1_suggestions_all_7_aircraft_classes`: Verifies `GET /api/trends/suggestions` returns valid payloads across all 7 classes.
- `test_tier1_r1_suggestions_dynamic_evaluation_with_m0`: Tests dynamic regression evaluation when MTOW $m_0$ is supplied.
- `test_tier1_r1_suggestions_fallback_when_m0_omitted`: Tests default cohort averages/medians when $m_0$ is not provided.
- `test_tier1_r1_suggestions_required_keys_structure`: Asserts all 10 required parameter estimations ($W/S$, $AR$, $m_e/m_0$, $P/W$ or $T/W$, $V_H$, control surfaces, dihedral) contain stats, $R^2$, $N$, and equation.
- `test_tier1_r1_suggestions_wing_configuration_options`: Verifies behavior with `wing_configuration=cantilever` and `strut_braced`.
- `test_tier1_r4_suggestions_json_validity_and_no_nan`: Ensures no `NaN`, `Infinity`, or invalid float values in JSON response.
- `test_tier2_r1_boundary_unknown_aircraft_class_returns_400`: Verifies invalid aircraft class returns HTTP 400.
- `test_tier2_r1_boundary_negative_and_zero_m0_handling`: Verifies negative and zero MTOW are rejected or handled defensively.
- `test_tier2_r1_boundary_extreme_m0_no_overflow`: Evaluates huge MTOW ($10^8$ kg) to verify no math overflow (`exp`/power laws).
- `test_tier2_r1_boundary_small_cohort_glider_uav`: Validates graceful statistical degradation for low sample sizes ($N < 15$).
- `test_tier2_r1_boundary_propulsion_loading_mutual_exclusion`: Asserts glider has null $P/W$ and $T/W$, jet has $T/W$ only, prop has $P/W$ only.

### 5.2 Aircraft Database CRUD Suite (`tests/test_e2e_aircraft_db.py`)

- `test_tier1_r3_catalog_retrieval_and_filtering`: Verifies `GET /api/aircraft` returns reference catalog with metadata.
- `test_tier1_r3_get_aircraft_by_id_success`: Retrieves existing record by unique ID with raw and derived attributes.
- `test_tier1_r3_create_new_aircraft_success`: Posts a valid new aircraft, checks 201 Created response.
- `test_tier1_r3_update_existing_aircraft_success`: Updates physical parameters via `PUT /api/aircraft/<id>`, checks 200 OK.
- `test_tier1_r3_delete_aircraft_success`: Deletes aircraft via `DELETE /api/aircraft/<id>`, checks 200 OK.
- `test_tier1_r3_reactive_recalculation_after_mutation`: Confirms `load_aircraft.cache_clear()` updates in-memory dataset immediately.
- `test_tier2_r3_boundary_missing_required_fields`: Checks 400 rejection when `id`, `model`, `manufacturer`, or `m0` is omitted.
- `test_tier2_r3_boundary_negative_mass_rejected`: Checks 400 rejection for $m_0 \le 0$ or $m_e \le 0$.
- `test_tier2_r3_boundary_inverted_empty_mass_fraction`: Checks 400 rejection when $m_e \ge m_0$.
- `test_tier2_r3_boundary_non_positive_wing_area`: Checks 400 rejection when $S \le 0$.
- `test_tier2_r3_boundary_engine_type_propulsion_mismatch`: Rejects jet with shaft power or propeller with thrust.
- `test_tier2_r3_boundary_duplicate_id_conflict`: Returns 409 Conflict when attempting to create already existing ID.
- `test_tier2_r3_boundary_update_nonexistent_returns_404`: Returns 404 Not Found on PUT to unknown ID.
- `test_tier2_r3_boundary_delete_nonexistent_returns_404`: Returns 404 Not Found on DELETE to unknown ID.

### 5.3 Workflows, Pairwise Interactions & Scenarios Suite (`tests/test_e2e_workflows.py`)

- `test_tier1_r2_module1_suggestions_ui_contract`: Verifies presence and structure of `#trendSuggestionsPanel` and `.apply-trend-btn`.
- `test_tier1_r2_transfer_panel_ui_contract`: Verifies structure of `#trendTransferPanel` and comparison delta badges.
- `test_tier1_r2_wizard_adoption_contract`: Verifies Project Wizard step template inputs accommodate trend adoptions.
- `test_tier3_interaction_crud_create_then_suggestions_recalculation`: Adds custom aircraft and verifies $N$ increments and regression updates.
- `test_tier3_interaction_crud_update_then_catalog_and_regression_update`: Updates aircraft $m_0$ and $S$, verifies updated regressions.
- `test_tier3_interaction_crud_delete_reverts_suggestions`: Deletes aircraft and verifies regressions revert exactly to baseline.
- `test_tier3_interaction_cross_class_engine_isolation`: Creates multi-engine and glider records, verifies no cross-class pollution.
- `test_tier3_interaction_disk_persistence_after_cache_flush`: Re-reads JSON files from disk directly to confirm disk persistence.
- `test_tier4_scenario1_student_ga_trainer_design_workflow`: Student designing GA trainer ($m_0 = 1150$ kg) adopting trend suggestions into P1 preliminary sizing.
- `test_tier4_scenario2_regional_turboprop_design_session`: Regional turboprop preliminary design session ($m_0 = 22\,000$ kg) comparing power and wing loading.
- `test_tier4_scenario3_fleet_database_manager_lifecycle`: Fleet manager adding new light electric plane, modifying specs, and decommissioning.
- `test_tier4_scenario4_business_jet_high_speed_cruise_session`: Super-midsize business jet ($m_0 = 18\,000$ kg) optimizing wing and thrust loading.
- `test_tier4_scenario5_motoglider_cs22_soaring_sizing_session`: Touring motoglider ($m_0 = 750$ kg) sizing aspect ratio $\Lambda > 16$ and verifying fallback statistics.
