import json
from pathlib import Path
from app.config import load_config


def test_load_config():
    config_data = [{"name": "test", "url": "https://test.substack.com"}]
    config_file = Path("config.json")
    with open(config_file, "w") as f:
        json.dump(config_data, f)

    config = load_config()
    assert config == config_data

    config_file.unlink()
