import dataclasses
from dataclasses import dataclass, field


@dataclass
class Post:
    title: str | None = None
    body_html: str | None = None
    description: str | None = None
    podcast_url: str | None = None
    audio_url: str | None = None
    post_date: str | None = None
    audience: str | None = None
    extra_fields: dict = field(default_factory=dict)

    def __post_init__(self):
        # Move any unexpected keyword arguments into extra_fields
        for key in list(self.__dict__.keys()):
            if key not in self.__annotations__ and key != "extra_fields":
                self.extra_fields[key] = self.__dict__.pop(key)

    @classmethod
    def from_dict(cls, data: dict):
        # Filter out keys not in the dataclass fields before passing to constructor
        valid_keys = {f.name for f in dataclasses.fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        extra_fields = {k: v for k, v in data.items() if k not in valid_keys}
        instance = cls(**filtered_data)
        instance.extra_fields = extra_fields
        return instance


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
