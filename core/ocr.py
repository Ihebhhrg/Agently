from utils.debuglog import dlog


class OCR:
    """Optical character recognition (RapidOCR / ONNX).

    onnxruntime is heavy (~80 MB), so the engine is imported and created
    lazily the first time text extraction is requested.
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.engine = None
        self._tried = False

    def _ensure(self):
        if self.engine is not None:
            return True
        if self._tried:
            return False
        self._tried = True
        try:
            dlog("OCR: loading engine on demand")
            from rapidocr_onnxruntime import RapidOCR
            self.engine = RapidOCR()
            dlog("OCR: engine ready")
            return True
        except Exception as e:
            dlog(f"OCR init failed: {e}")
            self.engine = None
            return False

    def extract_text(self, img_path) -> str:
        try:
            if not self._ensure():
                return ""
            res, _ = self.engine(img_path)
            texts = []
            if res:
                for item in res:
                    if item and len(item) > 1:
                        texts.append(str(item[1]).strip())
            return "\n".join([t for t in texts if t])
        except Exception as e:
            dlog(f"OCR error: {e}")
            return ""
