from dataclasses import dataclass


@dataclass
class Book:
    title: str
    author: str
    intro: str
    toc: str
    url: str
