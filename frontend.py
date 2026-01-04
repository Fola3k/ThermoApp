import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(layout="wide", page_title="Universal Thermo Solver")

st.title("🧪 Universal Thermodynamic Solver")
st.write("Rankine Cycles & Unsteady Flow Processes (Air, Methane, Water, etc.)")

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("Configuration")

process_mode = st.sidebar.selectbox("Select Process Type", ["Rankine Cycle", "Tank Discharge"])

if process_mode == "Tank Discharge":
    fluid_type = st.sidebar.selectbox("Select Fluid", ["Air", "Methane", "Nitrogen", "Oxygen", "Water", "CO2"])
else:
    fluid_type = "Water"
    st.sidebar.info("Fluid locked to 'Water' for Rankine Cycle.")

inputs = {}

# Rankine inputs
if process_mode == "Rankine Cycle":
    with st.sidebar.expander("🔥 Cycle Parameters", expanded=True):
        inputs["p_high"] = st.number_input("Boiler Pressure (bar)", value=35.0, min_value=0.01, help="Typical: 30–150 bar")
        inputs["t_high"] = st.number_input("Turbine Inlet Temp (°C)", value=350.0, help="Typical: 350–600 °C")
        inputs["p_low"] = st.number_input("Condenser Pressure (bar)", value=0.1, min_value=0.001, help="Typical: 0.05–0.2 bar")
    diagram_type = st.sidebar.selectbox("Select Diagram Type", ["T-s Diagram", "P-v Diagram", "Both"])

# Tank discharge inputs
elif process_mode == "Tank Discharge":
    with st.sidebar.expander("📦 Tank Parameters", expanded=True):
        inputs["volume"] = st.number_input("Tank Volume (m³)", value=0.3, min_value=0.0001)
        inputs["p_init"] = st.number_input("Initial Pressure (bar)", value=35.0, min_value=0.01)
        inputs["t_init"] = st.number_input("Initial Temp (°C)", value=40.0)
        inputs["p_final"] = st.number_input("Final Pressure (bar)", value=1.0, min_value=0.01)

# --- ACTIONS ---
run = st.button("Run Simulation", type="primary")
clear_hist = st.button("Clear History")

if clear_hist:
    try:
        resp = requests.delete("http://127.0.0.1:8000/history/clear")
        msg = resp.json()
        if "status" in msg:
            st.success("History cleared.")
        else:
            st.warning(msg.get("error", "Unknown response"))
    except Exception as e:
        st.error(f"Could not clear history: {e}")

if run:
    if process_mode == "Rankine Cycle":
        if inputs["p_low"] >= inputs["p_high"]:
            st.error("Condenser pressure must be lower than boiler pressure.")
        else:
            payload = {
                "process_type": process_mode,
                "fluid": fluid_type,
                "p_high_bar": inputs.get("p_high", 0),
                "t_high_c": inputs.get("t_high", 0),
                "p_low_bar": inputs.get("p_low", 0),
                "volume_m3": 0.0,
                "p_init_bar": 0.0,
                "t_init_c": 0.0,
                "p_final_bar": 0.0,
            }
            try:
                response = requests.post("http://127.0.0.1:8000/calculate", json=payload)
                data = response.json()

                if "error" in data:
                    st.error(data["error"])
                elif data["mode"] == "Rankine":
                    # Metrics
                    c1, c2 = st.columns(2)
                    c1.metric("Thermal Efficiency", f"{data['efficiency']} %")
                    c2.metric("Net Work", f"{data['work']} kJ/kg")

                    # State table
                    st.subheader("State Properties (1–4)")
                    states = data.get("states", {})
                    df_states = pd.DataFrame({
                        "State": [1, 2, 3, 4],
                        "P (bar)": states.get("P_bar", []),
                        "T (K)": [round(x, 3) for x in states.get("T", [])],
                        "h (J/kg)": [round(x, 3) for x in states.get("h", [])],
                        "s (J/kg·K)": [round(x, 6) for x in states.get("s", [])],
                        "v (m³/kg)": [round(x, 9) for x in states.get("v", [])],
                    })
                    st.dataframe(df_states, use_container_width=True)

                    # Diagrams
                    plot = data['plot']
                    if diagram_type == "T-s Diagram":
                        fig_ts = go.Figure()
                        fig_ts.add_trace(go.Scatter(
                            x=plot['x_dome_l'], y=plot['y_dome'],
                            line=dict(color='gray', dash='dash'), name='Liquid Dome'
                        ))
                        fig_ts.add_trace(go.Scatter(
                            x=plot['x_dome_r'], y=plot['y_dome'],
                            line=dict(color='gray', dash='dash'), name='Vapor Dome', showlegend=False
                        ))
                        fig_ts.add_trace(go.Scatter(
                            x=plot['x_cycle'], y=plot['y_cycle'],
                            line=dict(color='red', width=3), name='Cycle'
                        ))
                        fig_ts.update_layout(title="T-s Diagram", xaxis_title="Entropy (J/kg·K)", yaxis_title="Temperature (K)")
                        st.plotly_chart(fig_ts, use_container_width=True)

                    elif diagram_type == "P-v Diagram":
                        fig_pv = go.Figure()
                        fig_pv.add_trace(go.Scatter(
                            x=plot['v_points'], y=plot['p_points'],
                            line=dict(color='blue', width=3), name='Cycle'
                        ))
                        fig_pv.update_layout(title="P-v Diagram", xaxis_title="Specific Volume (m³/kg)", yaxis_title="Pressure (bar)")
                        st.plotly_chart(fig_pv, use_container_width=True)

                    elif diagram_type == "Both":
                        cA, cB = st.columns(2)
                        with cA:
                            fig_ts = go.Figure()
                            fig_ts.add_trace(go.Scatter(
                                x=plot['x_dome_l'], y=plot['y_dome'],
                                line=dict(color='gray', dash='dash'), name='Liquid Dome'
                            ))
                            fig_ts.add_trace(go.Scatter(
                                x=plot['x_dome_r'], y=plot['y_dome'],
                                line=dict(color='gray', dash='dash'), name='Vapor Dome', showlegend=False
                            ))
                            fig_ts.add_trace(go.Scatter(
                                x=plot['x_cycle'], y=plot['y_cycle'],
                                line=dict(color='red', width=3), name='Cycle'
                            ))
                            fig_ts.update_layout(title="T-s Diagram", xaxis_title="Entropy (J/kg·K)", yaxis_title="Temperature (K)")
                            st.plotly_chart(fig_ts, use_container_width=True)
                        with cB:
                            fig_pv = go.Figure()
                            fig_pv.add_trace(go.Scatter(
                                x=plot['v_points'], y=plot['p_points'],
                                line=dict(color='blue', width=3), name='Cycle'
                            ))
                            fig_pv.update_layout(title="P-v Diagram", xaxis_title="Specific Volume (m³/kg)", yaxis_title="Pressure (bar)")
                            st.plotly_chart(fig_pv, use_container_width=True)

                    # Download results
                    st.subheader("Download Results")
                    df_download = df_states.copy()
                    df_download["Efficiency (%)"] = data["efficiency"]
                    df_download["Net Work (kJ/kg)"] = data["work"]
                    st.download_button(
                        "Download Results as CSV",
                        df_download.to_csv(index=False),
                        file_name="rankine_results.csv",
                        mime="text/csv"
                    )

            except Exception as e:
                st.error(f"Connection Error: {e}. Is backend running?")

    elif process_mode == "Tank Discharge":
        if inputs["p_final"] > inputs["p_init"]:
            st.error("Final pressure must be less than or equal to initial pressure for discharge.")
        else:
            payload = {
                "process_type": process_mode,
                "fluid": fluid_type,
                "p_high_bar": 0.0,
                "t_high_c": 0.0,
                "p_low_bar": 0.0,
                "volume_m3": inputs.get("volume", 0),
                "p_init_bar": inputs.get("p_init", 0),
                "t_init_c": inputs.get("t_init", 0),
                "p_final_bar": inputs.get("p_final", 0),
            }
            try:
                response = requests.post("http://127.0.0.1:8000/calculate", json=payload)
                data = response.json()

                if "error" in data:
                    st.error(data["error"])
                elif data["mode"] == "Unsteady":
                    st.success(f"✅ Simulation Complete for {fluid_type}")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Max Work Output", f"{data['work_max_kj']} kJ")
                    c2.metric("Initial Mass", f"{data['mass_initial']} kg")
                    c3.metric("Final Mass", f"{data['mass_final']} kg")
                    c4.metric("Mass Discharged", f"{data.get('mass_exit', 0)} kg")
                    st.info(f"Final Temperature inside tank: {data['temp_final_k']} K")

                    # Download results
                    st.subheader("Download Results")
                    df_download = pd.DataFrame([data])
                    st.download_button(
                        "Download Results as CSV",
                        df_download.to_csv(index=False),
                        file_name="tank_discharge_results.csv",
                        mime="text/csv"
                    )

            except Exception as e:
                st.error(f"Connection Error: {e}. Is backend running?")

# --- HISTORY SECTION ---
st.subheader("📜 Simulation History")
try:
    hist_response = requests.get("http://127.0.0.1:8000/history")
    hist_data = hist_response.json()

    if "history" in hist_data and len(hist_data["history"]) > 0:
        df = pd.DataFrame(hist_data["history"])
        # Rename columns for readability
        df = df.rename(columns={
            "mode": "Mode",
            "fluid": "Fluid",
            "result_1": "Result 1",
            "result_2": "Result 2",
            "timestamp": "Timestamp"
        })
        # Parse timestamps flexibly and format for display
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No history available yet.")
except Exception as e:
    st.error(f"Could not load history: {e}")