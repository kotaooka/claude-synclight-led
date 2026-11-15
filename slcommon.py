"""フックと常駐プログラムで共有する設定・パス・プロセス操作。"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import subprocess
from pathlib import Path

HOME = Path(os.environ.get("CLAUDE_SYNCLIGHT_HOME", Path.home() / ".claude" / "synclight"))
SESSIONS = HOME / "sessions"
CONFIG = HOME / "config.json"
STOP_FLAG = HOME / "stop"
LOG = HOME / "daemon.log"
MUTEX_NAME = "Local\\ClaudeSyncLightDaemon"
SYNCLIGHT_EXE_NAME = "SyncLight.exe"

DEFAULT_CONFIG = {
    "lamps": 54,               # LEDの灯数
    "takeover": False,         # True: Claude作業中はSyncLightを終了し、終わったら起動し直す
    "done_seconds": 180,       # 完了(緑)を表示する秒数。その後は待機色
    "restore_seconds": 120,    # takeover時、作業が止まってからSyncLightに戻すまでの秒数
    "synclight_exe": "",       # SyncLight.exe のパス（空なら終了時に記録したものを使う）
    "colors": {
        "working": [255, 90, 20],
        "waiting": [255, 200, 0],
        "done": [0, 200, 60],
        "idle": [0, 0, 40],
    },
}

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.CreateMutexW.restype = wt.HANDLE
k32.CreateMutexW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.LPCWSTR]
k32.OpenMutexW.restype = wt.HANDLE
k32.OpenMutexW.argtypes = [wt.DWORD, wt.BOOL, wt.LPCWSTR]
k32.CloseHandle.argtypes = [wt.HANDLE]
k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]

NO_WINDOW = 0x08000000
DETACHED = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP


def load_config():
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        user = json.loads(CONFIG.read_text(encoding="utf-8"))
        colors = user.pop("colors", {})
        cfg.update(user)
        cfg["colors"].update(colors)
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg):
    HOME.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def daemon_running():
    h = k32.OpenMutexW(0x00100000, False, MUTEX_NAME)  # SYNCHRONIZE
    if h:
        k32.CloseHandle(h)
        return True
    return False


def acquire_daemon_mutex():
    """常駐プログラムの多重起動防止。取れなければ None。"""
    ctypes.set_last_error(0)
    h = k32.CreateMutexW(None, False, MUTEX_NAME)
    if not h or ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        return None
    return h


# ---------- SyncLight プロセス ----------
class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD),
                ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                ("szExeFile", ctypes.c_wchar * 260)]


k32.Process32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]


def synclight_pids():
    snap = k32.CreateToolhelp32Snapshot(0x2, 0)  # TH32CS_SNAPPROCESS
    pids = []
    try:
        e = PROCESSENTRY32W(); e.dwSize = ctypes.sizeof(e)
        ok = k32.Process32FirstW(snap, ctypes.byref(e))
        while ok:
            if e.szExeFile.lower() == SYNCLIGHT_EXE_NAME.lower():
                pids.append(e.th32ProcessID)
            ok = k32.Process32NextW(snap, ctypes.byref(e))
    finally:
        k32.CloseHandle(snap)
    return pids


def process_path(pid):
    h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024); n = wt.DWORD(1024)
        return buf.value if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)) else ""
    finally:
        k32.CloseHandle(h)


def synclight_running():
    return bool(synclight_pids())


def kill_synclight():
    """SyncLightを終了し、実行ファイルのパスを返す。"""
    pids = synclight_pids()
    path = next((p for p in map(process_path, pids) if p), "")
    if pids:
        subprocess.run(["taskkill", "/F", "/T", "/IM", SYNCLIGHT_EXE_NAME],
                       capture_output=True, creationflags=NO_WINDOW)
    return path


def launch_synclight(path):
    if path and Path(path).exists():
        subprocess.Popen([path], cwd=str(Path(path).parent), creationflags=DETACHED,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, close_fds=True)
        return True
    return False
