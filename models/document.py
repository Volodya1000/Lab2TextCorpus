from dataclasses import dataclass

@dataclass
class Document:
    id: int
    title: str
    author: str
    date: str
    genre: str
    text: str