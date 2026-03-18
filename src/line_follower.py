# line_follower.py
from machine import ADC, Pin

class QTRLineFollower:

    def __init__(self, out_pins, ctrl_pin=None, pitch_mm=8.0,
                 contrast_thresh=400, invert=True):

        if len(out_pins) != 8:
            raise ValueError("Must provide exactly 8 OUT pins")

        # Store parameters
        self.pitch_mm = pitch_mm
        self.contrast_thresh = contrast_thresh
        self.invert = invert

        # Setup ADC channels
        self.adcs = [ADC(Pin(p)) for p in out_pins]

        # Setup CTRL 
        self.ctrl = None
        if ctrl_pin is not None:
            self.ctrl = Pin(ctrl_pin, Pin.OUT)
            self.ctrl.value(1)

        # Precompute sensor positions
        self.positions = [(i - 3.5) * pitch_mm for i in range(8)]


    # Raw sensor
    def read_raw(self, samples=2):
        acc = [0] * 8
        for _ in range(samples):
            for i, adc in enumerate(self.adcs):
                acc[i] += adc.read_u16()
        return [v // samples for v in acc]

    # Compute centroid (no calibration)
    def read_line(self, samples=2):
        raw = self.read_raw(samples)

        mn = min(raw)
        mx = max(raw)
        rng = mx - mn

        if rng < self.contrast_thresh:
            return None, False, raw

        # Normalize
        norm = [(r - mn) / rng for r in raw]

        # 3-tap spatial smoothing across adjacent sensors.
        # Real line signal spans 2-4 sensors; specular spikes are single-sensor.
        # Smoothing kills isolated spikes while barely blurring the true line.
        smoothed = [0.0] * 8
        smoothed[0] = (norm[0] + norm[1]) / 2.0
        smoothed[7] = (norm[6] + norm[7]) / 2.0
        for i in range(1, 7):
            smoothed[i] = (norm[i-1] + norm[i] + norm[i+1]) / 3.0

        # Strength
        if self.invert:
            strength = smoothed
        else:
            strength = [1.0 - s for s in smoothed]

        total = sum(strength)
        if total < 1e-6:
            return None, False, raw

        pos_mm = sum(strength[i] * self.positions[i] for i in range(8)) / total

        return pos_mm, True, raw
