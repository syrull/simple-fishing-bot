import pyautogui
import time
import random
import sys
import threading

if sys.platform == "win32":
    import ctypes
    import ctypes.util

    _user32 = ctypes.windll.user32

    class _CURSORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_uint),
            ("flags", ctypes.c_uint),
            ("hCursor", ctypes.c_void_p),
            ("ptScreenPos", ctypes.c_long * 2),
        ]

    def get_cursor_info():
        ci = _CURSORINFO()
        ci.cbSize = ctypes.sizeof(_CURSORINFO)
        _user32.GetCursorInfo(ctypes.byref(ci))
        return ci.hCursor

else:
    import ctypes
    import ctypes.util
    import hashlib

    class _XFixesCursorImage(ctypes.Structure):
        _fields_ = [
            ("x", ctypes.c_short),
            ("y", ctypes.c_short),
            ("width", ctypes.c_ushort),
            ("height", ctypes.c_ushort),
            ("xhot", ctypes.c_ushort),
            ("yhot", ctypes.c_ushort),
            ("cursor_serial", ctypes.c_ulong),
            ("pixels", ctypes.POINTER(ctypes.c_ulong)),
            ("atom", ctypes.c_ulong),
            ("name", ctypes.c_char_p),
        ]

    _libX11 = ctypes.CDLL(ctypes.util.find_library("X11"))
    _libX11.XOpenDisplay.restype = ctypes.c_void_p
    _libX11.XFree.argtypes = [ctypes.c_void_p]

    _libXfixes = ctypes.CDLL(ctypes.util.find_library("Xfixes"))
    _libXfixes.XFixesGetCursorImage.restype = ctypes.POINTER(_XFixesCursorImage)

    _dpy = _libX11.XOpenDisplay(None)

    def get_cursor_info():
        cursor_ptr = _libXfixes.XFixesGetCursorImage(_dpy)
        c = cursor_ptr.contents
        n = c.width * c.height
        pixel_array = (ctypes.c_ulong * n).from_address(
            ctypes.addressof(c.pixels.contents)
        )
        digest = hashlib.md5(bytes(pixel_array)).digest()
        _libX11.XFree(cursor_ptr)
        return digest


class FishingBot:
    def __init__(
        self,
        bait_image="./bait.png",
        fishing_button="b",
        mouse_offset_px=35,
        edge_reset=(10, 10),
        start_delay=2,
        confidence=0.7,
        on_status=None,
        on_fish_caught=None,
    ):
        self.bait_image = bait_image
        self.fishing_button = fishing_button
        self.mouse_offset_px = mouse_offset_px
        self.edge_reset = edge_reset
        self.start_delay = start_delay
        self.confidence = confidence
        self.on_status = on_status or (lambda msg: None)
        self.on_fish_caught = on_fish_caught or (lambda count: None)

        self._stop_event = threading.Event()
        self._thread = None
        self._fish_count = 0

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running:
            return
        self._stop_event.clear()
        self._fish_count = 0
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _stopped(self):
        return self._stop_event.is_set()

    def _sleep(self, seconds):
        """Interruptible sleep. Returns True if interrupted."""
        return self._stop_event.wait(timeout=seconds)

    def _find_on_screen(self):
        while not self._stopped():
            try:
                loc = pyautogui.locateOnScreen(
                    self.bait_image, confidence=self.confidence
                )
                cp_loc = pyautogui.center(loc)
                return cp_loc
            except Exception:
                if self._sleep(0.25):
                    return None
        return None

    def _run(self):
        self.on_status("Starting in {} seconds...".format(self.start_delay))
        if self._sleep(self.start_delay):
            self.on_status("Stopped.")
            return

        self.on_status("Bot running.")

        while not self._stopped():
            delay = 0.25 + random.uniform(0, 1.5)
            if self._sleep(delay):
                break

            # 20% chance to press "space"
            chance = random.randint(0, 100)
            if chance <= 20:
                pyautogui.press("space")
                if self._sleep(2):
                    break

            pyautogui.write(self.fishing_button)
            self.on_status("Cast line, searching for bait...")

            # Reset mouse position
            pyautogui.moveTo(*self.edge_reset)

            bait = self._find_on_screen()
            if bait is None:
                break

            pyautogui.moveTo(
                bait.x,
                bait.y + self.mouse_offset_px + random.randint(1, 4),
            )
            self.on_status("Watching bobber...")

            cursor_info = get_cursor_info()
            catch_start = time.time()

            caught = False
            while not self._stopped():
                curr_cursor_info = get_cursor_info()
                if curr_cursor_info != cursor_info:
                    if self._sleep(0.25 + random.uniform(0, 0.15)):
                        break
                    pyautogui.click(bait.x, bait.y)
                    self._fish_count += 1
                    self.on_status("Fish caught! (#{})".format(self._fish_count))
                    self.on_fish_caught(self._fish_count)
                    caught = True
                    break

                if time.time() - catch_start > 22:
                    self.on_status("Bobber timed out, recasting...")
                    break

                # Avoid tight CPU-burning loop
                if self._sleep(0.05):
                    break

        self.on_status("Stopped.")


if __name__ == "__main__":
    bot = FishingBot(
        bait_image="./bait.png",
        fishing_button="b",
        mouse_offset_px=35,
        edge_reset=(10, 10),
        start_delay=2,
        confidence=0.7,
        on_status=lambda msg: print("[Bot]", msg),
        on_fish_caught=lambda count: print("[Fish]", count),
    )
    bot.start()
    try:
        while bot.running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        bot.stop()
