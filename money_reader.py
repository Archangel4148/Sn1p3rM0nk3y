import threading
import time

from vision import ocr_number_from_image


class MoneyReader:
    def __init__(self, window_manager, region=(0.192, 0.015, 0.156, 0.049), interval=0.3):
        self.window_manager = window_manager
        self.region = region
        self.interval = interval
        self._last_read: float = 0
        self._lock = threading.Lock()
        self._stop = False
        self._money = 0
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def _loop(self):
        while not self._stop:
            try:
                capture = self.window_manager.capture_window(region=self.region)
                value = ocr_number_from_image(capture)
                if value is not None:
                    with self._lock:
                        self._money = value
                        self._last_read = time.time()
            except Exception as e:
                print(f"[MoneyReader] OCR error: {e}")
            time.sleep(self.interval)

    def refresh_now(self):
        capture = self.window_manager.capture_window(region=self.region)
        value = ocr_number_from_image(capture)
        if value is not None:
            with self._lock:
                self._money = value
        return self._money

    def get_money(self) -> tuple[int, float]:
        """Thread-safe access to latest known money (also gives last read time)"""
        with self._lock:
            return self._money, self._last_read

    def start(self):
        self._stop = False
        self._thread.start()

    def stop(self):
        self._stop = True
        self._thread.join()
