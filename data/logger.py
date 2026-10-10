import logging
from datetime import datetime
from pathlib import Path
import config
def logger_init():
    LOG_DIR = Path("logs")
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    storterLogger = logging.getLogger("storter")
    storterLogger.setLevel(
        logging.DEBUG if config.DEBUG_MODE else logging.INFO
    )
    storterLogger.propagate = False

    # Remove any previously registered handlers
    for handler in storterLogger.handlers[:]:
        storterLogger.removeHandler(handler)
        handler.close()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))

    # File handler
    file_handler = logging.FileHandler(
        LOG_DIR / f"{now}.log",
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))

    storterLogger.addHandler(console_handler)
    storterLogger.addHandler(file_handler)

    # Diagnostic: should print 1
    storterLogger.debug(
        "Logger initialized | handlers=%d | pid=%d",
        len(storterLogger.handlers),
        __import__("os").getpid()
    )
    return storterLogger