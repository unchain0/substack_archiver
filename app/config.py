import json
import sys
from pathlib import Path
from loguru import logger


def load_config(config_path: str = "config.json") -> list[dict[str, str]]:
    config_file = Path(config_path)
    if not config_file.exists():
        logger.error(f"Config file not found at {config_path}")
        sys.exit(1)
    with open(config_file, "r") as f:
        config = json.load(f)
    if not isinstance(config, list):
        logger.error(f"Config file {config_path} does not contain a list at its root.")
        sys.exit(1)
    return config
