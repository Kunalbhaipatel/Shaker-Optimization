import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Shaker Health Dashboard", layout="wide")

# Style
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500&display=swap');
    html, body, [class*="css"] {
        font-family: 'Roboto', sans-serif;
    }
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ───── Sidebar Branding ─────
try:
    st.sidebar.image("assets/Prodigy_IQ_logo.png", width=200)
except:
    st.sidebar.warning("⚠️ Logo failed to load.")

df_mesh_type = st.sidebar.selectbox("Select Screen Mesh Type", ["API 100", "API 140", "API 170", "API 200"])
SCREEN_MESH_CAPACITY = {"API 100": 250, "API 140": 200, "API 170": 160, "API 200": 120}
mesh_capacity = SCREEN_MESH_CAPACITY[df_mesh_type]

util_threshold = st.sidebar.slider("Utilization Threshold (%)", 50, 100, 80)

# Sidebar shaker image
try:
    st.sidebar.image("Hyperpool_SideView_Compression1_LR-removebg-preview (1).png",
                     caption="Hyperpool Shaker Unit", use_container_width=True)
except:
    st.sidebar.warning("⚠️ Shaker image failed to load.")

# ───── Upload File ─────
st.title("🛠️ Real-Time Shaker Monitoring Dashboard")
uploaded_file = st.file_uploader("📤 Upload Shaker CSV Data", type=["csv"])

if uploaded_file:
    @st.cache_data(ttl=60)
    def load_data(file):
        return pd.read_csv(file)

    df = load_data(uploaded_file)

    # Process timestamp
    df['Timestamp'] = pd.to_datetime(df['YYYY/MM/DD'] + ' ' + df['HH:MM:SS'], errors='coerce')
    df = df.dropna(subset=['Timestamp'])
    df['Date'] = df['Timestamp'].dt.date

    # ───── Calendar Filter ─────
    if 'Date' in df.columns:
        date_options = sorted(df['Date'].dropna().unique())
        selected_date = st.sidebar.selectbox("📅 Select Date to View Performance", date_options)
        df = df[df['Date'] == selected_date]

    # Compute screen utilization if not available
    if 'Screen Utilization (%)' not in df.columns:
        if {'Weight on Bit (klbs)', 'MA_Flow_Rate (gal/min)'}.issubset(df.columns):
            df['Solids Volume Rate (gpm)'] = df['Weight on Bit (klbs)'] * df['MA_Flow_Rate (gal/min)'] / 100
            df['Screen Utilization (%)'] = (df['Solids Volume Rate (gpm)'] / mesh_capacity) * 100

    # ───── Overview KPIs & Screen Life ─────
    with st.expander("📌 Summary: Drilling & Shaker Overview", expanded=True):
        try:
            shaker_col = 'SHAKER #3 (PERCENT)'
            screen_col = 'Screen Utilization (%)'
            depth_col = 'Bit Depth (feet)' if 'Bit Depth (feet)' in df.columns else 'Hole Depth (feet)'

            total_depth = df[depth_col].max()
            shaker_avg = df[shaker_col].mean()
            shaker_min = df[shaker_col].min()
            shaker_max = df[shaker_col].max()

            screen_avg = df[screen_col].mean()
            screen_min = df[screen_col].min()
            screen_max = df[screen_col].max()
            screen_life = 120 - ((screen_avg / 100) * 30)

            col1, col2, col3 = st.columns(3)
            col1.metric("🛢️ Depth Drilled (ft)", f"{total_depth:,.0f}")
            col2.metric("🔄 Shaker Load", f"{shaker_avg:.1f}%", f"{shaker_min:.1f}–{shaker_max:.1f}%")
            col3.metric("📉 Screen Utilization", f"{screen_avg:.1f}%", f"{screen_min:.1f}–{screen_max:.1f}%")
            st.metric("🧮 Est. Remaining Screen Life (hrs)", f"{screen_life:.1f} hrs")

            if shaker_avg < 0 or shaker_max > 150:
                st.error("🔴 Shaker load anomalies detected — check for mechanical issues or data errors.")
            elif shaker_avg < 20:
                st.warning("⚠️ Low shaker throughput — possible screen blinding or underflow.")

        except Exception as e:
            st.warning(f"Summary stats unavailable: {e}")

    # ───── Tabs ─────
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Charts", "🔍 Drop Flags", "📊 Efficiency", "📋 Raw Data"])

    with tab1:
        st.subheader("📈 Shaker Output")
        try:
            fig = px.line(df.tail(1000), x='Timestamp', y='SHAKER #3 (PERCENT)', title="SHAKER #3 - Last 1000 Points")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Chart error: {e}")

    with tab2:
        st.subheader("🔍 Shaker Drop Detection Flags")
        try:
            drop_df = df[df['SHAKER #3 (PERCENT)'] < -10]
            fig_flag = go.Figure()
            fig_flag.add_trace(go.Scatter(x=df['Timestamp'], y=df['SHAKER #3 (PERCENT)'],
                                          mode='lines', name='SHAKER #3'))
            fig_flag.add_trace(go.Scatter(x=drop_df['Timestamp'], y=drop_df['SHAKER #3 (PERCENT)'],
                                          mode='markers', name='Drop Flags',
                                          marker=dict(color='red', size=10, symbol='x')))
            fig_flag.update_layout(title='SHAKER #3 Drop Detection', yaxis_title='% Load')
            st.plotly_chart(fig_flag, use_container_width=True)
        except Exception as e:
            st.warning(f"Drop detection failed: {e}")

    with tab3:
        st.subheader("🥧 Solids Removal Efficiency")
        try:
            in_rate = (df['Weight on Bit (klbs)'] * df['MA_Flow_Rate (gal/min)']) / 100
            out_rate = df['SHAKER #3 (PERCENT)']
            efficiency = (out_rate / (in_rate + 1e-5)) * 100
            eff_avg = efficiency.mean()
            pie = px.pie(values=[eff_avg, 100 - eff_avg], names=['Removed Solids', 'Losses'],
                         title="Solids Removal Efficiency")
            st.plotly_chart(pie, use_container_width=True)
        except Exception as e:
            st.warning(f"Efficiency plot error: {e}")

    with tab4:
        st.subheader("📋 Full Dataset")
        st.dataframe(df, use_container_width=True)

else:
    st.info("📂 Please upload a shaker CSV to begin.")
