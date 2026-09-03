import base45
from typing import Dict, Optional, Set
from core.models import QrHeader, ReceptionStatus, QrChunk


class QrDecoderEngine:
    def __init__(self):
        self.this_qr_valid = None
        self.reset()

    def reset(self):
        self.header: Optional[QrHeader] = None
        self.chunks: Dict[int, str] = {}
        self.received_indices: Set[int] = set()
        self.this_qr_valid: bool = None

    def parse_payload(self, text: str,)-> ReceptionStatus:
        self.this_qr_valid = True
        parts=text.split("|")
        if len(parts)==5 and parts[0]=="HDR":
            self.header = QrHeader(
                version=int(parts[1]),
                total_chunks=int(parts[2]),
                file_size=int(parts[3]),
                file_name=parts[4]
            )
        elif len(text)>4 and text[:4].isdigit():
            idx=int(text[:4])
            payload = text[4:]
            if idx not in self.chunks:
                self.chunks[idx]=payload
                self.received_indices.add(idx)
        else:
            self.this_qr_valid=False
        return self.get_status()

    def get_status(self) -> ReceptionStatus:
        if not self.header:
            return ReceptionStatus(
                has_header=False,
                collected_chunks=len(self.chunks),
                total_chunks=None,
                percentage=0.0,
                is_complete=False,
                is_this_qr_valid=self.this_qr_valid
            )
        total=self.header.total_chunks
        collected=len(self.chunks)
        pct=min(100.0, (collected / total) * 100.0) if total > 0 else 0.0

        return ReceptionStatus(
            has_header=True,
            collected_chunks=collected,
            total_chunks=total,
            percentage=pct,
            is_complete=(collected == total),
            is_this_qr_valid = self.this_qr_valid
        )

    def assemble_to_bytes(self):
        status = self.get_status()
        if not status.has_header or not status.is_complete:
            raise ValueError("Cannot assemble: Missing packets or header.")

        full_b45 = "".join(self.chunks[i] for i in range(self.header.total_chunks))
        raw_bytes = base45.b45decode(full_b45)
        return self.header.file_name, raw_bytes


