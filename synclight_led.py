"""Robobloq SyncLight (HID 1A86:FE07) のLEDを直接制御するスクリプト。

使い方:
  python synclight_led.py <state|#RRGGBB|off> [lamps]
  state: working / waiting / done / idle / off
手動テスト用のCLI兼ライブラリ（常駐プログラムから Device クラスを使う）。

プロトコル (SyncLight app.asar より解析):
  "RB" | len | seq | 0x86(setSectionLED) | [start, R, G, B, end]... | sum%256
  HIDには report ID 0 を前置して64バイト単位で書き込む。
"""
import ctypes
import ctypes.wintypes as wt
import os
import sys

VID, PID = 0x1A86, 0xFE07
LAMPS_DEFAULT = int(os.environ.get("SYNCLIGHT_LAMPS", "54"))  # LEDの灯数

STATES = {
    "working": (255, 90, 20),    # Claudeオレンジ: 作業中
    "waiting": (255, 200, 0),    # 黄: 許可・入力待ち
    "done":    (0, 200, 60),     # 緑: 応答完了
    "idle":    (0, 0, 40),       # うす青: 待機
    "off":     (0, 0, 0),
}

# ---------- Windows HID 列挙 ----------
setupapi = ctypes.WinDLL("setupapi", use_last_error=True)
hid = ctypes.WinDLL("hid", use_last_error=True)
k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class GUID(ctypes.Structure):
    _fields_ = [("d1", wt.DWORD), ("d2", wt.WORD), ("d3", wt.WORD), ("d4", ctypes.c_ubyte * 8)]


class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("guid", GUID), ("flags", wt.DWORD), ("reserved", ctypes.c_void_p)]


class HIDP_CAPS(ctypes.Structure):
    _fields_ = [("Usage", wt.USHORT), ("UsagePage", wt.USHORT),
                ("InputReportByteLength", wt.USHORT), ("OutputReportByteLength", wt.USHORT),
                ("FeatureReportByteLength", wt.USHORT), ("Reserved", wt.USHORT * 17),
                ("rest", wt.USHORT * 10)]


setupapi.SetupDiGetClassDevsW.restype = ctypes.c_void_p
setupapi.SetupDiGetClassDevsW.argtypes = [ctypes.POINTER(GUID), wt.LPCWSTR, wt.HWND, wt.DWORD]
setupapi.SetupDiEnumDeviceInterfaces.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(GUID), wt.DWORD,
                                                 ctypes.POINTER(SP_DEVICE_INTERFACE_DATA)]
setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [ctypes.c_void_p, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA),
                                                      ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
setupapi.SetupDiDestroyDeviceInfoList.argtypes = [ctypes.c_void_p]
k32.CreateFileW.restype = wt.HANDLE
k32.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD, wt.HANDLE]
k32.WriteFile.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
k32.CloseHandle.argtypes = [wt.HANDLE]
hid.HidD_GetPreparsedData.argtypes = [wt.HANDLE, ctypes.POINTER(ctypes.c_void_p)]
hid.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]
hid.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(HIDP_CAPS)]

INVALID_HANDLE = wt.HANDLE(-1).value


def find_device_path():
    g = GUID()
    hid.HidD_GetHidGuid(ctypes.byref(g))
    h = setupapi.SetupDiGetClassDevsW(ctypes.byref(g), None, None, 0x12)  # PRESENT|DEVICEINTERFACE
    key = f"vid_{VID:04x}&pid_{PID:04x}&mi_00"
    try:
        i = 0
        while True:
            d = SP_DEVICE_INTERFACE_DATA(); d.cbSize = ctypes.sizeof(d)
            if not setupapi.SetupDiEnumDeviceInterfaces(h, None, ctypes.byref(g), i, ctypes.byref(d)):
                return None
            i += 1
            need = wt.DWORD()
            setupapi.SetupDiGetDeviceInterfaceDetailW(h, ctypes.byref(d), None, 0, ctypes.byref(need), None)
            buf = ctypes.create_string_buffer(need.value)
            ctypes.cast(buf, ctypes.POINTER(wt.DWORD))[0] = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
            if setupapi.SetupDiGetDeviceInterfaceDetailW(h, ctypes.byref(d), buf, need, None, None):
                path = ctypes.wstring_at(ctypes.addressof(buf) + 4)
                if key in path.lower():
                    return path
    finally:
        setupapi.SetupDiDestroyDeviceInfoList(h)


def build_section_packet(sections, seq):
    """sections: [(start, r, g, b, end), ...]  (LED番号は1始まり)"""
    data = [v for s in sections for v in s]
    n = 6 + len(data)
    pkt = bytearray(n)
    pkt[0:2] = b"RB"
    pkt[2], pkt[3], pkt[4] = n, seq, 0x86
    pkt[5:5 + len(data)] = bytes(data)
    pkt[-1] = sum(pkt) % 256
    return bytes(pkt)


class Device:
    """LEDへのHIDハンドルを保持する。アニメーション用に開きっぱなしで使える。"""

    def __init__(self, lamps=LAMPS_DEFAULT):
        self.lamps = lamps
        self.fh = None
        self.out_len = 65
        self.seq = (os.getpid() % 253) + 1

    def open(self):
        if self.fh is not None:
            return
        path = find_device_path()
        if not path:
            raise RuntimeError("SyncLight LED (1A86:FE07) が見つかりません")
        fh = k32.CreateFileW(path, 0xC0000000, 0x3, None, 3, 0, None)  # RW, share RW, OPEN_EXISTING
        if fh == INVALID_HANDLE:
            raise ctypes.WinError(ctypes.get_last_error())
        pp = ctypes.c_void_p(); caps = HIDP_CAPS()
        if hid.HidD_GetPreparsedData(fh, ctypes.byref(pp)):
            hid.HidP_GetCaps(pp, ctypes.byref(caps)); hid.HidD_FreePreparsedData(pp)
            self.out_len = caps.OutputReportByteLength or 65
        self.fh = fh

    def close(self):
        if self.fh is not None:
            k32.CloseHandle(self.fh)
            self.fh = None

    def send(self, packet):
        self.open()
        chunk = self.out_len - 1
        try:
            for i in range(0, len(packet), chunk):
                report = (bytes([0]) + packet[i:i + chunk]).ljust(self.out_len, b"\0")
                written = wt.DWORD()
                if not k32.WriteFile(self.fh, report, len(report), ctypes.byref(written), None):
                    raise ctypes.WinError(ctypes.get_last_error())
        except OSError:
            self.close()  # 抜き差し等。次回に開き直す
            raise

    def sections(self, sections):
        self.seq = self.seq % 254 + 1
        self.send(build_section_packet(list(sections) + [(self.lamps + 1, 0, 0, 0, 254)], self.seq))

    def color(self, rgb):
        r, g, b = (max(0, min(255, int(v))) for v in rgb)
        self.sections([(1, r, g, b, self.lamps)])

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def send(packet):
    with Device() as d:
        d.send(packet)


def set_color(rgb, lamps=LAMPS_DEFAULT):
    with Device(lamps) as d:
        d.color(rgb)


def parse(arg):
    if arg in STATES:
        return STATES[arg]
    a = arg.lstrip("#")
    return tuple(int(a[i:i + 2], 16) for i in (0, 2, 4))


def main():
    if len(sys.argv) < 2:
        print(__doc__); return 1
    lamps = int(sys.argv[2]) if len(sys.argv) > 2 else LAMPS_DEFAULT
    try:
        set_color(parse(sys.argv[1]), lamps)
    except Exception as e:  # フックの失敗でClaudeを止めない
        print(f"synclight_led: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
