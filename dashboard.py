import streamlit as st
import asyncio
import threading
import logging
from collections import deque
from datetime import datetime
from main import TradingAssistant
from config import settings

# --- Configuration & State ---
st.set_page_config(page_title="Trading Assistant Dashboard", page_icon="📈", layout="wide")

if 'logs' not in st.session_state:
    st.session_state.logs = deque(maxlen=50)  # Store last 50 log entries
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
if 'assistant_instance' not in st.session_state:
    st.session_state.assistant_instance = None

# --- UI Callback ---
def add_log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.appendleft(f"[{timestamp}] {msg}")

# --- Background Worker ---
def run_assistant_thread(assistant):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(assistant.run())
    except Exception as e:
        add_log(f"Error: {e}")
    finally:
        loop.close()

# --- Dashboard Layout ---
st.title("🛡️ Institutional Trading Assistant")
st.markdown("---")

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Scanner Settings")
    assets = st.multiselect("Monitoring Assets",
                            options=["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT"],
                            default=settings.DEFAULT_ASSETS)
    st.divider()
    st.write(f"**RSI Period:** {settings.RSI_PERIOD}")
    st.write(f"**SMA Filter:** 200")
    st.write(f"**Lookback:** {settings.LOOKBACK_WINDOW}m")

# Main Control Panel
status_col, button_col1, button_col2 = st.columns([2, 1, 1])

with status_col:
    status_color = "green" if st.session_state.is_running else "red"
    status_text = "ACTIVE & STREAMING" if st.session_state.is_running else "SLEEPING (POWER SAVER)"
    st.subheader(f"Status: :{status_color}[{status_text}]")

with button_col1:
    if st.button("▶️ START SCANNER", use_container_width=True, type="primary", disabled=st.session_state.is_running):
        st.session_state.assistant_instance = TradingAssistant(assets, ui_callback=add_log)
        thread = threading.Thread(target=run_assistant_thread, args=(st.session_state.assistant_instance,), daemon=True)
        thread.start()
        st.session_state.is_running = True
        st.rerun()

with button_col2:
    if st.button("⏹️ STOP SCANNER", use_container_width=True, disabled=not st.session_state.is_running):
        if st.session_state.assistant_instance:
            for streamer in st.session_state.assistant_instance.streamers:
                streamer.stop()
        st.session_state.is_running = False
        st.session_state.assistant_instance = None
        st.rerun()

st.markdown("---")

# Live Logs Section
st.subheader("📟 Real-Time Activity Log")
log_container = st.container(height=400, border=True)

with log_container:
    if not st.session_state.logs:
        st.write("_Waiting for scanner to start..._")
    for log in st.session_state.logs:
        st.write(log)

# Auto-refresh to see logs update
if st.session_state.is_running:
    st.empty() # Placeholder for refresh
    async def refresh_trigger():
        await asyncio.sleep(2)
        st.rerun()
    # Note: Streamlit Community Cloud doesn't support complex async triggers inside the UI flow
    # as easily as local, but for this setup, we use a simple interval-based refresh or manual.
    # We will use st_autorefresh if available, but for standard deployment, a sleep/rerun works.
    st.caption("Auto-refreshing every 5 seconds...")
    import time
    time.sleep(5)
    st.rerun()
