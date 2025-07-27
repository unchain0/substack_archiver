import json
import re
import sys
from pathlib import Path

from loguru import logger


def extract_name_from_url(url: str) -> str:
    """Extract the Substack name from the URL using regex.

    Examples:
    - https://plebs.substack.com -> plebs
    - https://artificialcorner.com/archive -> artificialcorner
    - https://www.cafecomsatoshi.com.br/archive -> cafecomsatoshi
    """
    # Pattern for substack.com domains
    substack_pattern = r"https?://(?:www\.)?([^.]+)\.substack\.com"

    # Pattern for custom domains
    custom_domain_pattern = r"https?://(?:www\.)?([^.]+)\.(?:com|com\.br|org|net)"

    # Try the substack pattern first
    match = re.match(substack_pattern, url)
    if match:
        return match.group(1)

    # Try the custom domain pattern
    match = re.match(custom_domain_pattern, url)
    if match:
        return match.group(1)

    # If no pattern matches, use the domain without extensions as fallback
    domain = url.split("//")[1].split("/")[0]
    domain = domain.replace("www.", "")
    name = domain.split(".")[0]

    logger.warning(f"Using fallback name extraction for URL: {url} -> {name}")
    return name


def load_config(config_path: str = "config.json") -> list[dict[str, str]]:
    config_file = Path(config_path)
    if not config_file.exists():
        logger.error(f"Config file not found at {config_path}")
        sys.exit(1)

    with open(config_file, "r") as f:
        config_data = json.load(f)

    # Handle both old and new format
    processed_config = []

    if not isinstance(config_data, list):
        logger.error(f"Config file {config_path} does not contain a list at its root.")
        sys.exit(1)

    for item in config_data:
        if isinstance(item, str):
            # New format: just URL string
            url = item
            name = extract_name_from_url(url)
            processed_config.append({"name": name, "url": url})
        elif isinstance(item, dict) and "url" in item:
            # Old format or partial format
            url = item["url"]
            # Use provided name or extract from URL
            name = item.get("name") or extract_name_from_url(url)

            config_item = {"name": name, "url": url}

            # Preserve any additional fields
            for key, value in item.items():
                if key != "name" and key != "url":
                    config_item[key] = value

            processed_config.append(config_item)
        else:
            logger.warning(f"Skipping invalid config entry: {item}")

    return processed_config
