import dataclasses


@dataclasses.dataclass
class Point:
    index: int
    score: float
    meta: dict
