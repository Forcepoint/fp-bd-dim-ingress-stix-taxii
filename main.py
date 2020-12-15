from logger import LogConfig
from dim_endpoints import register_with_controller
from server import flask_thread, enq
from config import Config
import signal


class ProgramStop:
    stop = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        self.stop = True


if __name__ == "__main__":

    LogConfig()

    config = Config()
    config.load()
    configured = config.is_configured()

    register_with_controller(configured)
    flask_thread()

    if configured:
        enq()

    stop_me = ProgramStop()

    while not stop_me.stop:
        signal.pause()
