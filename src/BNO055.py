from pyb import Pin, I2C
import time

CALIB_FILE = "bno055_calib.txt"

class BNO055:

    def __init__(self, i2c_bus, rst_pin, mode="NDOF"):

        ## Registers ##
        self.REG_CHIP_ID    = 0x00
        self.REG_PAGE_ID    = 0x07
        self.REG_OPR_MODE   = 0x3D
        self.REG_PWR_MODE   = 0x3E
        self.REG_CALIB_STAT = 0x35
        self.REG_CALIB_DATA = 0x55

        self.REG_ACCEL_DATA = 0x08   # 6 bytes
        self.REG_GYRO_DATA  = 0x14   # 6 bytes
        self.REG_EULER_DATA = 0x1A   # 6 bytes
        self.REG_QUAT_DATA  = 0x20   # 8 bytes
        self.REG_LIA_DATA   = 0x28   # 6 bytes
        self.REG_GRAVITY    = 0x2E   # 6 bytes

        # ---- Constants ----
        self.CHIP_ID_OK  = 0xA0
        self.MODE_CONFIG = 0x00
        self.PWR_NORMAL  = 0x00

        # ---- Fusion modes ----
        self.FUSION_MODES = {
            "IMU":          0x08,
            "COMPASS":      0x09,
            "M4G":          0x0A,
            "NDOF_FMC_OFF": 0x0B,
            "NDOF":         0x0C,
        }

        self.rst_pin = rst_pin
        self.addr    = 0x28
        self.i2c     = I2C(i2c_bus, I2C.CONTROLLER, baudrate=100000)
        self.mode    = None
        self._mode   = mode   # desired fusion mode, used after calibration

        # Most recently read values (updated by update())
        self.heading  = 0.0   # degrees, 0-360
        self.yaw_rate = 0.0   # deg/s
        self._ready   = False

    # ------------------------------------------------------------------ #
    #  Low-level I2C
    # ------------------------------------------------------------------ #

    def write8(self, addr, reg, val):
        self.i2c.mem_write(bytes([val & 0xFF]), addr, reg)

    def read8(self, addr, reg):
        buf = bytearray(1)
        for attempt in range(5):
            try:
                self.i2c.mem_read(buf, addr, reg)
                return buf[0]
            except OSError:
                time.sleep_ms(100)
        raise OSError("read8 failed after retries at reg {}".format(hex(reg)))

    def readn(self, addr, reg, n):
        buf = bytearray(n)
        self.i2c.mem_read(buf, addr, reg)
        return buf

    def le_i16(self, lo, hi):
        v = lo | (hi << 8)
        return v - 65536 if v & 0x8000 else v

    # ------------------------------------------------------------------ #
    #  Device control
    # ------------------------------------------------------------------ #

    def reset(self):
        rst = Pin(self.rst_pin, Pin.OUT_PP)
        rst.high(); time.sleep_ms(10)
        rst.low();  time.sleep_ms(10)
        rst.high(); time.sleep_ms(1000)

    def set_mode(self, mode_name):
        """Switch operating mode. Must be a key in FUSION_MODES or 'CONFIG'."""
        if mode_name == "CONFIG":
            code = self.MODE_CONFIG
        elif mode_name in self.FUSION_MODES:
            code = self.FUSION_MODES[mode_name]
        else:
            raise ValueError("Unknown mode '{}'. Choose from: {}".format(
                mode_name, ["CONFIG"] + list(self.FUSION_MODES.keys())
            ))
        self.write8(self.addr, self.REG_OPR_MODE, self.MODE_CONFIG); time.sleep_ms(30)
        self.write8(self.addr, self.REG_OPR_MODE, code);             time.sleep_ms(30)
        self.mode = mode_name

    def setup(self, mode=None):
        """
        Initialise the BNO055 hardware, run the calibration routine
        (loading from file if available), and leave the sensor ready
        to read. Blocks until calibration is complete.
        Call once before the cotask scheduler starts.
        """
        if mode is not None:
            self._mode = mode

        # Hardware init
        self.reset()
        scan = self.i2c.scan()
        print("I2C scan:", [hex(x) for x in scan])
        if self.addr not in scan:
            raise RuntimeError("BNO055 not found. Check wiring and bus number.")

        chip = self.read8(self.addr, self.REG_CHIP_ID)
        print("CHIP_ID:", hex(chip))
        if chip != self.CHIP_ID_OK:
            raise RuntimeError("Unexpected CHIP_ID: {}".format(hex(chip)))

        self.write8(self.addr, self.REG_OPR_MODE, self.MODE_CONFIG); time.sleep_ms(30)
        self.write8(self.addr, self.REG_PAGE_ID,  0x00);              time.sleep_ms(10)
        self.write8(self.addr, self.REG_PWR_MODE, self.PWR_NORMAL);   time.sleep_ms(10)
        self.set_mode(self._mode)
        print("BNO055: hardware initialised in {} mode.".format(self._mode))

        # Calibration
        time.sleep(3)   # let gyro settle before checking status
        coeffs = self._load_calibration()

        if coeffs is not None:
            self.set_calibration_coefficients(coeffs)
            print("BNO055: calibration loaded from file, skipping routine.")
        else:
            print("BNO055: no calibration file found, starting calibration...")
            print("  Hold still for gyro, then move in figure-8s for mag,")
            print("  then tilt to several orientations for accel.")
            self._run_calibration()

        self._ready = True
        print("BNO055: ready.")

    def is_ready(self):
        """Returns True once setup() has completed successfully."""
        return self._ready

    # ------------------------------------------------------------------ #
    #  Called each tick by the observer task
    # ------------------------------------------------------------------ #

    def update(self):
        """Read fresh heading and yaw_rate. Call this each tick."""
        self.heading  = self.get_heading()
        self.yaw_rate = self.get_yaw_rate()

    # ------------------------------------------------------------------ #
    #  Calibration
    # ------------------------------------------------------------------ #

    def get_calibration_status(self):
        """
        Returns calibration status as a dict (sys, gyro, accel, mag).
        Each value is 0 (uncalibrated) to 3 (fully calibrated).
        """
        byte = self.read8(self.addr, self.REG_CALIB_STAT)
        return {
            "sys":   (byte >> 6) & 0x03,
            "gyro":  (byte >> 4) & 0x03,
            "accel": (byte >> 2) & 0x03,
            "mag":   (byte >> 0) & 0x03,
        }

    def is_fully_calibrated(self):
        """Returns True when gyro, accel and mag are all at level 3."""
        s = self.get_calibration_status()
        return s["gyro"] == 3 and s["accel"] == 3 and s["mag"] == 3

    def get_calibration_coefficients(self):
        """Read 22 bytes of calibration coefficients (must be in CONFIG mode)."""
        prev_mode = self.mode
        self.set_mode("CONFIG")
        time.sleep_ms(100)
        data = bytes(self.readn(self.addr, self.REG_CALIB_DATA, 22))
        self.set_mode(prev_mode)
        return data

    def set_calibration_coefficients(self, data):
        """Write 22 bytes of saved calibration coefficients back to the IMU."""
        if len(data) != 22:
            raise ValueError("Calibration data must be 22 bytes, got {}".format(len(data)))
        prev_mode = self.mode
        self.set_mode("CONFIG")
        time.sleep_ms(30)
        for i, byte in enumerate(data):
            self.write8(self.addr, self.REG_CALIB_DATA + i, byte)
            time.sleep_ms(5)
        self.set_mode(prev_mode)
        print("BNO055: calibration coefficients written.")

    def _run_calibration(self):
        """Block until relevant subsystems reach status 3, then save to file."""
        # In IMU mode the magnetometer is disabled — don't wait for it
        imu_mode = self._mode in ("IMU",)

        while True:
            s = self.get_calibration_status()
            print("  gyro={} accel={} mag={} (sys={})".format(
                s["gyro"], s["accel"], s["mag"], s["sys"]))

            if imu_mode:
                done = s["gyro"] == 3 and s["accel"] == 3
            else:
                done = s["gyro"] == 3 and s["accel"] == 3 and s["mag"] == 3

            if done:
                time.sleep(0.5)
                s2 = self.get_calibration_status()
                if imu_mode:
                    confirmed = s2["gyro"] == 3 and s2["accel"] == 3
                else:
                    confirmed = s2["gyro"] == 3 and s2["accel"] == 3 and s2["mag"] == 3

                if confirmed:
                    print("BNO055: calibration confirmed.")
                    self._save_calibration()
                    return

            time.sleep(1)

    def _save_calibration(self):
        """Read coefficients in CONFIG mode and write to file."""
        try:
            self.set_mode("CONFIG")
            time.sleep_ms(100)
            coeffs = bytes(self.readn(self.addr, self.REG_CALIB_DATA, 22))
            self.set_mode(self._mode)
            with open(CALIB_FILE, "w") as f:
                f.write(",".join(str(b) for b in coeffs))
            print("BNO055: calibration saved to", CALIB_FILE)
        except Exception as e:
            print("BNO055: failed to save calibration:", e)

    def _load_calibration(self):
        """Return 22-byte coefficients from file, or None if not found/invalid."""
        try:
            with open(CALIB_FILE, "r") as f:
                data = f.read().strip()
            coeffs = bytes([int(x) for x in data.split(",")])
            if len(coeffs) == 22:
                return coeffs
            print("BNO055: calibration file invalid, ignoring.")
            return None
        except:
            return None

    # ------------------------------------------------------------------ #
    #  Euler angles
    # ------------------------------------------------------------------ #

    def get_euler(self):
        """Returns (heading, roll, pitch) in degrees."""
        e = self.readn(self.addr, self.REG_EULER_DATA, 6)
        return (
            self.le_i16(e[0], e[1]) / 16.0,
            self.le_i16(e[2], e[3]) / 16.0,
            self.le_i16(e[4], e[5]) / 16.0,
        )

    def get_heading(self):
        """Returns heading (yaw) in degrees (0-360)."""
        e = self.readn(self.addr, self.REG_EULER_DATA, 2)
        return self.le_i16(e[0], e[1]) / 16.0

    def get_pitch(self):
        """Returns pitch in degrees (-180 to +180)."""
        e = self.readn(self.addr, self.REG_EULER_DATA, 6)
        return self.le_i16(e[4], e[5]) / 16.0

    def get_roll(self):
        """Returns roll in degrees (-180 to +180)."""
        e = self.readn(self.addr, self.REG_EULER_DATA, 6)
        return self.le_i16(e[2], e[3]) / 16.0

    # ------------------------------------------------------------------ #
    #  Angular velocity
    # ------------------------------------------------------------------ #

    def get_gyro(self):
        """Returns (gx, gy, gz) angular velocities in deg/s."""
        g = self.readn(self.addr, self.REG_GYRO_DATA, 6)
        return (
            self.le_i16(g[0], g[1]) / 16.0,
            self.le_i16(g[2], g[3]) / 16.0,
            self.le_i16(g[4], g[5]) / 16.0,
        )

    def get_yaw_rate(self):
        """Returns yaw rate (Z axis) in deg/s."""
        g = self.readn(self.addr, self.REG_GYRO_DATA, 6)
        return self.le_i16(g[4], g[5]) / 16.0

    def get_pitch_rate(self):
        """Returns pitch rate in deg/s."""
        g = self.readn(self.addr, self.REG_GYRO_DATA, 6)
        return self.le_i16(g[2], g[3]) / 16.0

    def get_roll_rate(self):
        """Returns roll rate in deg/s."""
        g = self.readn(self.addr, self.REG_GYRO_DATA, 6)
        return self.le_i16(g[0], g[1]) / 16.0

    # ------------------------------------------------------------------ #
    #  Other sensors
    # ------------------------------------------------------------------ #

    def get_accel(self):
        """Returns (ax, ay, az) in m/s²."""
        b = self.readn(self.addr, self.REG_ACCEL_DATA, 6)
        return (
            self.le_i16(b[0], b[1]) / 100.0,
            self.le_i16(b[2], b[3]) / 100.0,
            self.le_i16(b[4], b[5]) / 100.0,
        )

    def get_quaternion(self):
        """Returns (w, x, y, z) quaternion."""
        q = self.readn(self.addr, self.REG_QUAT_DATA, 8)
        scale = 1.0 / (1 << 14)
        return (
            self.le_i16(q[0], q[1]) * scale,
            self.le_i16(q[2], q[3]) * scale,
            self.le_i16(q[4], q[5]) * scale,
            self.le_i16(q[6], q[7]) * scale,
        )

    def get_linear_accel(self):
        """Returns linear acceleration (gravity removed) in m/s²."""
        b = self.readn(self.addr, self.REG_LIA_DATA, 6)
        return (
            self.le_i16(b[0], b[1]) / 100.0,
            self.le_i16(b[2], b[3]) / 100.0,
            self.le_i16(b[4], b[5]) / 100.0,
        )

    def get_gravity(self):
        """Returns gravity vector in m/s²."""
        b = self.readn(self.addr, self.REG_GRAVITY, 6)
        return (
            self.le_i16(b[0], b[1]) / 100.0,
            self.le_i16(b[2], b[3]) / 100.0,
            self.le_i16(b[4], b[5]) / 100.0,
        )

    # ------------------------------------------------------------------ #
    #  Run loop (for standalone testing only)
    # ------------------------------------------------------------------ #

    def run(self):
        """Simple streaming loop for standalone testing. Ctrl+C to stop."""
        print("Streaming... (Ctrl+C to stop)")
        while True:
            self.update()
            h, r, p    = self.get_euler()
            gx, gy, gz = self.get_gyro()
            print("Heading={:+.1f} Roll={:+.1f} Pitch={:+.1f} | "
                  "YawRate={:+.1f} PitchRate={:+.1f} RollRate={:+.1f}".format(
                      h, r, p, gz, gy, gx))
            time.sleep(0.1)