# bot.py
"""
Wrapper that turns your existing bot into a
*start/stop*‑controllable object suitable for Streamlit.

Usage
-----
    from bot import BotWrapper
    bot = BotWrapper(client, logger)
    bot.start()          # run in the current thread
    # …later…
    bot.running = False  # gracefully stop
"""

import time
import logging
import threading
from main import run_bot

# --- Import the *original* bot logic ----------------------------
# (Assume the original logic is defined in `main.py` as run_bot()
#  or similar.  Adjust the import path if the original function
#  lives elsewhere.)
try:
    from main import run_bot  # the existing entry point
except Exception as exc:
    raise ImportError("Could not import the original run_bot()") from exc

# ----------------------------------------------------------------
class BotWrapper:
    """
    Minimal interface required by the Streamlit dashboard.
    """
    def __init__(self, client, logger=None):
        self.client = client           # the Alpaca REST client used by the bot
        self.logger = logger or logging.getLogger("trading_bot")
        self.running = False
        self._thread = None

    # ----------------------------------------------------------------
    def start(self):
        """
        Kick the bot loop in a daemon thread so the UI stays responsive.
        """
        if self.running:
            self.logger.warning("Bot already running")
            return

        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.logger.info("Bot started (wrapper)")

    # ----------------------------------------------------------------
    def _run_loop(self):
        """
        The actual loop that repeatedly calls the original logic.
        The original bot is expected to expose a callable like `run_bot()`
        that performs a single “step” – e.g. fetch a bar, decide, execute.
        If your bot is a continuous loop you can simply call it here;
        it will be stopped gracefully when self.running becomes False.
        """
        while self.running:
            try:
                # ----------------------------------------------------------------
                # Call the *real* bot logic
                # ----------------------------------------------------------------
                run_bot(client=self.client, logger=self.logger)
                # ----------------------------------------------------------------
                # If the original bot already contains its own sleep / waiting,
                # you don't need an extra sleep here.
                # If it is an instant “step” you might want to sleep a bit:
                # time.sleep(0.5)
                # ----------------------------------------------------------------
            except Exception as exc:
                self.logger.exception("Unexpected error in bot loop: %s", exc)
                # Sleep a short while to avoid a tight crash‑loop
                time.sleep(5)

    # ----------------------------------------------------------------
    def stop(self):
        """
        Signal the running loop to exit.  The thread will join automatically.
        """
        if not self.running:
            self.logger.warning("Bot not running")
            return

        self.running = False
        if self._thread:
            self._thread.join()
        self.logger.info("Bot stopped")

    # ----------------------------------------------------------------
    def is_running(self):
        return self.running
