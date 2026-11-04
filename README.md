# H₂SENSE — H₂S Exposure Detection & Cumulative Exposure Monitoring System

> **"Know Your Exposure. Protect Your Workforce."**  
> An intelligent colorimetric exposure-monitoring software prototype that transforms sensor color response into actionable cumulative exposure insights.

---

## ⚠️ Important Technical Honesty & Prototype Context

- **Academic Engineering Prototype**: This application is a college engineering software prototype demonstrating the color-to-exposure estimation and worker exposure-recording workflow.
- **Sensor Representation**: Physical chemical sensors and toxic $H_2S$ gas are not utilized for this demonstration. Instead, a **Digital Sensor Simulator** accurately renders the predefined colorimetric response of the proposed sensor substrate.
- **Honest System Architecture**:
  $$\text{Chemical/Colorimetric Concept} \longrightarrow \text{Digital Color Simulation} \longrightarrow \text{Computer Vision (OpenCV)} \longrightarrow \text{CIELAB Calibration Model} \longrightarrow \text{Environmental Compensation} \longrightarrow \text{Threshold Engine} \longrightarrow \text{Flask Backend} \longrightarrow \text{MySQL/WAMP} \longrightarrow \text{Workforce Dashboard}$$
- **Disclaimer**: Exposure values displayed in this prototype are simulated/calibration-demonstration values and are **not certified occupational $H_2S$ measurements**. Real-world deployment requires controlled chemical laboratory calibration, shelf-life testing, and safety regulatory certification.

---

## 1. Features

- **Virtual Digital Sensor Simulator (`/simulator`)**:
  - Interactive colorimetric substrate rendering across 8 preset exposure increments: `0, 10, 25, 50, 75, 100, 150, 200 ppm`.
  - Continuous slider with real-time RGB and CIE $L^*a^*b^*$ coordinate telemetry.
  - Direct 1-click **"Send to Scanner"** bridge and simulated test badge image generator.

- **Optical Color Detection Scanner (`/scanner`)**:
  - **Triple Input Modalities**:
    1. *Live Webcam Stream* with targeting ROI reticle.
    2. *Image Upload* (JPEG / PNG drag-and-drop).
    3. *Digital Simulator Direct Bridge*.
  - **OpenCV Vision Engine**: Extracts dominant colors within the central 45% Region of Interest (ROI), eliminating border shadows and specular reflections.
  - **CIE $L^*a^*b^*$ Perceptual Space**: Separates lightness ($L^*$) from chromatic vectors ($a^*, b^*$) and calculates Euclidean color distance $\Delta E$.
  - **Prototype Environmental Compensation**: Dynamic sliders for Temperature ($20^\circ\text{C} - 45^\circ\text{C}$) and Relative Humidity ($30\% - 90\%$).
  - **Dual Scan Checkpoints**: Distinct `ENTRY` (shift baseline) and `EXIT` (shift end) recording.
  - **Safe Shift Subtraction**: `shift_exposure = max(0, exit_reading - entry_reading)`. Safely handles insufficient change when exit < entry.

- **Predefined Threshold Engine**:
  - `SAFE`: $0 - 25$ ppm (Green)
  - `CAUTION`: $25 - 50$ ppm (Yellow / Amber)
  - `HIGH`: $50 - 100$ ppm (Orange)
  - `CRITICAL`: $> 100$ ppm (Red / Dark Brown)

- **Industrial Administrator Dashboard (`/dashboard`)**:
  - 4 Key Metric KPIs: Active Workers, Today's Scans, High Risk Personnel Alerts, Total Cumulative System Exposure.
  - 3 Interactive Chart.js Visualizations:
    1. 7-Day Facility Average Exposure Trend.
    2. Workforce Risk Category Distribution Doughnut.
    3. Cumulative Exposure Comparison by Operator.
  - High-risk worker alert table and recent scans feed.
  - Optical badge validity monitor.

- **Dedicated Worker Personal Portal (`/worker-dashboard`)**:
  - Instant worker profile switcher (`W101` to `W105`).
  - Current reading, Today's shift increment, Cumulative badge exposure.
  - Personal chronological exposure progression chart and ambient condition audits.

- **Personnel & Badge Management (`/workers`)**:
  - Worker CRUD with search, department filtering, and active/inactive toggle.
  - Badge lifecycle tracking (`VALID`, `NEAR EXPIRY`, `EXPIRED`) with automatic age calculation and 1-click renewal.

- **Calibration Administration (`/calibration`)**:
  - Metrological reference point editor with live OpenCV CIELAB coordinate generation.
  - Reset to default prototype calibration curve.
  - Environmental compensation coefficient tuning.

---

## 2. Technology Stack

- **Backend**: Python 3.10+, Flask 3.0, Flask-SQLAlchemy 3.1, Flask-CORS, PyMySQL, Cryptography
- **Computer Vision & Math**: OpenCV (`cv2`), NumPy, scikit-learn
- **Database**: MySQL (WAMP Server on port 3306), Database name: `h2sense`
- **Frontend**: HTML5, Vanilla CSS3 (Custom Industrial Dark System), Vanilla JavaScript (ES6+), Bootstrap 5, Chart.js 4, Font Awesome 6
- **Architecture**: Modular Flask Blueprints, centralized service layer, RESTful JSON APIs

---

## 3. Project Directory Structure

```text
sih26/
├── app.py                     # Flask application factory and runner
├── config.py                  # Environment & database configuration
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
├── .env.example               # Template environment configuration
├── README.md                  # Complete documentation
│
├── models/                    # SQLAlchemy database models
│   ├── __init__.py
│   ├── worker.py              # Worker entity & relationships
│   ├── badge.py               # Optical badge entity & validity logic
│   ├── exposure.py            # Entry/Exit exposure scan records
│   └── calibration.py         # Reference calibration points
│
├── services/                  # Business logic & algorithms
│   ├── __init__.py
│   ├── color_detector.py      # OpenCV ROI extraction, RGB, HSV, CIELAB
│   ├── calibration_service.py # Reference interpolation & confidence index
│   ├── exposure_service.py    # Env compensation, shift subtraction, thresholds
│   └── validation_service.py  # Input parameter validation
│
├── routes/                    # Modular Flask Blueprints
│   ├── __init__.py
│   ├── main.py                # Landing page, login/logout, session
│   ├── simulator.py           # Digital Sensor Simulator route
│   ├── scanner.py             # Optical scanner workstation route
│   ├── dashboard.py           # Admin and Worker dashboards
│   ├── workers.py             # Worker directory and detail views
│   ├── calibration.py         # Calibration admin route
│   └── api.py                 # RESTful JSON API endpoints
│
├── templates/                 # Jinja2 HTML templates
│   ├── base.html              # Core layout, navbar, disclaimer banner, footer
│   ├── landing.html           # High-impact industrial landing page
│   ├── login.html             # Prototype authentication & role switcher
│   ├── simulator.html         # Digital Sensor Simulator interface
│   ├── scanner.html           # Scanner workstation with camera & upload
│   ├── dashboard.html         # Administrator analytics dashboard
│   ├── worker_dashboard.html  # Dedicated worker exposure portal
│   ├── workers.html           # Personnel directory & registration modal
│   ├── worker_detail.html     # Worker dossier with scan history & charts
│   └── calibration.html       # Calibration curve & threshold admin
│
├── static/                    # Frontend assets
│   ├── css/
│   │   └── style.css          # Dark industrial aesthetic stylesheet
│   ├── js/
│   │   ├── main.js            # Toast notifications & UI utilities
│   │   ├── camera.js          # WebRTC getUserMedia & frame capture
│   │   ├── simulator.js       # Color interpolation & preset controllers
│   │   ├── scanner.js         # Scan orchestrator & API integration
│   │   └── dashboard.js       # Chart.js analytics charts
│   └── uploads/               # Temporary storage for uploaded badges
│
└── database/
    ├── schema.sql             # Complete MySQL DDL schema script
    └── seed_data.py           # Demo workers (W101-W105), badges, scan history
```

---

## 4. Installation & Setup Guide

### Prerequisites
1. **Python 3.10+**: Ensure Python is added to your system `PATH`.
2. **WAMP Server**: Ensure WAMP is installed and running (Apache + MySQL on port 3306).

### Step 1: Clone or Navigate to Project
```powershell
cd c:\Users\kishore\OneDrive\Desktop\sih26
```

### Step 2: Set Up Python Virtual Environment (Optional but Recommended)
```powershell
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Configure Database in WAMP MySQL
1. Open your browser and navigate to **phpMyAdmin**:
   ```text
   http://localhost/phpmyadmin
   ```
2. Log in (default username: `root`, password: empty).
3. Create the database:
   ```sql
   CREATE DATABASE IF NOT EXISTS h2sense CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
4. *(Optional)* If you wish to import the schema manually, click the **Import** tab in phpMyAdmin and upload `database/schema.sql`. (Note: The Flask application automatically verifies and initializes tables and seed data upon startup!).

### Step 5: Configure Environment Variables
Copy `.env.example` to `.env`, then set a unique random `SECRET_KEY` and adjust the database settings for your environment. Keep `.env` local; do not commit it.
```ini
FLASK_APP=app.py
FLASK_ENV=development
DEBUG=True
SECRET_KEY=replace-with-a-random-secret-key

# Database Configuration (WAMP Server default)
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=h2sense
DB_USER=root
DB_PASSWORD=

# Environmental Baselines
TEMP_BASELINE=25.0
TEMP_COEFFICIENT=0.35
HUMIDITY_BASELINE=50.0
HUMIDITY_COEFFICIENT=0.15

# Threshold Configuration
THRESHOLD_SAFE=25.0
THRESHOLD_CAUTION=50.0
THRESHOLD_HIGH=100.0
```

### Step 6: Start the Application
Run the Flask application:
```powershell
python app.py
```
Output should confirm:
```text
[INFO] Initializing database tables...
[INFO] Database tables verified. Checking seed data...
[INFO] Seed data verified.
[INFO] Starting H2SENSE Industrial Exposure System on http://127.0.0.1:5000
```

### Step 7: Open in Browser
Open your browser and navigate to:
```text
http://127.0.0.1:5000
```

---

## 5. Demonstration Walkthrough Sequence

Follow this exact sequence to present a complete, presentation-ready demonstration:

1. **Explore the Landing Page (`/`)**:
   - Note the industrial dark aesthetic, problem breakdown, OpenCV CIELAB workflow explanation, and live hero sensor simulation.
2. **Launch Digital Sensor Simulator (`/simulator`)**:
   - Click the preset buttons (`0, 10, 25, 50, 75, 100, 150, 200`).
   - Notice the smooth color transition from vibrant Safe Green $\rightarrow$ Lime $\rightarrow$ Caution Amber $\rightarrow$ High Orange $\rightarrow$ Critical Dark Red.
   - Click **`25 ppm`** (Safe Green).
   - Click **"Send to Scanner Workstation"**.
3. **Perform an ENTRY Scan (`/scanner`)**:
   - The scanner receives the simulated green color (`RGB: 163, 230, 53`).
   - Select operator **`W104 — Sarah Jenkins`** (Assigned badge: `BD-W104`).
   - Adjust Temperature to $26^\circ\text{C}$ and Humidity to $52\%$.
   - Click **`[ RECORD ENTRY SCAN ]`**.
   - Confirmation toast appears indicating the entry baseline reading has been stored in MySQL.
4. **Simulate High Exposure during Shift**:
   - Return to `/simulator` (or switch to the "Digital Simulator Bridge" tab in the scanner).
   - Select preset **`75 ppm`** (High Risk Orange, `RGB: 249, 115, 22`).
   - Send to scanner.
5. **Perform an EXIT Scan (`/scanner`)**:
   - Set ambient conditions to higher heat/humidity (e.g., $31^\circ\text{C}$ and $72\%$ RH).
   - Notice the Environmental Correction layer adjusts the reading: $+5.4$ ppm.
   - Select **`W104 — Sarah Jenkins`**.
   - Click **`[ RECORD EXIT SCAN ]`**.
   - The system calculates:
     $$\Delta E_{\text{shift}} = E_{\text{exit}} - E_{\text{entry}} \approx 50\text{ ppm}$$
     and increments cumulative badge exposure.
6. **Inspect Worker Personal Dossier (`/worker-dashboard`)**:
   - Select `W104`.
   - Verify the newly recorded Entry and Exit scans appear in the chronological table with color swatches, raw and corrected values, and shift increments.
   - Observe the personal exposure curve updating dynamically.
7. **Inspect Plant Administrator Dashboard (`/dashboard`)**:
   - Review updated KPI metric cards, the 7-day facility average curve, the risk category distribution doughnut, and the high-risk worker alert table.
8. **Test Boundary & Edge Cases**:
   - Test an exit reading that is lower than the entry reading to confirm safe handling: *"Reading change is insufficient to calculate a valid shift increment."*
   - View Worker `W103` to verify the badge lifecycle monitor flags it as `NEAR EXPIRY`.
   - Open `/calibration` to inspect the underlying MySQL calibration points.

---

## 6. Pre-seeded Demo Accounts & Personnel

| Worker Code | Name | Department | Role | Active Badge | Expiry Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **W101** | Marcus Vance | Refinery Operations | Senior Lead Operator | `BD101` | Valid (180d) |
| **W102** | Elena Rostova | Inspection & QA | Industrial Hygienist | `BD102` | Valid (90d) |
| **W103** | David Chen | Maintenance | Pipefitting Specialist | `BD103` | **Near Expiry (4d)** |
| **W104** | Sarah Jenkins | Production | Hydrocracker Operator | `BD104` | Valid (150d) |
| **W105** | Tariq Al-Mansoor | Plant Safety | Safety Auditor | `BD105` | Valid (240d) |

---

## 7. REST API Documentation

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/workers` | List workers with search/dept filters |
| `POST` | `/api/workers` | Register new worker and issue initial badge |
| `GET` | `/api/workers/<id>` | Worker profile, badge history, scan logs |
| `POST` | `/api/detect-color` | OpenCV color extraction from image/bytes/RGB |
| `POST` | `/api/calculate-exposure` | CIELAB calibration lookup & env compensation |
| `POST` | `/api/record-scan` | Commit ENTRY or EXIT scan to MySQL |
| `GET` | `/api/exposure/<worker_id>` | Complete exposure history for a worker |
| `GET` | `/api/dashboard/stats` | Aggregated telemetry & Chart.js datasets |
| `GET` | `/api/calibration` | Calibration coordinates & environmental baselines |
| `POST` | `/api/calibration` | Add new calibration reference point |
| `POST` | `/api/badges` | Issue new or replacement badge |

---

## 8. Limitations & Future Scope

- **Chemical Substrate**: This software prototype operates with digital sensor simulations. Physical commercialization will require chemical dye immobilization (e.g., lead acetate or silver nanoparticle indicators), shelf-life degradation studies, and gas chamber validation.
- **Ambient Lighting**: Computer vision accuracy in real-world deployment can be further enhanced using physical calibration reference color rings printed directly onto the badge border to normalize variable ambient white balance.
