# 樣品資料管理系統（MVP 架構）

## 0. 設計原則
- 檔名：短、穩定、可人工辨識
- Metadata：完整、可機器解析（Pydantic）
- 原始資料：一旦上傳至 NAS 即不可修改（immutable）
- Fab 與 Characterization：系統解耦，僅透過 ID 連結
- Index 層：集中查詢入口（避免每次掃描整個 NAS）

---

## 1. 識別碼設計（Identifier Strategy）

### 主要識別碼
Characterization 檔名使用：

`lot_id + wafer_id + chip_id`

範例：
`L123_W02_C015`

設計理由：
- 控制 Windows 檔名長度限制
- 可直接對應 Fab 系統
- 避免將 layout 複雜資訊塞入檔名

---

### 延伸識別碼（僅存在於 Metadata）
- sample_id
- device_id（選用）
- die_position（x, y）
- mask_id
- layout_cell
- device_map_ref

---

## 2. NAS 資料夾結構

/char_data/
  /L123/
    /W02/
      /C015/
        /VNA/
        /T1/
        /PULL/
        /RELIABILITY/

---

## 3. 檔名命名規則

格式：
{date}_{lot}_{wafer}_{chip}_{meas}_{run}_{stage}.{ext}

範例：
260423_L123_W02_C015_VNA_R001_raw.csv  
260423_L123_W02_C015_T1_R003_fit.json  

### Run ID 規則
- R001：第一次量測
- R002：重複量測
- R003：stress 後量測
- 可加後綴：RETRY / CAL / FAIL

---

## 4. Measurement Metadata（JSON）

每次量測必須有一個 JSON（Pydantic 驗證）

必要欄位：
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

## 5. 原始資料管理規則（Raw Data Policy）
- 原始資料上傳後不可修改
- 必須搭配 metadata JSON
- 不允許覆蓋（no overwrite）
- 建議記錄：
  - file_size
  - checksum（md5 / sha256）
  - upload_timestamp

---

## 6. Fab ↔ Characterization 連結

Fab 與 Characterization 為獨立系統  
透過以下識別碼連結：

`lot_id + wafer_id + chip_id`

### 查詢流程
1. 讀取 fab runcard JSON
2. 查詢 char index
3. 取得所有量測紀錄
4. 載入 metadata 與 raw data
5. 組合完整樣品履歷

---

## 7. Index 層（關鍵設計）

避免每次掃 NAS，建立集中索引

### MVP
- 使用 CSV index

### 升級
- SQLite / DuckDB

### Index 欄位
- sample_id
- measurement_run_id
- measurement_type
- timestamp
- tool_id
- file_path
- metadata_path
- result_summary

---

## 8. 查詢方式（Query Interface）

使用方式：
- Python script
- Jupyter Notebook

範例：
query_sample("L123", "W02", "C015")

回傳：
- fab 履歷
- 所有量測紀錄
- summary table
- 檔案路徑

---

## 9. 風險與缺口（Risk & Missing Areas）

### 重複量測語意
需區分：
- retry
- 新實驗
- stress 前 / 後
- calibration

---

### 機台差異
不同機台輸出格式不同：
- CSV / TXT / binary

Metadata 必須記錄：
- tool_id
- format_type
- parser_version

---

### 可重現性（Reproducibility）
必須記錄：
- git_commit
- script_version

---

### 環境與校正
建議記錄：
- calibration ID
- 溫度
- cooldown ID

---

## 10. 未來擴展路線（Roadmap）

Phase 1：CSV + JSON（目前）  
Phase 2：加入 index database  
Phase 3：導入 HDF5（大型資料）  
Phase 4：建立 dashboard / 自動報表  

---

## 總結

此架構具備：
- 可擴展性
- 清晰的 fab ↔ char 連結
- 輕量實作成本
- 未來升級空間

