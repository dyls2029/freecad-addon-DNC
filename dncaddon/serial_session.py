import FreeCAD

try:
    import serial
except Exception:
    serial = None


class SerialSession:
    def __init__(self, port, baudrate=9600, timeout=1, transport_mode="basic", rtscts=False, bytesize=7, parity="EVEN", stopbits="TWO", line_ending="CRLF", received_line_ending="CRLF", raw_received=False):
        self.port = port
        self.baudrate = int(baudrate)
        self.timeout = timeout
        self.transport_mode = transport_mode
        self.rtscts = rtscts
        self.bytesize = int(bytesize)
        self.parity = parity.upper()
        self.stopbits = stopbits.upper()
        self.line_ending = line_ending.upper().replace("/", "")
        self.received_line_ending = received_line_ending.upper().replace("/", "")
        self.raw_received = bool(raw_received)
        self._serial = None

    def open(self):
        if serial is None:
            raise RuntimeError("pyserial is not installed")

        kwargs = {
            "port": self.port,
            "baudrate": self.baudrate,
            "timeout": self.timeout,
        }

        parity_map = {
            "NONE": serial.PARITY_NONE,
            "EVEN": serial.PARITY_EVEN,
            "ODD": serial.PARITY_ODD,
            "MARK": serial.PARITY_MARK,
            "SPACE": serial.PARITY_SPACE,
        }
        stopbits_map = {
            "ONE": serial.STOPBITS_ONE,
            "1": serial.STOPBITS_ONE,
            "ONEPOINTFIVE": serial.STOPBITS_ONE_POINT_FIVE,
            "1.5": serial.STOPBITS_ONE_POINT_FIVE,
            "1POINT5": serial.STOPBITS_ONE_POINT_FIVE,
            "TWO": serial.STOPBITS_TWO,
            "2": serial.STOPBITS_TWO,
        }
        bytesize_map = {
            5: serial.FIVEBITS,
            6: serial.SIXBITS,
            7: serial.SEVENBITS,
            8: serial.EIGHTBITS,
        }

        kwargs["bytesize"] = bytesize_map.get(self.bytesize, serial.SEVENBITS)
        kwargs["parity"] = parity_map.get(self.parity, serial.PARITY_EVEN)
        kwargs["stopbits"] = stopbits_map.get(self.stopbits, serial.STOPBITS_TWO)

        if self.transport_mode == "adapter":
            kwargs.update({
                "xonxoff": True,
                "rtscts": self.rtscts,
                "dsrdtr": False
            })
        else:
            kwargs.update({
                "xonxoff": False,
                "rtscts": self.rtscts,
                "dsrdtr": False
            })

        self._serial = serial.Serial(**kwargs)

    def close(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None

    def is_open(self):
        return self._serial is not None and self._serial.is_open

    def send_line(self, line):
        if not self.is_open():
            raise RuntimeError("Serial session is not open")

        ending = "\r\n"
        if self.line_ending == "CR":
            ending = "\r"
        elif self.line_ending == "LF":
            ending = "\n"

        self._serial.write((line + ending).encode("ascii", errors="ignore"))
        self._serial.flush()

    def read_all(self):
        if not self.is_open():
            return ""

        try:
            waiting = getattr(self._serial, "in_waiting", 0)

            if waiting:
                data = self._serial.read(waiting)
            else:
                return ""

            if self.raw_received:
                return " ".join(f"{b:02X}" for b in data)

            text = data.decode("ascii", errors="replace")

            # Remove control characters but keep CR/LF/TAB
            text = "".join(
                c for c in text
                if c in "\r\n\t" or ord(c) >= 32
            )

            if self.received_line_ending == "LFCRCR":
                # Fanuc LFCRCR -> single newline
                text = text.replace("\n\r\r", "\n")

            elif self.received_line_ending == "CRLF":
                text = text.replace("\r\n", "\n")

            elif self.received_line_ending == "CR":
                text = text.replace("\r", "\n")

            elif self.received_line_ending == "LF":
                pass

            return text

        except Exception as exc:
            return f"\n[RECEIVE ERROR] {exc}\n"

        return ""