# Sample Data Management System (MVP Architecture)

## 0. Design Principles
- Filenames: short, stable, human-readable
- Metadata: complete, machine-readable (Pydantic)
- Raw data: immutable once uploaded to NAS
- Fab and characterization: decoupled systems
- Index layer: central query interface (avoid scanning NAS)

---

## 1. Identifier Strategy

### Primary Identifier
Characterization filenames use:
`lot_id + wafer_id + chip_id`

Example:
`L123_W02_C015`

Rationale:
- Avoid Windows filename length issues
- Direct mapping to fab system
- Keep filenames simple

### Extended Identifiers (Metadata Only)
- sample_id
- device_id (optional)
- die_position (x, y)
- mask_id
- layout_cell
- device_map_ref

---

## 2. NAS Directory Structure

/char_data/
  /L123/
    /W02/
      /C015/
        /VNA/
        /T1/
        /PULL/
        /RELIABILITY/

---

## 3. File Naming Convention

Format:
{date}_{lot}_{wafer}_{chip}_{meas}_{run}_{stage}.{ext}

Example:
260423_L123_W02_C015_VNA_R001_raw.csv
260423_L123_W02_C015_T1_R003_fit.json

### Run ID Rules
- R001: first measurement
- R002: repeat
- R003: post-stress
- RETRY / CAL / FAIL optional tags

---

## 4. Measurement Metadata (JSON)

Required fields:
- measurement_run_id
- lot_id
- wafer_id
- chip_id
- measurement_type
- run_id
- tool_id
- timestamp
- operator
- raw_data_path
- script_version
- git_commit
- measurement_config
- result_summary

---

## 5. Raw Data Policy
- Raw files are immutable after upload
- Metadata must accompany raw data
- No overwrite allowed
- Store checksum and file size

---

## 6. Fab ↔ Char Linking

Link via:
`lot_id + wafer_id + chip_id`

Workflow:
1. Load fab runcard JSON
2. Query characterization index
3. Retrieve metadata + raw files
4. Merge into sample history

---

## 7. Index Layer

MVP:
- CSV index file

Upgrade:
- SQLite / DuckDB

Fields:
- sample_id
- measurement_run_id
- measurement_type
- timestamp
- tool_id
- file_path
- metadata_path
- result_summary

---

## 8. Query Interface

Access via:
- Python scripts
- Jupyter notebooks

Example:
query_sample("L123", "W02", "C015")

Returns:
- fab history
- measurement list
- summaries
- file paths

---

## 9. Risk & Missing Areas

### Re-measurement ambiguity
- distinguish retry vs new run

### Tool variability
- track format_type and parser_version

### Reproducibility
- record git_commit and script_version

### Environment tracking
- calibration ID
- temperature
- cooldown ID

---

## 10. Roadmap

Phase 1: CSV + JSON
Phase 2: Add index DB
Phase 3: Introduce HDF5
Phase 4: Dashboard / automation

---

## Summary

This architecture provides:
- Scalable data organization
- Clear fab ↔ characterization linkage
- Lightweight implementation
- Future upgrade path

