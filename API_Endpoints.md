# HKO Open Data API — Flood Swarm Reference

> Base URLs and endpoints used by the swarm agents. All requests are `GET`, all responses are `JSON` unless noted.

---

## 1. Weather Information API

**Base URL:** `https://data.weather.gov.hk/weatherAPI/opendata/weather.php`

**`lang` parameter (all endpoints):** `en` | `tc` | `sc` — default `en`

---

### 1.1 Local Weather Forecast — `flw`

**Example:** `?dataType=flw&lang=en`

**Used by:** `ForecastAgent`

| Field | Description |
|---|---|
| `generalSituation` | Synoptic situation narrative — check for trough / monsoon trough / typhoon mentions |
| `tclnfo` | Tropical cyclone information |
| `forecastDesc` | Forecast description — check for squall / thunderstorm / persistent rain language |
| `outlook` | Extended outlook |
| `updateTime` | `YYYY-MM-DDTHH:mm:ssZ` |

---

### 1.2 9-day Weather Forecast — `fnd`

**Example:** `?dataType=fnd&lang=en`

**Used by:** `ForecastAgent`

| Field | Description |
|---|---|
| `weatherForecast` | List of daily forecast objects |
| `forecastDate` | `YYYYMMDD` |
| `forecastWind` | Wind description |
| `forecastMaxrh` / `forecastMinrh` | Relative humidity range |
| `PSR` | Probability of Significant Rain: `High` \| `Medium High` \| `Medium` \| `Medium Low` \| `Low` |

> **Note:** `soilTemp` and `seaTemp` fields are also returned but not used by swarm agents.

---

### 1.3 Current Weather Report — `rhrread`

**Example:** `?dataType=rhrread&lang=en`

**Used by:** `ForecastAgent` (antecedent rainfall), `WarningAgent` (warning messages)

| Field | Description |
|---|---|
| `rainfall.data[].place` | Station name |
| `rainfall.data[].max` | Maximum rainfall record |
| `rainfall.data[].min` | Minimum rainfall record |
| `rainfall.data[].main` | Maintenance flag (`TRUE`/`FALSE`) |
| `rainfall.startTime` / `endTime` | Measurement window |
| `rainfallFrom00To12` | Accumulated rainfall at HKO from midnight to noon |
| `rainfallLastMonth` | Rainfall last month — used for antecedent saturation assessment |
| `warningMessage` | List of active warning messages (plain text) |
| `rainstormReminder` | Rainstorm reminder text |
| `tcmessage` | Tropical cyclone position message |
| `temperature.data[].place` / `.value` / `.unit` | Per-station temperature |
| `humidity.data[].value` | Relative humidity |
| `updateTime` | `YYYY-MM-DDTHH:mm:ssZ` |

> **Note:** `uvindex`, `icon`, `mintempFrom00To09`, `lightning` fields are returned but not used by swarm agents.

---

### 1.4 Weather Warning Summary — `warnsum`

**Example:** `?dataType=warnsum&lang=en`

**Used by:** `WarningAgent`

Response is a keyed object. Each key is a warning type. Flood-relevant codes:

| Key | Warning | Flood-relevant codes |
|---|---|---|
| `WRAIN` | Rainstorm Warning | `WRAINA` (Amber), `WRAINR` (Red), `WRAINB` (Black) |
| `WFNTSA` | Northern NT Flooding Announcement | `WFNTSA` |
| `WL` | Landslip Warning | `WL` |
| `WTCSGNL` | Tropical Cyclone Warning | `TC1`, `TC3`, `TC8NE/SE/NW/SW`, `TC9`, `TC10`, `CANCEL` |
| `WTS` | Thunderstorm Warning | `WTS` |
| `WMSGNL` | Strong Monsoon Signal | `WMSGNL` |

Each active warning object contains:

| Field | Description |
|---|---|
| `name` | Warning name string |
| `code` | Specific code (e.g. `WRAINB`) |
| `actionCode` | `ISSUE` \| `REISSUE` \| `CANCEL` \| `EXTEND` \| `UPDATE` |
| `issueTime` | `YYYY-MM-DDTHH:mm:ssZ` |
| `expireTime` | `YYYY-MM-DDTHH:mm:ssZ` (may be absent) |
| `updateTime` | `YYYY-MM-DDTHH:mm:ssZ` |

> **Non-flood warnings** (`WFIRE`, `WFROST`, `WHOT`, `WCOLD`, `WTMW`) are returned but not used by swarm agents.

---

### 1.5 Weather Warning Information — `warningInfo`

**Example:** `?dataType=warningInfo&lang=en`

**Used by:** `WarningAgent` — parse `contents` text for embedded quantitative data

| Field | Description |
|---|---|
| `details[].warningStatementCode` | Warning type (same codes as `warnsum`) |
| `details[].subtype` | Sub-type: e.g. `WRAINB`, `TC8NE` |
| `details[].contents` | List of strings — full warning text. Mine for mm/hr figures, district names, flood references |
| `details[].updateTime` | `YYYY-MM-DDTHH:mm:ssZ` |

> **Key pattern:** `WFNTSA` contents frequently contain sentences like *"More than 70 millimetres of rainfall have been recorded in the past 1 hour in [district]"* — extract these figures and district names.

---

## 2. Open Data API — Tides & Lightning

**Base URL:** `https://data.weather.gov.hk/weatherAPI/opendata/opendata.php`

---

### 2.1 Hourly Tide Heights — `HHOT`

**Example:** `?dataType=HHOT&rformat=json&station=QUB&year=2025&month=5`

**Used by:** `TideAgent`

**Swarm stations (3 required):**

| Station | Code | Flood zone covered |
|---|---|---|
| Quarry Bay | `QUB` | Victoria Harbour / urban core |
| Tsim Bei Tsui | `TBT` | Deep Bay / Yuen Long plains |
| Cheung Chau | `CCH` | South channel / storm surge indicator |

**Other available stations:** `CLK`, `CMW`, `KCT`, `KLW`, `LOP`, `MWC`, `SPW`, `TAO`, `TMW`, `TPK`, `WAG`

**Parameters:**

| Parameter | Values | Notes |
|---|---|---|
| `station` | See above | Required |
| `year` | `2022`–current | Required |
| `month` | `1`–`12` | Optional |
| `day` | `1`–`31` | Optional |
| `hour` | `1`–`24` | Optional |

**JSON response shape:**
```json
{ "fields": ["..."], "data": [["...", "..."], ...] }
```

---

### 2.2 High and Low Tide Times — `HLT`

**Example:** `?dataType=HLT&rformat=json&station=QUB&year=2025&month=5`

**Used by:** `TideAgent` — to compute time-to-next-peak

Same station codes and parameter structure as `HHOT`.

---

### 2.3 Lightning Count — `LHL`

**Example:** `?dataType=LHL&rformat=json&lang=en`

**Used by:** `LightningAgent`

Returns cloud-to-ground and cloud-to-cloud lightning counts by district/area.

**JSON response shape:**
```json
{ "fields": ["..."], "data": [["...", "..."], ...] }
```

> Count interpretation for swarm: 0–5 = background noise; 6–20 = isolated cell; 21–50 = active cell; 51–100 = intense cell; >100 = extreme/supercell signature.

---

## 3. Hourly Rainfall API

**Base URL:** `https://data.weather.gov.hk/weatherAPI/opendata/hourlyRainfall.php`

**Example:** `?lang=en`

**Used by:** `RainfallAgent`

> Data is provisional — stations returning `"M"` are under maintenance. Reduce agent confidence when >3 stations return `"M"`.

**Response:**

| Field | Description |
|---|---|
| `obsTime` | Observation time: `YYYY-MM-DDTHH:mm:ssZ` |
| `hourlyRainfall[].automaticWeatherStation` | Station name |
| `hourlyRainfall[].automaticWeatherStationID` | Station ID (e.g. `RF001`) |
| `hourlyRainfall[].value` | mm in past hour — integer string, or `"M"` if maintenance |
| `hourlyRainfall[].unit` | `"mm"` |

**All 35 stations (ID → name):**

| ID | Station | ID | Station |
|---|---|---|---|
| RF001 | Lau Fau Shan | RF002 | Wetland Park |
| N12 | Shui Pin Wai | RF003 | Shek Kong |
| RF004 | Tai Mei Tuk | RF005 | Tai Po Market |
| RF006 | Pak Tam Chung | RF007 | Kau Sai Chau |
| N15 | Sai Kung | RF008 | Tseung Kwan O |
| RF009 | Clear Water Bay | RF010 | Waglan Island |
| RF011 | Cheung Chau | RF012 | Peng Chau |
| RF013 | Ngong Ping | RF014 | HK International Airport |
| RF015 | Ta Kwu Ling | RF016 | Sheung Shui |
| RF017 | Tai Lung | RF018 | Tsuen Wan Ho Koon |
| RF019 | Tuen Mun | RF020 | Sha Tin |
| RF021 | Cheung Ching | RF022 | Sham Shui Po |
| RF023 | Hong Kong Observatory | RF024 | King's Park |
| K02 | Broadcast Drive | RF025 | Kai Tak |
| K09 | San Po Kong | K03 | Kwun Tong |
| RF026 | Shau Kei Wan | RF027 | Happy Valley |
| RF028 | The Peak | H17 | Magazine Gap |
| H15 | Stanley | H24 | Wong Chuk Hang |

---

## 4. Endpoints Not Used by the Swarm

The following HKO APIs are available but excluded from swarm agents:

| API | Reason excluded |
|---|---|
| Earthquake API (`earthquake.php`) | Not relevant to flood prediction |
| Gregorian-Lunar Calendar API (`lunardate.php`) | No flood relevance |
| Sunrise / sunset (`SRS`) | No flood relevance |
| Moonrise / moonset (`MRS`) | No flood relevance |
| Visibility (`LTMV`) | No flood relevance |
| Daily temperature (`CLMTEMP`, `CLMMAXT`, `CLMMINT`) | Historical climate only; not real-time |
| Weather & Radiation Report (`RYES`) | Next-day availability; not real-time |
| Special Weather Tips (`swt`) | Redundant with `warningInfo` content |
