from machine import UART
import sys

class BTBridge:
    def __init__(self, uart_no=4, baud=9600, print_incoming=True):
        self.uart = UART(uart_no, baud)
        self.print_incoming = print_incoming

        self._bt_buf = bytearray()
        self._rx_lines = []  # list of bytes lines (no CR/LF)

    def send_text(self, s):
        """Send text (str or bytes) out over Bluetooth."""
        if isinstance(s, str):
            b = s.encode()
        else:
            b = s
        self.uart.write(b)

    def send_line(self, line):
        """Send a line (str or bytes) with CRLF."""
        if isinstance(line, str):
            b = line.encode()
        else:
            b = line
        if not b.endswith(b"\r\n"):
            b += b"\r\n"
        self.uart.write(b)

    def _print(self, *args, end="\r\n"):
    # Like print(): joins args with spaces
        s = " ".join(str(a) for a in args) + end
        self.send_text(s)

    def poll_bt(self):
        """Non-blocking: read all available BT bytes, split into lines."""
        while self.uart.any():
            b = self.uart.read(1)
            if not b:
                break

            # ignore BEL/noise if present
            if b == b'\x07':
                continue

            self._bt_buf += b

            if b in (b'\r', b'\n'):
                line = bytes(self._bt_buf).rstrip(b"\r\n") 
                self._bt_buf = bytearray()

                if line:
                    self._rx_lines.append(line)

                    if self.print_incoming:
                        sys.stdout.write("\n<BT> " + line.decode("utf-8", errors="replace") + "\n")
                        sys.stdout.flush()

    def bt_line_available(self):
        return len(self._rx_lines) > 0

    def read_bt_line(self):
        """Pop oldest received BT line (bytes, no CR/LF) or None."""
        if self._rx_lines:
            return self._rx_lines.pop(0)
        return None

class Tee:
    def __init__(self, usb_stream, bt_uart):
        self.usb = usb_stream
        self.bt = bt_uart

    def write(self, s):
        # Write to USB stream (expects str)
        try:
            self.usb.write(s)
        except Exception:
            pass

        # Write to BT UART (expects bytes)
        try:
            if isinstance(s, str):
                self.bt.write(s.encode())
            else:
                self.bt.write(s)
        except Exception:
            pass

    def flush(self):
        try:
            self.usb.flush()
        except Exception:
            pass
