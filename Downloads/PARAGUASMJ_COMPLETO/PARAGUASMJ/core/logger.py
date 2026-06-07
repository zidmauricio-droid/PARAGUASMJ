"""core/logger.py — Logger institucional ASUACAP."""
import logging, os, sys
from logging.handlers import RotatingFileHandler
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

def configurar_logger(nombre: str = "asuacap") -> logging.Logger:
    logger = logging.getLogger(nombre)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    log_file = os.path.join(Config.LOG_FOLDER, "paraguasmj.log")
    fh = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger

logger = configurar_logger()
