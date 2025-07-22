import re
from loguru import logger
from pathlib import Path


def serialize(value: str) -> str:
    if not isinstance(value, str):
        logger.error(f"Error serializing: {value} is not a string")

    value = re.sub(r"[^a-zA-Z0-9\s-]", "", value)
    return re.sub(r"[-\s]+", "-", value).strip("-")


class TruncatingFileSink:
    def __init__(self, file_path, max_size_bytes):
        self.file_path = Path(file_path)
        self.max_size_bytes = max_size_bytes
        self.file = open(self.file_path, "a", encoding="utf-8")

    def write(self, message):
        if self.file.tell() + len(message) > self.max_size_bytes:
            self.file.seek(0)
            self.file.truncate(0)

        self.file.write(message)
        self.file.flush()

    def __call__(self, message):
        self.write(message)

    def __del__(self):
        if hasattr(self, "file") and not self.file.closed:
            self.file.close()
