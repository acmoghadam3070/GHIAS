from dataclasses import dataclass
from typing import Optional


@dataclass
class Question:

    id: int

    code: str

    category: str

    department: str

    title: str

    answer_type: str

    risk: str

    weight: int

    required_photo: bool

    required_comment: bool

    recommendation: str

    standard: str

    active: bool = True