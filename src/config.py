import os
import json
import sys
from loguru import logger

def load_config(config_path: str = "config.json") -> list[dict[str, str]]:
    if not os.path.exists(config_path):
        logger.error(f"Config file not found at {config_path}")
        sys.exit(1)
    with open(config_path, "r") as f:
        config = json.load(f)
    return config.get("substacks", [])
