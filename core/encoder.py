import os
import lzma
import shutil
import base45
import segno
from pathlib import Path
from typing import List, Tuple, Generator
from core.models import QrHeader, QrChunk

class QrEncoderEngine:
    def __init__(self, qr_version: int = 40, error_level: str = "m"):
        self.qr_version = qr_version
        self.error_level = error_level

    def read_raw_bytes_and_proccess_file_comperssion(self, file_path: str, compression_level: int = 9)->Tuple[bytes, bool]:
        with open(file_path, "rb") as f:
            raw_bytes=f.read()
        compressed=lzma.compress(raw_bytes, preset=compression_level)
        if len(compressed)/len(raw_bytes)<=0.8:
            return compressed, True
        return raw_bytes, False

    def to_base45_chunks(self, data: bytes) -> List[str]:
        encoded=base45.b45encode(data).decode("utf-8")
        capacity=1014 if self.qr_version == 25 else 3380
        return [encoded[i:i + capacity] for i in range(0, len(encoded), capacity)]

    def build_header_payload(self, file_name: str, file_size: int, total_chunks: int) -> str:
        return f"HDR|{self.qr_version}|{total_chunks}|{file_size}|{file_name}"

    def build_chunk_payload(self, chunk_idx: int, payload: str) -> str:
        return f"{chunk_idx:04d}{payload}"

    def generate_qr_svg_or_png_bytes(self, payload: str, scale: int = 4) -> bytes:
        qr=segno.make(payload, error=self.error_level, version=self.qr_version)
        import io
        buffer = io.BytesIO()
        qr.save(buffer, kind="png", scale=scale, border=2)
        return buffer.getvalue()