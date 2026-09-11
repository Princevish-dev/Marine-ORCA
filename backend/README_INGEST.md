# ORCA — OCM-3 Data Ingest Guide

Ye guide **Hinglish** mein hai. ISRO Bhoonidhi se manually data download karke ORCA backend ko feed karne ka complete tarika yahan diya gaya hai.

---

## Step 1: Bhoonidhi se Data Download Karo

1. Browser mein jao: [https://bhoonidhi.nrsc.gov.in](https://bhoonidhi.nrsc.gov.in)
2. Register/Login karo apne credentials se
3. **Search** section mein jao aur ye select karo:
   - **Satellite:** EOS-06 (Oceansat-3)
   - **Sensor:** OCM-3
   - **Product:** GEOPHYSICAL / L2C
   - **AOI:** Indian Ocean region (lat 5-25°N, lon 65-95°E)
   - **Date Range:** Jo dates chahiye wo select karo
4. Results mein se apni marzi ke scenes choose karo
5. **Cart** mein add karo, phir **Order** place karo
6. Download link email par aayega — `.nc` files download kar lo

---

## Step 2: Files Drop Karo `incoming/` Folder Mein

Bhoonidhi se download ki gayi `.nc` files ko is folder mein rakh do:

```
P:\SIH2026\ORCA\backend\incoming\
```

**Note:** Files ka naam kuch bhi ho sakta hai. Nested folders mein bhi rakh sakte ho. Script khud sab scan kar legi — filename pe depend nahi karti.

Example:
```
incoming/
  E06_OCM3_20260908.nc
  day2/
    E06_OCM3_20260909.nc
    E06_OCM3_20260909_tile2.nc
```

---

## Step 3: Ingest Script Chalao

```bash
cd P:\SIH2026\ORCA\backend

# Pehle dry-run karo — files move nahi hongi, sirf report milegi
python ingest_ocm3.py --dry-run

# Sab sahi laga to actual ingest karo
python ingest_ocm3.py
```

Script khud ye kaam karegi:
- Har `.nc` file ko open karke validate karegi
- Metadata extract karegi (date, satellite, sensor, variables)
- File ko canonical path par move karegi: `data/bhoonidhi/ocm3/YYYY/MM/DD/`
- `manifest.json` update karegi
- Corrupt files ko `quarantine/` mein move karegi

---

## CLI Options

```bash
python ingest_ocm3.py --help
```

| Flag | Default | Description |
|------|---------|-------------|
| `--incoming` | `./incoming` | Jahan aap files drop karte ho |
| `--output` | `./data/bhoonidhi` | Organized output folder |
| `--quarantine` | `./quarantine` | Corrupt files yahan jayengi |
| `--dry-run` | False | Sirf check karo, move mat karo |
| `--keep-source` | False | Move ki jagah copy karo |
| `--rebuild-manifest` | False | Manifest fresh banao |

---

## Output Structure

Ingest ke baad ye structure ban jaati hai:

```
data/bhoonidhi/
  ocm3/
    2026/
      09/
        08/
          E06_OCM3_20260908.nc
        09/
          E06_OCM3_20260909.nc
  manifest.json       <-- ORCA backend ye padhta hai
  ingest.log          <-- Pura log
  failed_ingest.json  <-- (Optional) Jo files fail hui

quarantine/
  broken.nc
  broken.nc.error.txt  <-- Kyu fail hui
```

---

## ORCA Backend Ke Saath Integration

Ingest hone ke baad ORCA ke agents automatically ye data use karte hain:

- `marine_agent.py` → `manifest_loader.get_latest_manifest()` call karta hai
- Har `.nc` file se `chlorophyll`, `sst`, `wave_height`, `wind_speed` extract hoti hai
- Anomaly score `R(t)` compute hota hai
- Ollama ke through Hinglish/English mein report generate hoti hai

**Aapko kuch aur nahi karna!** Bas files `incoming/` mein daalo aur script chalao.

---

## Tests Chalana

```bash
pip install -r requirements.txt
pytest test_ingest.py -v
```
