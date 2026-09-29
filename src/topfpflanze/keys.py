"""Tastaturzählung (nur die Anzahl der Tastendrücke)."""

import sys
import threading



# ---------------------------------------------------------------- Tastatur

class KeyCounter:
    """Zählt Tastendrücke systemweit in einem Hintergrund-Thread (nur Anzahl)."""

    def __init__(self):
        self._n = 0
        self._lock = threading.Lock()

    def add(self, n=1):
        with self._lock:
            self._n += n

    def take(self):
        with self._lock:
            n, self._n = self._n, 0
        return n

    def start(self):
        if sys.platform.startswith("linux") and self._start_evdev():
            return "evdev"
        return self._start_pynput()

    def _start_evdev(self):
        try:
            import evdev
            from evdev import ecodes
        except ImportError:
            return None
        devices = []
        for path in evdev.list_devices():  # listet nur lesbare Geräte
            try:
                dev = evdev.InputDevice(path)
            except OSError:
                continue
            keys = dev.capabilities().get(ecodes.EV_KEY, [])
            if ecodes.KEY_A in keys and ecodes.KEY_SPACE in keys:
                devices.append(dev)
            else:
                dev.close()
        if not devices:
            return None

        def run():
            import selectors
            sel = selectors.DefaultSelector()
            for d in devices:
                sel.register(d, selectors.EVENT_READ)
            while sel.get_map():
                for key, _ in sel.select():
                    try:
                        for ev in key.fileobj.read():
                            if ev.type == ecodes.EV_KEY and ev.value == 1:
                                self.add()
                    except BlockingIOError:
                        continue
                    except OSError:
                        sel.unregister(key.fileobj)

        threading.Thread(target=run, daemon=True).start()
        return "evdev"

    def _start_pynput(self):
        try:
            from pynput import keyboard
            listener = keyboard.Listener(on_press=lambda _k: self.add())
            listener.daemon = True
            listener.start()
        except Exception:
            return None
        return "pynput"
