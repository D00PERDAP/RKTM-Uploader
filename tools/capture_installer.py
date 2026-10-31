"""Verify real installer Unicode labels before any installation and capture its welcome page."""
import ctypes
from ctypes import wintypes
import subprocess
import sys
import time
from pathlib import Path
from PIL import ImageGrab

user=ctypes.windll.user32
callback=ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user.GetWindowTextLengthW.argtypes=[wintypes.HWND]
user.GetWindowTextW.argtypes=[wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user.GetWindowThreadProcessId.argtypes=[wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user.GetWindowRect.argtypes=[wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user.IsWindowVisible.argtypes=[wintypes.HWND]
user.SetForegroundWindow.argtypes=[wintypes.HWND]

def text(hwnd):
    buf=ctypes.create_unicode_buffer(user.GetWindowTextLengthW(hwnd)+1)
    user.GetWindowTextW(hwnd, buf, len(buf))
    return buf.value

proc=subprocess.Popen([str(Path(sys.argv[1]).resolve()), '/SP-', '/NORESTART'])
try:
    hwnds=[]
    @callback
    def find(hwnd, param):
        pid=wintypes.DWORD()
        user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if user.IsWindowVisible(hwnd) and 'РКТМ' in text(hwnd) and 'Установка' in text(hwnd):hwnds.append(hwnd)
        return True
    for _ in range(100):
        user.EnumWindows(find, 0)
        if hwnds:break
        time.sleep(.1)
    assert hwnds, 'Installer title must contain correctly decoded РКТМ'
    hwnd=hwnds[0]
    labels=[]
    @callback
    def child(hwnd, param):
        labels.append(text(hwnd))
        return True
    user.EnumChildWindows(hwnd, child, 0)
    assert any('Установка РКТМ — Расписание' in label for label in labels), labels
    user.SetForegroundWindow(hwnd)
    time.sleep(.5)
    rect=wintypes.RECT()
    user.GetWindowRect(hwnd, ctypes.byref(rect))
    Path('previews').mkdir(exist_ok=True)
    ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom)).save('previews/installer.png')
    print('Installer Unicode title and welcome text verified')
finally:
    subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    proc.wait(timeout=10)
