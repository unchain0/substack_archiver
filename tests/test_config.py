import pytest  # type: ignore
import json
from src.config import load_config


def test_load_config_success(tmp_path):
    """Tests that a valid config.json is loaded correctly."""
    config_data = {"substacks": [{"name": "test", "url": "https://test.substack.com"}]}
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_data))
    result = load_config(str(config_file))
    assert result == config_data["substacks"]


def test_load_config_file_not_found(tmp_path):
    """Tests that the function exits if the config file is not found."""
    with pytest.raises(SystemExit) as e:
        load_config(str(tmp_path / "nonexistent.json"))
    assert e.type is SystemExit
    assert e.value.code == 1


def test_load_config_invalid_json(tmp_path):
    """Tests that a JSONDecodeError is raised for a malformed config file."""
    config_file = tmp_path / "config.json"
    config_file.write_text("{\"substacks\": [}")  # Malformed JSON
    with pytest.raises(json.JSONDecodeError):
        load_config(str(config_file))


def test_load_config_missing_key(tmp_path):
    """Tests that an empty list is returned if 'substacks' key is missing."""
    config_data = {"other_key": "some_value"}
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_data))
    result = load_config(str(config_file))
    assert result == []
