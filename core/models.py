from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class QrHeader:
    version: int
    total_chunks: int
    file_size: int
    file_name: str

@dataclass(frozen=True)
class QrChunk:
    index: int
    payload: str

@dataclass
class TransmissionProgress:
    current: int
    total: int
    percentage: float

@dataclass
class ReceptionStatus:
    has_header: bool
    collected_chunks: int
    total_chunks: Optional[int]
    percentage: float
    is_complete: bool