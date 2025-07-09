from dataclasses import dataclass
from typing import Any


@dataclass
class Post:
    title: str
    body_html: str | None
    description: str = ""
    podcast_url: str = ""
    post_date: str = ""


@dataclass
class ProcessedPosts:
    titles: list[str]
    bodies: list[str]
    descriptions: list[str]
    body_none: list[str]
    audio_files: list[str]
    post_dates: list[str]

    @classmethod
    def create_empty(cls) -> "ProcessedPosts":
        return cls([], [], [], [], [], [])


@dataclass
class PostForRendering:
    title: str
    body: str
    description: str
    audio: str
    date: str

    def to_dict(self) -> dict[str, str]:
        return {
            "title": self.title,
            "body": self.body,
            "description": self.description,
            "audio": self.audio,
            "date": self.date,
        }
