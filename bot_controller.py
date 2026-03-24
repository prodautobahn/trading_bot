# bot_controller.py
import threading

class BotController:
    """
    Wraps a bot instance so it can be started/stopped
    from the Streamlit UI in a background thread.
    """
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.thread = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return False  # already running
        self.thread = threading.Thread(target=self.bot.start, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        if not self.bot.running:
            return False
        self.bot.running = False
        if self.thread:
            self.thread.join()
        return True

    @property
    def is_running(self):
        return self.bot.running
