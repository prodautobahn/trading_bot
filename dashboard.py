# dashboard.py
import streamlit as st
import pandas as pd
import logging
from queue import Queue
from datetime import datetime
import threading

# ---------- Imports ----------
import config
import alpaca_client
import bot_controller
import bot  # <-- your bot class lives here

# ---------- Logging ----------
log_queue = Queue()

class QueueHandler(logging.Handler):
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        msg = self.format(record)
        self.queue.put(msg)

# Attach the queue handler to the bot's logger
queue_handler = QueueHandler(log_queue)
queue_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
bot_logger = logging.getLogger("trading_bot")
bot_logger.setLevel(logging.INFO)
bot_logger.addHandler(queue_handler)

# ---------- Helper to get Alpaca client ----------
def get_client(mode):
    if mode == "Paper":
        return alpaca_client.AlpacaClient(
            config.ALPACA_BASE_URL_PAPER,
            config.ALPACA_API_KEY_PAPER,
            config.ALPACA_SECRET_KEY_PAPER,
        )
    else:
        return alpaca_client.AlpacaClient(
            config.ALPACA_BASE_URL_LIVE,
            config.ALPACA_API_KEY_LIVE,
            config.ALPACA_SECRET_KEY_LIVE,
        )

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Alpaca Trading Bot", layout="wide")

st.sidebar.title("Trading Bot Control")

# ---------- Initialize session state ----------
if "client" not in st.session_state:
    from alpaca_client import AlpacaClient
    import config
    st.session_state["client"] = AlpacaClient(
        base_url=config.ALPACA_BASE_URL_PAPER,
        api_key=config.ALPACA_API_KEY_PAPER,
        secret_key=config.ALPACA_SECRET_KEY_PAPER,
    )

if "bot" not in st.session_state:
    from bot import BotWrapper
    import logging
    st.session_state["bot"] = BotWrapper(
        client=st.session_state["client"],
        logger=logging.getLogger("trading_bot"),
    )

if "controller" not in st.session_state:
    from bot_controller import BotController
    st.session_state["controller"] = BotController(st.session_state["bot"])

if "mode" not in st.session_state:
    st.session_state["mode"] = "Paper"

# 1️⃣ Mode selector
mode = st.sidebar.radio("Mode", ("Paper", "Live"))
if mode != st.session_state.get("mode", mode):
    # Mode changed – re‑initialise client & bot
    st.session_state["client"] = get_client(mode)
    st.session_state["bot"] = bot.DummyTradingBot(st.session_state["client"])
    st.session_state["controller"] = bot_controller.BotController(st.session_state["bot"])
    st.session_state["mode"] = mode

client = st.session_state["client"]
controller = st.session_state["controller"]

# 2️⃣ Start / Stop buttons
col_start, col_stop = st.sidebar.columns(2)
if col_start.button("Start Bot"):
    started = controller.start()
    if started:
        st.sidebar.success("Bot started.")
    else:
        st.sidebar.warning("Bot already running.")

if col_stop.button("Stop Bot"):
    stopped = controller.stop()
    if stopped:
        st.sidebar.success("Bot stopped.")
    else:
        st.sidebar.warning("Bot not running.")

st.sidebar.write(f"✅ Bot running: {controller.is_running}")

# 3️⃣ Auto‑refresh every REFRESH_INTERVAL_SECONDS
from streamlit.runtime.scriptrunner import add_script_run_ctx
from streamlit_autorefresh import st_autorefresh

st_autorefresh(interval=config.REFRESH_INTERVAL_SECONDS * 1000, key="refresher")

# ─────────────────────────────────────────────────────────────────────
# MAIN PANEL
# ─────────────────────────────────────────────────────────────────────
st.title("📈 Trading Bot Dashboard")

# ── 1. Account equity ----------------------------------------------
col_equity, col_positions = st.columns([3, 2])

with col_equity:
    account = client.get_account()
    st.metric(label="Account Equity", value=f"${float(account.equity):,.2f}")

# ── 2. Open positions -----------------------------------------------
with col_positions:
    positions = client.get_positions()
    if positions:
        pos_rows = []
        for p in positions:
            pos_rows.append({
                "Symbol": p.symbol,
                "Qty": p.qty,
                "Avg Entry": f"${float(p.avg_entry_price):,.2f}",
                "Current": f"${client.get_latest_price(p.symbol):,.2f}",
                "Unrealized P/L": f"${p.unrealized_pl:.2f}",
                "%": f"{p.pl_percent:.2f}%",
            })
        pos_df = pd.DataFrame(pos_rows)
        st.table(pos_df)
    else:
        st.write("No open positions")

# ── 3. Recent trade history -------------------------------------------
trades = client.get_trades(limit=20)
if trades:
    trade_rows = []
    for t in trades:
        trade_rows.append({
            "Time": t.time,
            "ID": t.id,
            "Symbol": t.symbol,
            "Qty": t.qty,
            "Side": t.side,
            "Price": f"${float(t.price):,.2f}",
            "Status": t.status,
        })
    trades_df = pd.DataFrame(trade_rows)
    st.subheader("Recent Trades")
    st.dataframe(trades_df)
else:
    st.write("No trade history available")

# ── 4. Equity curve ----------------------------------------------------
st.subheader("Equity Curve")
hist = client.get_account_history(start=None, end=None)  # last ~30 days
# NEW:
if not hist.empty:
    hist_df = hist.copy()
    equity_series = hist_df["equity"].resample("1D").last()
    st.line_chart(equity_series)
else:
    st.write("No equity history to display")

# ── 5. Log panel --------------------------------------------------------
with st.expander("📚 Bot Logs"):
    # fetch all pending log messages
    log_text = ""
    while not log_queue.empty():
        log_text += log_queue.get() + "\n"
    st.text(log_text)
