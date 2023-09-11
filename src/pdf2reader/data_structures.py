from dataclasses import dataclass


@dataclass
class Box:
    x0: int
    y0: int
    x1: int
    y1: int
    color: str
    on_click: callable
