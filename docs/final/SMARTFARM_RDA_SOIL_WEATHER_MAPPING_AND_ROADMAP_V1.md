# RDA public soil and agri-meteo data: column mapping and 4-week roadmap

**Purpose:** Turn the received ZIP (`토양 환경 데이터  기상 및 환경 데이터제공.zip`) into actionable integration for the existing AI smartfarm contract and pilot KPIs, without claiming capabilities the public dataset does not support.

**Machine-readable map:** [SMARTFARM_RDA_COLUMN_MAP_V1.json](SMARTFARM_RDA_COLUMN_MAP_V1.json)

**Related SSOT in repo**

- Control safety: [AI_SMARTFARM_CONTROL_SAFETY_POLICY.yaml](AI_SMARTFARM_CONTROL_SAFETY_POLICY.yaml)
- API contract schema: [schemas/ai_smartfarm_api_contract_v1.schema.json](schemas/ai_smartfarm_api_contract_v1.schema.json)
- Examples: [AI_SMARTFARM_API_CONTRACT_EXAMPLES_V1.json](AI_SMARTFARM_API_CONTRACT_EXAMPLES_V1.json)
- Pilot KPI template: [AI_SMARTFARM_PILOT_KPI_TEMPLATE.csv](AI_SMARTFARM_PILOT_KPI_TEMPLATE.csv)
- Responsibility boundary: [AI_SMARTFARM_OPERATION_RESPONSIBILITY_1P.md](AI_SMARTFARM_OPERATION_RESPONSIBILITY_1P.md)
- Stub runtime (pilot): [scripts/ai_smartfarm_api_stub.py](../../scripts/ai_smartfarm_api_stub.py)

---

## 1) What we actually received (verified unpack)

**Local extract path (gitignored, large):** `data/smartfarm_rda_extract_v1/데이터제공/`

| Path | Contents | Notes |
|------|-----------|--------|
| `기상/농업기상 시간자료(2023년~2026년).xlsx` | Multiple half-year sheets (2023 H1 through 2026 up to Apr 26) | Columns: `지점명`, `일시`, `온도`, `습도`, `일사량`, `강수량`. `일시` sample: `20230101  00` (hourly). First sheet row count on the order of 9e5 rows; **212** distinct `지점명` on that sheet. |
| `토양/토양검정화학성상세정보(2023).xlsx` etc. | One sheet per year `Sheet1` | Korean columns as below. 2023 file on the order of 6e5 rows. |
| `토양/토양검정화학성상세정보(2025).xlsx` | Same semantics, broken header row | Row 0 repeats Korean headers under English column names; **ETL: `skiprows=1`** then columns are standard Korean. |
| `토양/토양검정화학성상세정보(2024).xlsx` | Same as 2023 | Column `산도 ` includes a **trailing space**; normalize to `산도` on ingest. |

**Not in this package (per supplier mail):** soil moisture time series, growth indices, input (fertilizer/pesticide) logs, pest/disease raster or vector originals. Plan accordingly: **weather + soil chemistry support irrigation timing and agronomic context; they do not replace field sensors for auto irrigation under the current contract.**

---

## 2) Column mapping (source to canonical to product use)

### 2.1 Weather (hourly, all sheets concatenated)

| Source (KO) | Canonical | Use in smartfarm stack |
|-------------|-----------|-------------------------|
| `지점명` | `agmet_station_name` | Join key: map station to `farm_id` / `zone_id` via a small operator-maintained table (pilot: one station per zone). |
| `일시` | `agmet_ts_seoul` | Parse `YYYYMMDD  HH` to hourly timestamp in `Asia/Seoul`. |
| `온도` | `air_temp_c` | `external_context` for ET proxy, heat stress alerts (advisory). |
| `습도` | `rh_pct` | `external_context`. |
| `일사량` | `solar_radiation` | `external_context`; **confirm official unit** from RDA/OpenAPI field spec before any physics-based model. |
| `강수량` | `precip_mm_h` | Roll **12-hour sum** ending at decision time to feed `decision_log_event.payload.input_snapshot.forecast_rain_mm_12h` during **historical replay**. Live operation should still use an operational forecast feed; this archive validates rain-gate behaviour and KPI-06. |

### 2.2 Soil test (parcel-level, sparse in time)

| Source (KO) | Canonical | Use in smartfarm stack |
|-------------|-----------|-------------------------|
| `시료채취년도` | `sample_year` | Context and versioning. |
| `토양검정일` | `exam_date` | Often readable as `int` YYYYMMDD after 2025 fix; normalize to date. |
| `경지구분코드` | `land_use_code` | Filter (e.g. paddy vs upland) for analytics. |
| `대상지 지번주소` | `parcel_address` | Human audit. |
| `지번코드` | `pnu_code` | **Primary join** to farm registry when the pilot parcel PNU is known. |
| `유기물` … `칼슘` | `om`, `p`, `k`, `mg`, `k`, `ca` (canonical names in JSON map) | Fertilizer advisory and long-term soil health reporting; **not** wired to `control_command` without agronomy rules + human gate. |
| `산도` / `산도 ` | `soil_ph` | Same as above. |
| `전기전도도` | `soil_ec_raw` | Potential input to salinity risk; **do not** map straight into `telemetry_ingest.soil_ec_us_cm` until **documented unit conversion** and preferably calibration against field EC sensor (contract field is microsiemens per cm in examples). |

---

## 3) Contract gap (explicit)

`schemas/ai_smartfarm_api_contract_v1.schema.json` requires for `telemetry_ingest`: `soil_moisture_pct`, `soil_temp_c`, `soil_ec_us_cm`, `comm_ok`. **None of these are provided as time series in the RDA public pack.**  

`AI_SMARTFARM_CONTROL_SAFETY_POLICY.yaml` `rain_gate.require_soil_condition_gate: true` expects soil **condition** from live telemetry, not an annual soil test row.

**Implication:** Use RDA data in **`external_context`** (and optional **replay-only** synthetic or upper-bound moisture if you add a separate research lane), keep live auto irrigation gated on real sensors until policy is explicitly revised with evidence.

---

## 4) Four-week execution roadmap

### Week 1: Ingestion and normalization

- Unpack ZIP to `data/smartfarm_rda_extract_v1/` (already done on your machine; path gitignored).
- Implement or script: concatenate all weather sheets; normalize `일시` parser; normalize `산도 `; read 2025 with `skiprows=1`.
- Build **station to zone** mapping table (CSV/JSON) for the pilot farm’s nearest agmet station(s).
- Deliverable: Parquet or SQLite **canonical tables** `agmet_hourly`, `soil_test_parcel` with stable dtypes.

### Week 2: Join logic and historical replay inputs

- Join `pnu_code` (soil) to pilot `farm_id`/`zone_id` registry (manual row for pilot).
- Compute `rain_mm_12h_rolling` per station for replay alignment with `AutoEvaluateRequest.forecast_rain_mm_12h` in [scripts/ai_smartfarm_api_stub.py](../../scripts/ai_smartfarm_api_stub.py).
- Run **offline** replay: for each historical hour, attach latest preceding soil test row as `external_context` (forward-filled by parcel until next test).
- Deliverable: JSONL of `decision_log_event`-shaped rows with `input_snapshot` filled from replay policy (document divergence from live forecast).

### Week 3: KPI harness and policy tuning

- Populate baseline columns in [AI_SMARTFARM_PILOT_KPI_TEMPLATE.csv](AI_SMARTFARM_PILOT_KPI_TEMPLATE.csv) for **KPI-06** (rain-loss avoidance), **KPI-09** (data completeness for merged feed), **KPI-10** (decision trace coverage).
- Sensitivity analysis: `rain_mm_threshold` (default 3.0 in stub) vs skip rate using historical precip only; document trade-offs.
- Deliverable: short internal report (can live under `reports/` if you add one file) with charts optional; **no live control change** without sign-off per operation responsibility doc.

### Week 4: Hardening and optional UI

- Add validation gates: missing station mapping, impossible timestamps, NaN spikes in precip.
- If productizing: read-only dashboard panel “Agmet + last soil test” fed from canonical tables; control plane unchanged.
- Deliverable: checklist aligned with [AI_SMARTFARM_OPERATION_RESPONSIBILITY_1P.md](AI_SMARTFARM_OPERATION_RESPONSIBILITY_1P.md) section 8 (audit fields) for any new automated suggestion path.

---

## 5) Risk register (keep visible)

| Risk | Mitigation |
|------|------------|
| EC unit ambiguity | Block `soil_ec_us_cm` mapping until RDA field documentation or side-by-side sensor calibration. |
| Soil test is not soil moisture | Do not satisfy `rain_gate.require_soil_condition_gate` with soil test alone; keep sensor path. |
| 2025 duplicate header | Enforce `skiprows=1` + schema validation on first load. |
| Weather vs forecast | Replay uses observed precip sums; live `forecast_rain_mm_12h` remains a different evidence chain—label clearly in logs. |

---

## 6) Optional next code step (not done in this pass)

- Add `scripts/etl_smartfarm_rda_xlsx_to_parquet_v1.py` (or similar) that encodes the rules in `SMARTFARM_RDA_COLUMN_MAP_V1.json` and writes gitignored Parquet under `data/smartfarm_rda_extract_v1/out/`.
- Extend stub or a small library module to accept `external_context` on `/v1/auto/evaluate` for replay-only experiments **without** weakening telemetry requirements for live `execute`.

---

**CENTRAL alignment:** Treat this stream as **evidence-backed pilot analytics** first; **B-track / replay** before any A-track control policy change; Fact-Lock: contract paths above are the product boundary until explicitly extended.
