from dataclasses import dataclass


@dataclass
class Box:
    x0: float
    y0: float
    x1: float
    y1: float
    color: str
    on_click: callable
