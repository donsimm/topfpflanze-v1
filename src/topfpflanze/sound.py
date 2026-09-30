"""Töne: Giesssound und Gong zum Ende des Fokus-Timers, mit Gesamtlautstärke 0–100.

Die Klänge werden selbst erzeugt (keine fremden Audiodateien, keine Lizenzfragen) und einmalig als WAV im
Datenordner abgelegt. Abgespielt wird mit Qt Multimedia. Ist kein Audio verfügbar (fehlende Bibliothek,
kein Ausgabegerät), bleibt das Spiel einfach stumm.
"""

import math
import random
import struct
import time
import wave

from . import config

RATE = 22050
VERSION = 1                      # erhöhen, wenn sich die Klänge ändern: die Dateien werden neu erzeugt
DEFAULT_VOLUME = 0              # Standard: stumm; der Regler in den Einstellungen schaltet den Ton ein
GAINS = {"giessen": 0.55, "gong": 0.9}          # Grundlautstärke je Klang (vor dem Gesamtregler)
MIN_INTERVAL = {"giessen": 0.16, "gong": 1.0}   # Sekunden: schnelles Klicken soll nicht rattern


# ---------------------------------------------------------------- Klangerzeugung

def _lowpass(samples, alpha):
    out, y = [], 0.0
    for x in samples:
        y += alpha * (x - y)
        out.append(y)
    return out


def _normalize(samples, peak=0.9, fade=0.02):
    m = max(1e-9, max(abs(s) for s in samples))
    n = len(samples)
    k = peak / m
    fade_n = max(1, int(fade * RATE))
    out = [s * k for s in samples]
    for i in range(fade_n):                  # sanftes Ausblenden: kein Knacken am Ende
        out[n - 1 - i] *= i / fade_n
    return out


def synth_water(seed=11):
    """Giesssound: weiches Wasserrauschen mit ein paar aufsteigenden Blubbern (ca. 0.55 s)."""
    rng = random.Random(seed)
    n = int(0.55 * RATE)
    noise = _lowpass(_lowpass([rng.uniform(-1, 1) for _ in range(n)], 0.32), 0.5)
    out = []
    for i in range(n):
        t = i / RATE
        env = (1 - math.exp(-t / 0.02)) * math.exp(-t / 0.21)
        wobble = 0.65 + 0.35 * math.sin(2 * math.pi * 27 * t + 3 * noise[i])
        out.append(noise[i] * 3.2 * env * wobble)
    for _ in range(8):                       # Blubber: kurze, aufsteigende Sinustöne
        start = rng.uniform(0.03, 0.42)
        f0 = rng.uniform(520, 1150)
        length = rng.uniform(0.04, 0.08)
        amp = rng.uniform(0.18, 0.32)
        i0 = int(start * RATE)
        for j in range(int(length * RATE)):
            if i0 + j >= n:
                break
            t = j / RATE
            f = f0 * (1 + 0.6 * t / length)
            out[i0 + j] += amp * math.sin(2 * math.pi * f * t) * math.exp(-t / (length * 0.45))
    return _normalize(out, 0.85)


def synth_gong():
    """Gong: mehrere unharmonische Teiltöne, die unterschiedlich schnell abklingen, plus ein weicher Anschlag (ca. 3.6 s)."""
    rng = random.Random(5)
    f0 = 174.6
    partials = ((1.0, 1.00, 1.9), (1.47, 0.75, 1.6), (2.0, 0.55, 1.3), (2.63, 0.45, 1.0), (3.42, 0.32, 0.8),
                (4.29, 0.22, 0.6), (5.61, 0.14, 0.45))
    n = int(3.6 * RATE)
    out = [0.0] * n
    for ratio, amp, tau in partials:
        for detune, share in ((0.0, 0.6), (0.8, 0.4)):   # zwei leicht verstimmte Töne: das Schwebende eines Gongs
            w = 2 * math.pi * (f0 * ratio + detune * ratio)
            a = amp * share
            for i in range(n):
                t = i / RATE
                out[i] += a * math.sin(w * t) * math.exp(-t / tau)
    strike = _lowpass([rng.uniform(-1, 1) for _ in range(int(0.06 * RATE))], 0.25)
    for i, s in enumerate(strike):
        out[i] += 0.45 * s * math.exp(-(i / RATE) / 0.012)
    for i in range(int(0.004 * RATE)):       # kurzer Anstieg statt hartem Einsatz
        out[i] *= i / (0.004 * RATE)
    return _normalize(out, 0.9, fade=0.15)


SYNTHS = {"giessen": synth_water, "gong": synth_gong}


_PCM = {}   # einmal pro Programmlauf erzeugt (die Synthese dauert einen Moment)


def pcm(name):
    """16-Bit-Mono-Daten des Klangs (little endian)."""
    if name not in _PCM:
        samples = SYNTHS[name]()
        _PCM[name] = struct.pack(f"<{len(samples)}h",
                                 *(int(max(-1.0, min(1.0, s)) * 32767) for s in samples))
    return _PCM[name]


def write_wav(path, name):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm(name))


def sound_dir():
    return config.STATE_DIR / "sounds"


def ensure_files():
    """Erzeugt die Klangdateien, falls sie fehlen; gibt {Name: Pfad} zurück."""
    d = sound_dir()
    d.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name in SYNTHS:
        path = d / f"{name}-v{VERSION}.wav"
        if not path.exists():
            write_wav(path, name)
        paths[name] = path
    return paths


# ---------------------------------------------------------------- Wiedergabe

def effective_volume(volume, name):
    """Gesamtlautstärke 0–100 → Qt-Lautstärke 0..1 (quadratisch: fühlt sich gleichmässiger an)."""
    v = max(0, min(100, volume)) / 100.0
    return (v ** 2) * GAINS.get(name, 1.0)


class SoundPlayer:
    """Spielt die Klänge ab. volume: Gesamtlautstärke 0–100 (0 = stumm)."""

    def __init__(self, volume=DEFAULT_VOLUME):
        self.volume = max(0, min(100, int(volume)))
        self.effects = {}
        self.last = {}
        self.available = False
        self.error = ""
        try:
            from PyQt6.QtCore import QUrl
            from PyQt6.QtMultimedia import QSoundEffect
            paths = ensure_files()
            for name, path in paths.items():
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(str(path)))
                self.effects[name] = effect
            self.available = True
            self.set_volume(self.volume)
        except Exception as e:  # fehlende Bibliothek, kein Ausgabegerät, Datei nicht schreibbar ...
            self.error = f"{type(e).__name__}: {e}"

    def set_volume(self, volume):
        self.volume = max(0, min(100, int(volume)))
        for name, effect in self.effects.items():
            effect.setVolume(effective_volume(self.volume, name))

    def play(self, name):
        """Spielt einen Klang ab (ohne Wirkung bei Lautstärke 0, ohne Audio oder bei zu schnellem Wiederholen)."""
        effect = self.effects.get(name)
        if effect is None or self.volume <= 0:
            return False
        now = time.monotonic()
        if now - self.last.get(name, -1e9) < MIN_INTERVAL.get(name, 0.0):
            return False
        self.last[name] = now
        effect.play()
        return True
