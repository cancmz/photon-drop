import io
import os
import lzma
import shutil
import base45
import segno
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Tuple, Generator
from core.models import QrHeader, QrChunk

# Bu sayının altındaki işlerde process havuzu açmak (özellikle Windows'ta
# "spawn" maliyeti) kazandırdığından fazlasına mal olur; seri üretilir.
_PARALLEL_MIN_ITEMS = 16


def _encode_task(args: Tuple[int, str, int, Optional[int], str]) -> bytes:
    """Process havuzu worker'ı. Modül seviyesinde olmak zorunda (pickle)."""
    qr_version, error_level, mask, scale, payload = args
    return QrEncoderEngine(qr_version, error_level, mask).generate_qr_svg_or_png_bytes(payload, scale)


class QrEncoderEngine:
    def __init__(self, qr_version: int = 40, error_level: str = "m", mask: Optional[int] = 4):
        self.qr_version = qr_version
        self.error_level = error_level
        # mask=None: segno 8 maskeyi tek tek puanlar (version 40'ta ~6x yavaş).
        # Sabit maske her okuyucu tarafından geçerli bir QR üretir.
        self.mask = mask

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
        qr = segno.make(payload, error=self.error_level, version=self.qr_version, mask=self.mask)
        buffer = io.BytesIO()
        # compresslevel=1: ekranda gösterilen geçici kare için boyut değil hız önemli
        qr.save(buffer, kind="png", scale=scale, border=2, compresslevel=1)
        return buffer.getvalue()

    def iter_png_bytes(self, payloads: Iterable[str], scale: int = 4,
                       max_workers: Optional[int] = None) -> Iterator[bytes]:
        """payloads sırasıyla PNG byte'larını üretir (sıra HER ZAMAN korunur).

        Çok çekirdek: işler process havuzuna dağıtılır, sonuçlar girdi sırasıyla
        döner. Generator erken kapatılırsa (cancel) bekleyen işler iptal edilir.
        """
        payloads = list(payloads)
        if max_workers is None:
            max_workers = max(1, (os.cpu_count() or 2) - 1)  # 1 çekirdek UI'a kalsın

        if max_workers <= 1 or len(payloads) < _PARALLEL_MIN_ITEMS:
            for payload in payloads:
                yield self.generate_qr_svg_or_png_bytes(payload, scale)
            return

        args = [(self.qr_version, self.error_level, self.mask, scale, p) for p in payloads]
        pool = ProcessPoolExecutor(max_workers=max_workers)
        try:
            # map girdi sırasını korur; chunksize IPC maliyetini düşürür
            yield from pool.map(_encode_task, args, chunksize=4)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
