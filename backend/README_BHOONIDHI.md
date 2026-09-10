# ORCA Bhoonidhi OCM-3 Downloader

Ye script ISRO Bhoonidhi portal se EOS-06 (Oceansat-3) ka OCM-3 Level-2C (L2C) geophysical NetCDF data download karne ke liye banayi gayi hai. Ye ORCA ke Local-First architecture ka hissa hai, jisse aap bina live API ke 8-20 din ka satellite data seedhe apne system par download aur process kar sakte hain.

## 🛠️ Setup Instructions

1. **Python Environment Setup Karein:**
   Make sure aapke paas Python 3.10+ installed hai. Phir dependencies install karein:
   ```bash
   pip install -r requirements.txt
   ```

2. **Credentials Configure Karein:**
   `.env.example` ko copy karke `.env` banayein aur apni Bhoonidhi details daalein:
   ```bash
   cp .env.example .env
   # Ab .env file me apna username aur password enter karein
   ```
   *Agar account nahi hai toh [Bhoonidhi Portal](https://bhoonidhi.nrsc.gov.in/) par register karein.*

3. **Data Download Run Karein:**
   Default settings ke sath (pichle 20 din ka data, Arabian Sea + Bay of Bengal AOI):
   ```bash
   python download_ocm3.py
   ```

## 🚀 Usage Options (CLI Flags)

Aap in flags ka use karke download ko customize kar sakte hain:

- `--days` : Kitne din purana data chahiye? (Default: 20)
- `--aoi` : Area of Interest chunein. Options: `default`, `arabian_sea`, `bay_of_bengal`, `custom`
- `--bbox` : Agar `--aoi custom` hai, toh bounding box pass karein: `MIN_LAT MAX_LAT MIN_LON MAX_LON`
- `--output` : Download folder ka path (Default: `./data/bhoonidhi`)
- `--dry-run` : Sirf check karega ki kaunsi files aayengi, download nahi karega.
- `--no-resume` : Pehle se download hui files ko bhi dobara download karega.

**Examples:**

1. Arabian Sea ka pichle 5 din ka data download karein:
   ```bash
   python download_ocm3.py --days 5 --aoi arabian_sea
   ```

2. Custom Bounding Box (Mumbai Coast):
   ```bash
   python download_ocm3.py --days 10 --aoi custom --bbox 18.5 19.5 72.5 73.5
   ```

3. Sirf test karein ki kitni files milengi (bina download kiye):
   ```bash
   python download_ocm3.py --dry-run
   ```

## 📂 Output Structure

Download hone ke baad files is structure me save hongi:
```
data/bhoonidhi/
├── ocm3/
│   └── 2026/
│       └── 08/
│           ├── 22/
│           │   └── OCM3_L2C_XYZ.nc
│           └── 23/
│               └── OCM3_L2C_ABC.nc
├── download_manifest.json  <-- Download status aur file hashes
├── download.log            <-- Pura log (success/failures)
└── failed_downloads.json   <-- (Optional) Jo files fail ho gayi unki list
```

## 🤖 ORCA Integration Note
Jab ye `.nc` files download ho jayengi, toh aapka `marine_agent.py` inhi files se `chlorophyll`, `sst`, `wave_height`, aur `wind_speed` read karke ORCA dashboard par show karega aur anomaly scores calculate karega. Ye completely offline kaam karega!
