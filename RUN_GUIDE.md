# ORCA Run Guide

Ye guide Windows par ORCA ko run karne ke liye hai.

## 1. Requirements

Install these first:

- Python 3.13
- Node.js 20 or newer
- Git

Check installation:

```powershell
py -3.13 --version
node --version
npm --version
```

## 1.5. Download Project

```powershell
git clone https://github.com/Princevish-dev/Marine-ORCA.git
cd Marine-ORCA
```

## 2. Backend Setup

PowerShell me:

```powershell
cd "d:\HackaThon SIH\orca\backend"
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

Agar PowerShell execution policy error aaye, ye command ek baar run karein:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## 3. Backend Environment File

Backend folder ke andar `.env` file banayein:

```powershell
cd "d:\HackaThon SIH\orca\backend"
notepad .env
```

Is content ko paste karke save karein:

```env
APP_ENV=development
DEMO_MODE=false
GUARDIAN_ENABLED=true
GUARDIAN_INTERVAL_SECONDS=15
OLLAMA_ENABLED=true
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:1b
IMD_FEED_URL=
FRONTEND_URL=http://localhost:3000
```

`DEMO_MODE=false` = working mode (live Open-Meteo data). Login/auth disabled — open http://localhost:3000 seedha dashboard. Ollama local chalana zaroori hai (`ollama serve` + model pull).

> Offline demo chahiye ho to `DEMO_MODE=true` set karein.

## 4. Backend Run Karein

Backend terminal me:

```powershell
cd "d:\HackaThon SIH\orca\backend"
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 8000
```

Backend check karein:

- http://localhost:8000/
- http://localhost:8000/api/health

Terminal ko open rehne dein.

## 5. Frontend Setup

Naya PowerShell terminal kholkar:

```powershell
cd "d:\HackaThon SIH\orca\frontend"
npm install
npm run dev
```

Frontend open karein:

- http://localhost:3000

## 6. Quick Copy-Paste Version

Backend terminal:

```powershell
cd "d:\HackaThon SIH\orca\backend"
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
$env:DEMO_MODE="false"
$env:APP_ENV="development"
$env:OLLAMA_ENABLED="true"
$env:GUARDIAN_ENABLED="true"
python -m uvicorn app.main:app --reload --port 8000
```

Frontend terminal:

```powershell
cd "d:\HackaThon SIH\orca\frontend"
npm install
npm run dev
```

## 7. Tests Run Karna

Backend tests:

```powershell
cd "d:\HackaThon SIH\orca\backend"
.\.venv\Scripts\Activate.ps1
python -m pytest tests -q
```

Expected result:

```text
21 passed
```

Frontend production build:

```powershell
cd "d:\HackaThon SIH\orca\frontend"
npm run build
```

## 8. Live Mode

Live mode ke liye `backend/.env` me ye values set karein:

```env
APP_ENV=development
DEMO_MODE=false
GUARDIAN_ENABLED=true
OLLAMA_ENABLED=true
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:1b
IMD_FEED_URL=your-official-imd-json-or-rss-feed
FRONTEND_URL=http://localhost:3000
```

Live / working mode me Open-Meteo marine/weather APIs use honge. Login auth nahi hai. Ollama unavailable hone par deterministic fallback answer milega.

## 9. Production Note

Ye build local working prototype ke liye hai — **login/JWT auth disabled**. Production deploy se pehle auth wapas add karna hoga. `.env` ko GitHub par upload na karein.

## 10. Common Problems

### `ModuleNotFoundError`

Virtual environment activate karke dependencies install karein:

```powershell
cd "d:\HackaThon SIH\orca\backend"
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

### Port already in use

Backend ke liye doosra port:

```powershell
python -m uvicorn app.main:app --reload --port 8001
```

Phir frontend me API URL set karein:

```powershell
$env:NEXT_PUBLIC_API_URL="http://localhost:8001"
npm run dev
```

### Frontend backend se connect nahi ho raha

Check karein:

1. Backend terminal me `Uvicorn running` dikh raha hai.
2. http://localhost:8000/api/health open ho raha hai.
3. Frontend aur backend dono running hain.
4. Backend ka port frontend ke API URL se match karta hai.

### Hindi voice kaam nahi kar rahi

Browser microphone permission allow karein. Voice feature browser support par depend karta hai; text chat normally kaam karega.
