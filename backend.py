from fastapi import FastAPI
from pydantic import BaseModel
from CoolProp.CoolProp import PropsSI
import numpy as np
import sqlite3
import datetime

app = FastAPI()
DB_FILE = "thermo.db"

print("✅ BACKEND LOADED: Multi-Fluid & Unsteady Flow Support")

# --- DATA MODELS ---
class ThermoInput(BaseModel):
    process_type: str  # "Rankine Cycle" or "Tank Discharge"
    fluid: str         # "Water", "Air", "Methane", etc.
    
    # Rankine Inputs
    p_high_bar: float = 35.0
    t_high_c: float = 350.0
    p_low_bar: float = 0.1
    
    # Unsteady/Tank Inputs
    volume_m3: float = 0.3
    p_init_bar: float = 35.0
    t_init_c: float = 40.0
    p_final_bar: float = 1.0

# --- LOGGING HELPER ---
def log_to_db(mode, fluid, res1, res2):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS GlobalLogs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT, fluid TEXT,
                result_1 REAL, result_2 REAL,
                timestamp TEXT
            )
        ''')
        # Use consistent ISO format with 'T' separator for easier parsing
        ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        cursor.execute(
            'INSERT INTO GlobalLogs (mode, fluid, result_1, result_2, timestamp) VALUES (?, ?, ?, ?, ?)',
            (mode, fluid, res1, res2, ts)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Logging Error: {e}")

@app.get("/history")
def get_history():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT mode, fluid, result_1, result_2, timestamp FROM GlobalLogs ORDER BY id DESC LIMIT 100")
        rows = cursor.fetchall()
        conn.close()
        history = [
            {"mode": r[0], "fluid": r[1], "result_1": r[2], "result_2": r[3], "timestamp": r[4]}
            for r in rows
        ]
        return {"history": history}
    except Exception as e:
        return {"error": f"History Error: {str(e)}"}

@app.delete("/history/clear")
def clear_history():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM GlobalLogs")
        conn.commit()
        conn.close()
        return {"status": "History cleared"}
    except Exception as e:
        return {"error": f"Clear History Error: {str(e)}"}

@app.post("/calculate")
def calculate_thermo(data: ThermoInput):
    try:
        # --- VALIDATION ---
        if data.process_type == "Rankine Cycle":
            if data.p_low_bar <= 0 or data.p_high_bar <= 0:
                return {"error": "Pressures must be positive for Rankine Cycle."}
            if data.p_low_bar >= data.p_high_bar:
                return {"error": "Condenser pressure must be lower than boiler pressure."}
        elif data.process_type == "Tank Discharge":
            if data.volume_m3 <= 0:
                return {"error": "Tank volume must be positive."}
            if data.p_init_bar <= 0 or data.p_final_bar <= 0:
                return {"error": "Pressures must be positive for Tank Discharge."}
            if data.p_final_bar > data.p_init_bar:
                return {"error": "Final pressure must be less than or equal to initial pressure for discharge."}

        # --- MODE 1: RANKINE CYCLE ---
        if data.process_type == "Rankine Cycle":
            fluid = "Water"
            P_boiler = data.p_high_bar * 1e5
            T_boiler = data.t_high_c + 273.15
            P_cond = data.p_low_bar * 1e5

            try:
                # 1. Condenser Exit (Sat Liquid)
                h1 = PropsSI('H', 'P', P_cond, 'Q', 0, fluid)
                s1 = PropsSI('S', 'P', P_cond, 'Q', 0, fluid)
                v1 = 1/PropsSI('D', 'P', P_cond, 'Q', 0, fluid)
                T1 = PropsSI('T','P',P_cond,'Q',0,fluid)
                
                # 2. Pump Exit (isentropic)
                s2 = s1
                h2 = PropsSI('H', 'P', P_boiler, 'S', s2, fluid)
                T2 = PropsSI('T', 'P', P_boiler, 'S', s2, fluid)
                v2 = 1/PropsSI('D', 'P', P_boiler, 'S', s2, fluid)

                # 3. Turbine Inlet (superheated)
                h3 = PropsSI('H', 'P', P_boiler, 'T', T_boiler, fluid)
                s3 = PropsSI('S', 'P', P_boiler, 'T', T_boiler, fluid)
                v3 = 1/PropsSI('D', 'P', P_boiler, 'T', T_boiler, fluid)

                # 4. Turbine Exit (isentropic to condenser pressure)
                s4 = s3
                h4 = PropsSI('H', 'P', P_cond, 'S', s4, fluid)
                T4 = PropsSI('T', 'P', P_cond, 'S', s4, fluid)
                v4 = 1/PropsSI('D', 'P', P_cond, 'S', s4, fluid)
            except Exception as e:
                return {"error": f"Property calculation error: {str(e)}"}

            w_turbine = h3 - h4
            w_pump = h2 - h1
            w_net = w_turbine - w_pump
            q_in = h3 - h2
            eff = (w_net / q_in) * 100 if q_in != 0 else 0.0
            
            # Saturation dome for T-s
            try:
                t_dome = np.linspace(273.16, 640.0, 50).tolist()
                s_liquid = [PropsSI('S','T',t,'Q',0,fluid) for t in t_dome]
                s_vapor  = [PropsSI('S','T',t,'Q',1,fluid) for t in t_dome]
            except Exception:
                t_dome, s_liquid, s_vapor = [], [], []

            log_to_db("Rankine", fluid, eff, w_net)

            return {
                "mode": "Rankine",
                "efficiency": round(eff, 2),
                "work": round(w_net/1000, 3),
                "states": {
                    "h": [h1, h2, h3, h4],
                    "s": [s1, s2, s3, s4],
                    "v": [v1, v2, v3, v4],
                    "T": [T1, T2, T_boiler, T4],
                    "P_bar": [data.p_low_bar, data.p_high_bar, data.p_high_bar, data.p_low_bar]
                },
                "plot": {
                    # T-s
                    "x_dome_l": s_liquid, "y_dome": t_dome,
                    "x_dome_r": s_vapor,
                    "x_cycle": [s1, s2, s3, s4, s1],
                    "y_cycle": [T1, T2, T_boiler, T4, T1],
                    # P-v (pressures in bar, volumes in m3/kg)
                    "v_points": [v1, v2, v3, v4, v1],
                    "p_points": [data.p_low_bar, data.p_high_bar, data.p_high_bar, data.p_low_bar, data.p_low_bar]
                }
            }

        # --- MODE 2: UNSTEADY FLOW (Tank Discharge) ---
        elif data.process_type == "Tank Discharge":
            fluid = data.fluid
            V = data.volume_m3
            P1 = data.p_init_bar * 1e5
            T1 = data.t_init_c + 273.15
            P2 = data.p_final_bar * 1e5

            try:
                # Initial state
                rho1 = PropsSI('D', 'P', P1, 'T', T1, fluid)
                u1   = PropsSI('U', 'P', P1, 'T', T1, fluid)
                s1   = PropsSI('S', 'P', P1, 'T', T1, fluid)
                m1   = rho1 * V

                # Remaining mass assumed isentropic (adiabatic reversible)
                s2 = s1
                T2 = PropsSI('T', 'P', P2, 'S', s2, fluid)
                rho2 = PropsSI('D', 'P', P2, 'S', s2, fluid)
                u2   = PropsSI('U', 'P', P2, 'S', s2, fluid)
                m2   = rho2 * V

                m_exit = max(m1 - m2, 0.0)
                h_exit = PropsSI('H', 'P', P2, 'S', s2, fluid)

                U_initial = m1 * u1
                U_final   = m2 * u2
                H_leaving = m_exit * h_exit

                W_max = (U_initial - U_final) - H_leaving
            except Exception as e:
                return {"error": f"Property calculation error: {str(e)}"}

            log_to_db("Unsteady", fluid, W_max, m_exit)

            return {
                "mode": "Unsteady",
                "work_max_kj": round(W_max / 1000.0, 3),
                "mass_initial": round(m1, 6),
                "mass_final": round(m2, 6),
                "mass_exit": round(m_exit, 6),
                "temp_final_k": round(T2, 3)
            }

    except Exception as e:
        return {"error": f"Calc Error: {str(e)}"}