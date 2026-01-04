
# 🧪 Universal Thermodynamic Solver

A web application for solving **Rankine cycles** and **unsteady tank discharge processes**.  
It combines a FastAPI backend with a Streamlit frontend, uses **CoolProp** for thermodynamic properties, and logs results into an SQLite database with history viewing.

---

## ✨ Features

- **Rankine Cycle Analysis**
  - Calculates turbine/pump work, net work, and thermal efficiency.
  - Displays state properties (h, s, v, T) at each point.
  - Plots **T–s** and **P–v** diagrams (toggle or view both side by side).
- **Tank Discharge Analysis**
  - Computes maximum turbine work from a rigid tank discharging to atmosphere.
  - Shows initial/final mass, discharged mass, and final temperature.
- **History Logging**
  - All runs are logged into an SQLite database.
  - View history in the frontend as a table.
  - Clear history with a single click.
- **Export Results**
  - Download results as CSV for documentation or further analysis.
- **Robust Validation**
  - Input checks for pressures, volumes, and temperatures.
  - Friendly error messages for invalid inputs.

---

## 🛠️ Tech Stack

- **Backend:** FastAPI, CoolProp, SQLite  
- **Frontend:** Streamlit, Plotly, Pandas  
- **Language:** Python 3.9+

---

## ⚙️ Installation

1. Clone the repository:
   ```
   git clone https://github.com/fola3k/THERMOapp.git
   cd THERMOapp
   ```

2. Install dependencies:
   ```
   pip install fastapi uvicorn streamlit coolprop plotly pandas requests
   ```

---

## 🚀 Usage

### Start the backend
```
uvicorn main:app --reload
```
Backend runs at `http://127.0.0.1:8000`.

### Start the frontend
```
streamlit run frontend.py
```
Frontend runs at `http://localhost:8501`.

---

## 📊 Example Problems

- **Rankine Cycle:**  
  Boiler at 30 bar, turbine inlet 350 °C, condenser at 0.1 bar.  
  → Efficiency and net work are calculated, with T–s and P–v diagrams plotted.

- **Tank Discharge:**  
  Tank volume 0.3 m³, initial 35 bar at 40 °C, final 1 bar.  
  → Maximum turbine work, mass discharged, and final temperature are shown.

---

## 📜 History Management

- All simulations are logged in `thermo.db`.  
- View history in the frontend under **Simulation History**.  
- Clear history with the **Clear History** button.

---

## 📂 Project Structure

```
THERMOapp/
├── backend.py       # FastAPI backend
├── frontend.py      # Streamlit frontend
├── thermo.db        # SQLite database (auto-created)
├── SaturatedWater.csv
├── SuperheatedSteam.csv
└── readme.md        # Documentation
```

---

## 🧩 Future Improvements

- Add Ideal Gas vs Real Fluid toggle for tank discharge.  
- Overlay saturation dome on P–v diagram.  
- Support more cycles (Brayton, Otto, Diesel).  

