"""Tray utility that inverts the visible portion of a selected top-level window.

The implementation intentionally uses only the Python standard library. GDI's
``NOTSRCCOPY`` operation performs the inversion in the compositor capture path,
while rectangle subtraction keeps overlays away from windows above the selected
window in Z order.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from dataclasses import dataclass
from typing import Optional, Union


if sys.platform != "win32":
    raise SystemExit("此工具仅支持 Windows 10/11。")


# ---- Win32 constants -----------------------------------------------------
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

try:
    SetProcessDpiAwarenessContext = user32.SetProcessDpiAwarenessContext
    SetProcessDpiAwarenessContext.argtypes = [wintypes.HANDLE]
    SetProcessDpiAwarenessContext.restype = wintypes.BOOL
    # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = (HANDLE)-4
    SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except (AttributeError, OSError, OverflowError):
    try:
        user32.SetProcessDPIAware()
    except AttributeError:
        pass


HWND = wintypes.HWND
HINSTANCE = wintypes.HINSTANCE
HMENU = wintypes.HMENU
HICON = wintypes.HICON
HBRUSH = wintypes.HBRUSH
HDC = wintypes.HDC
LRESULT = wintypes.LPARAM
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
ENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, HWND, wintypes.LPARAM)
UINT_PTR = ctypes.c_size_t

WM_NULL = 0x0000
WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_TIMER = 0x0113
WM_NCHITTEST = 0x0084
WM_MOUSEACTIVATE = 0x0021
WM_APP = 0x8000
WM_TRAY = WM_APP + 41
WM_RBUTTONUP = 0x0205
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203

HTTRANSPARENT = -1
MA_NOACTIVATE = 3
WS_POPUP = 0x80000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST = 0x00000008
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
WS_EX_LAYERED = 0x00080000
SW_HIDE = 0
SW_SHOW = 5
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_NOOWNERZORDER = 0x0200
HWND_TOPMOST = HWND(-1)

MF_STRING = 0x0000
MF_SEPARATOR = 0x0800
MF_POPUP = 0x0010
MF_CHECKED = 0x0008
MF_DISABLED = 0x0002
TPM_RIGHTBUTTON = 0x0002
TPM_RETURNCMD = 0x0100

NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
IDI_APPLICATION = 32512
ULW_ALPHA = 0x00000002
NOTSRCCOPY = 0x00330008
DWMWA_CLOAKED = 14
DWMWA_EXTENDED_FRAME_BOUNDS = 9
ERROR_ALREADY_EXISTS = 183

class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG)]


class SIZE(ctypes.Structure):
    _fields_ = [("cx", wintypes.LONG), ("cy", wintypes.LONG)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [("BlendOp", ctypes.c_ubyte), ("BlendFlags", ctypes.c_ubyte),
                ("SourceConstantAlpha", ctypes.c_ubyte), ("AlphaFormat", ctypes.c_ubyte)]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", HINSTANCE),
        ("hIcon", HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uTimeout", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", GUID),
        ("hBalloonIcon", HICON),
    ]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", HWND), ("message", wintypes.UINT), ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM), ("time", wintypes.DWORD), ("pt", POINT),
    ]


@dataclass(frozen=True)
class WindowInfo:
    hwnd: int
    title: str
    class_name: str


@dataclass(frozen=True)
class Box:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


def _handle(hwnd: Optional[Union[HWND, int]]) -> int:
    """Return a numeric HWND value (ctypes HWND is a c_void_p on 64-bit)."""
    if hwnd is None:
        return 0
    if isinstance(hwnd, int):
        return hwnd
    return int(hwnd.value or 0)


def _configure_api() -> None:
    """Set the signatures used by ctypes so failures are deterministic."""
    user32.EnumWindows.argtypes = [ENUMPROC, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.IsWindow.argtypes = [HWND]
    user32.IsWindow.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = [HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.IsIconic.argtypes = [HWND]
    user32.IsIconic.restype = wintypes.BOOL
    user32.GetWindowRect.argtypes = [HWND, ctypes.POINTER(RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.GetSystemMetrics.restype = ctypes.c_int
    user32.GetWindowTextLengthW.argtypes = [HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.argtypes = [HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindow.argtypes = [HWND, wintypes.UINT]
    user32.GetWindow.restype = HWND
    user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR,
                                       wintypes.LPCWSTR, wintypes.DWORD,
                                       ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                       ctypes.c_int, HWND, HMENU, HINSTANCE,
                                       wintypes.LPVOID]
    user32.CreateWindowExW.restype = HWND
    user32.DestroyWindow.argtypes = [HWND]
    user32.DestroyWindow.restype = wintypes.BOOL
    user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
    user32.RegisterClassW.restype = wintypes.ATOM
    user32.DefWindowProcW.argtypes = [HWND, wintypes.UINT, wintypes.WPARAM,
                                      wintypes.LPARAM]
    user32.DefWindowProcW.restype = LRESULT
    user32.SetWindowPos.argtypes = [HWND, HWND, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.SetTimer.argtypes = [HWND, UINT_PTR, wintypes.UINT, wintypes.LPVOID]
    user32.SetTimer.restype = UINT_PTR
    user32.KillTimer.argtypes = [HWND, UINT_PTR]
    user32.ShowWindow.argtypes = [HWND, ctypes.c_int]
    user32.UpdateWindow.argtypes = [HWND]
    user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), HWND, wintypes.UINT, wintypes.UINT]
    user32.GetMessageW.restype = wintypes.BOOL
    user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
    user32.PostQuitMessage.argtypes = [ctypes.c_int]
    user32.PostMessageW.argtypes = [HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
    user32.SetForegroundWindow.argtypes = [HWND]
    user32.TrackPopupMenu.argtypes = [HMENU, wintypes.UINT, ctypes.c_int,
                                       ctypes.c_int, ctypes.c_int, HWND,
                                       ctypes.POINTER(RECT)]
    user32.TrackPopupMenu.restype = wintypes.UINT
    user32.CreatePopupMenu.restype = HMENU
    user32.AppendMenuW.argtypes = [HMENU, wintypes.UINT, UINT_PTR,
                                   wintypes.LPCWSTR]
    user32.AppendMenuW.restype = wintypes.BOOL
    user32.DestroyMenu.argtypes = [HMENU]
    user32.DestroyMenu.restype = wintypes.BOOL
    user32.LoadIconW.restype = HICON
    shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD,
                                          ctypes.POINTER(NOTIFYICONDATAW)]
    shell32.Shell_NotifyIconW.restype = wintypes.BOOL
    dwmapi.DwmGetWindowAttribute.argtypes = [HWND, wintypes.DWORD,
                                             wintypes.LPVOID, wintypes.DWORD]
    dwmapi.DwmGetWindowAttribute.restype = wintypes.LONG

    user32.GetDC.argtypes = [HWND]
    user32.GetDC.restype = HDC
    user32.ReleaseDC.argtypes = [HWND, HDC]
    user32.ReleaseDC.restype = ctypes.c_int
    user32.PrintWindow.argtypes = [HWND, HDC, wintypes.UINT]
    user32.PrintWindow.restype = wintypes.BOOL
    user32.UpdateLayeredWindow.argtypes = [HWND, HWND, ctypes.POINTER(POINT),
                                           ctypes.POINTER(SIZE), HDC,
                                           ctypes.POINTER(POINT), wintypes.COLORREF,
                                           ctypes.POINTER(BLENDFUNCTION), wintypes.DWORD]
    user32.UpdateLayeredWindow.restype = wintypes.BOOL
    gdi32.CreateCompatibleDC.argtypes = [HDC]
    gdi32.CreateCompatibleDC.restype = HDC
    gdi32.CreateCompatibleBitmap.argtypes = [HDC, ctypes.c_int, ctypes.c_int]
    gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
    gdi32.SelectObject.argtypes = [HDC, wintypes.HGDIOBJ]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteObject.restype = wintypes.BOOL
    gdi32.DeleteDC.argtypes = [HDC]
    gdi32.DeleteDC.restype = wintypes.BOOL
    gdi32.BitBlt.argtypes = [HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                             ctypes.c_int, HDC, ctypes.c_int, ctypes.c_int,
                             wintypes.DWORD]
    gdi32.BitBlt.restype = wintypes.BOOL
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = HINSTANCE
    kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    user32.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
    user32.RegisterWindowMessageW.restype = wintypes.UINT


_configure_api()


def _rect_for(hwnd: int) -> Optional[Box]:
    rect = RECT()
    # DWM's extended bounds omit the invisible resize border on modern Windows.
    # Fall back to GetWindowRect for classic/accelerated windows where DWM fails.
    if dwmapi.DwmGetWindowAttribute(HWND(hwnd), DWMWA_EXTENDED_FRAME_BOUNDS,
                                    ctypes.byref(rect), ctypes.sizeof(rect)) != 0:
        if not user32.GetWindowRect(HWND(hwnd), ctypes.byref(rect)):
            return None
    box = Box(rect.left, rect.top, rect.right, rect.bottom)
    return box if box.width > 0 and box.height > 0 else None


def _virtual_screen() -> Box:
    """Return the current virtual desktop in physical, DPI-aware pixels."""
    return Box(
        user32.GetSystemMetrics(76), user32.GetSystemMetrics(77),
        user32.GetSystemMetrics(76) + user32.GetSystemMetrics(78),
        user32.GetSystemMetrics(77) + user32.GetSystemMetrics(79),
    )


def _clip_box(box: Box, bounds: Box) -> Optional[Box]:
    clipped = Box(max(box.left, bounds.left), max(box.top, bounds.top),
                  min(box.right, bounds.right), min(box.bottom, bounds.bottom))
    return clipped if clipped.width > 0 and clipped.height > 0 else None


def _is_cloaked(hwnd: int) -> bool:
    value = wintypes.DWORD()
    result = dwmapi.DwmGetWindowAttribute(HWND(hwnd), DWMWA_CLOAKED,
                                          ctypes.byref(value), ctypes.sizeof(value))
    return result == 0 and value.value != 0


def _window_title(hwnd: int) -> tuple[str, str]:
    length = user32.GetWindowTextLengthW(HWND(hwnd))
    title_buf = ctypes.create_unicode_buffer(max(2, length + 1))
    user32.GetWindowTextW(HWND(hwnd), title_buf, len(title_buf))
    class_buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(HWND(hwnd), class_buf, len(class_buf))
    title = title_buf.value.strip()
    class_name = class_buf.value.strip()
    return title, class_name


def _subtract_box(source: Box, cut: Box) -> list[Box]:
    left = max(source.left, cut.left)
    top = max(source.top, cut.top)
    right = min(source.right, cut.right)
    bottom = min(source.bottom, cut.bottom)
    if left >= right or top >= bottom:
        return [source]
    pieces: list[Box] = []
    if source.top < top:
        pieces.append(Box(source.left, source.top, source.right, top))
    if bottom < source.bottom:
        pieces.append(Box(source.left, bottom, source.right, source.bottom))
    if source.left < left:
        pieces.append(Box(source.left, top, left, bottom))
    if right < source.right:
        pieces.append(Box(right, top, source.right, bottom))
    return [piece for piece in pieces if piece.width > 0 and piece.height > 0]


class Overlay:
    """One click-through layered window for one visible rectangle."""

    def __init__(self, owner: "InvertApp") -> None:
        self.owner = owner
        exstyle = WS_EX_TOOLWINDOW | WS_EX_TOPMOST | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_LAYERED
        self.host = user32.CreateWindowExW(
            exstyle, owner.class_name, "", WS_POPUP,
            0, 0, 1, 1, None, None, owner.instance, None,
        )
        if not self.host:
            raise ctypes.WinError(ctypes.get_last_error())
        self.box: Optional[Box] = None

    def set_box(self, box: Box) -> None:
        self.box = box
        user32.SetWindowPos(self.host, HWND_TOPMOST, box.left, box.top,
                            box.width, box.height,
                            SWP_NOACTIVATE | SWP_NOOWNERZORDER)

    def update_pixels(self, source_dc: HDC, source_origin: Box) -> None:
        """Invert a crop from a target-window bitmap and publish it atomically."""
        if not self.box or not self.host:
            return
        box = self.box
        memory_dc = gdi32.CreateCompatibleDC(source_dc)
        bitmap = gdi32.CreateCompatibleBitmap(source_dc, box.width, box.height)
        if not memory_dc or not bitmap:
            if memory_dc:
                gdi32.DeleteDC(memory_dc)
            return
        old_bitmap = gdi32.SelectObject(memory_dc, bitmap)
        try:
            if not gdi32.BitBlt(memory_dc, 0, 0, box.width, box.height,
                                source_dc, box.left - source_origin.left,
                                box.top - source_origin.top, NOTSRCCOPY):
                return
            destination = POINT(box.left, box.top)
            size = SIZE(box.width, box.height)
            source = POINT(0, 0)
            # A compatible bitmap has no meaningful alpha channel. Use the
            # constant alpha path so its RGB pixels are treated as opaque.
            blend = BLENDFUNCTION(0, 0, 255, 0)
            if not user32.UpdateLayeredWindow(self.host, None,
                                              ctypes.byref(destination), ctypes.byref(size),
                                              memory_dc, ctypes.byref(source), 0,
                                              ctypes.byref(blend), ULW_ALPHA):
                self.hide()
            else:
                user32.ShowWindow(self.host, SW_SHOW)
        finally:
            gdi32.SelectObject(memory_dc, old_bitmap)
            gdi32.DeleteObject(bitmap)
            gdi32.DeleteDC(memory_dc)

    def hide(self) -> None:
        user32.ShowWindow(self.host, SW_HIDE)

    def destroy(self) -> None:
        if self.host:
            user32.DestroyWindow(self.host)
        self.host = None


class InvertApp:
    TIMER_ID = 7
    CMD_SELECT_BASE = 1000
    CMD_TOGGLE = 10
    CMD_EXIT = 11

    def __init__(self) -> None:
        self.mutex = kernel32.CreateMutexW(None, True, "Local\\WindowInvertTrayMutex")
        if not self.mutex:
            raise ctypes.WinError(ctypes.get_last_error())
        if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(self.mutex)
            raise RuntimeError("工具已经在运行")
        self.instance = kernel32.GetModuleHandleW(None)
        self.class_name = "WindowInvertTrayHost"
        self.overlay_class = "WindowInvertOverlay"
        self._callbacks: list[WNDPROC] = []
        self.overlays: list[Overlay] = []
        self.target: Optional[int] = None
        self.enabled = False
        self.window_cache: dict[int, int] = {}
        self.tray_added = False
        self.menu_open = False
        self.taskbar_created_msg = user32.RegisterWindowMessageW("TaskbarCreated")
        self.running = True
        self._register_classes()
        self.hwnd = user32.CreateWindowExW(
            WS_EX_TOOLWINDOW, self.class_name, "Window Invert", WS_POPUP,
            0, 0, 0, 0, None, None, self.instance, None,
        )
        if not self.hwnd:
            raise ctypes.WinError(ctypes.get_last_error())
        self._add_tray_icon()
        user32.SetTimer(self.hwnd, self.TIMER_ID, 33, None)

    def _register_classes(self) -> None:
        @WNDPROC
        def tray_proc(hwnd, msg, wparam, lparam):
            try:
                return self._tray_proc(hwnd, msg, wparam, lparam)
            except Exception:
                return 0

        @WNDPROC
        def overlay_proc(hwnd, msg, wparam, lparam):
            try:
                if msg == WM_NCHITTEST:
                    return HTTRANSPARENT
                if msg == WM_MOUSEACTIVATE:
                    return MA_NOACTIVATE
                if msg == WM_CLOSE:
                    return 0
                return user32.DefWindowProcW(hwnd, msg, wparam, lparam)
            except Exception:
                return 0

        self.tray_proc = tray_proc
        self.overlay_proc = overlay_proc
        self._callbacks.extend([tray_proc, overlay_proc])
        for name, proc in ((self.class_name, tray_proc), (self.overlay_class, overlay_proc)):
            wc = WNDCLASSW()
            wc.lpfnWndProc = proc
            wc.hInstance = self.instance
            wc.lpszClassName = name
            # A null background keeps the overlay compositor-only.
            if not user32.RegisterClassW(ctypes.byref(wc)):
                error = ctypes.get_last_error()
                if error != 1410:  # ERROR_CLASS_ALREADY_EXISTS
                    raise ctypes.WinError(error)

    def _add_tray_icon(self) -> None:
        icon = user32.LoadIconW(None, IDI_APPLICATION)
        self.notify_data = NOTIFYICONDATAW()
        self.notify_data.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        self.notify_data.hWnd = self.hwnd
        self.notify_data.uID = 1
        self.notify_data.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        self.notify_data.uCallbackMessage = WM_TRAY
        self.notify_data.hIcon = icon
        self._set_tray_tip()
        self.tray_added = bool(shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self.notify_data)))

    def _set_tray_tip(self) -> None:
        if self.enabled and self.target:
            tip = "窗口反相：开启"
        elif self.target:
            tip = "窗口反相：关闭"
        else:
            tip = "窗口反相：未选择窗口"
        self.notify_data.szTip = tip
        if getattr(self, "tray_added", False) and self.hwnd:
            shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self.notify_data))

    def _remove_tray_icon(self) -> None:
        if getattr(self, "notify_data", None):
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.notify_data))

    def _tray_proc(self, hwnd, msg, wparam, lparam):
        if msg == self.taskbar_created_msg:
            self.tray_added = bool(shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self.notify_data)))
            return 0
        if msg == WM_TRAY and lparam in (WM_RBUTTONUP, WM_LBUTTONUP, WM_LBUTTONDBLCLK):
            if lparam == WM_LBUTTONDBLCLK and self.target:
                self.enabled = not self.enabled
                self._set_tray_tip()
                self.refresh()
            else:
                self.show_menu()
            return 0
        if msg == WM_TIMER and wparam == self.TIMER_ID and not self.menu_open:
            self.refresh()
            return 0
        if msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _enumerate_windows(self) -> list[WindowInfo]:
        result: list[WindowInfo] = []
        own_hosts = {_handle(item.host) for item in self.overlays if item.host}

        @ENUMPROC
        def callback(hwnd, _lparam):
            handle = _handle(hwnd)
            if handle == _handle(self.hwnd) or handle in own_hosts:
                return 1
            if not user32.IsWindowVisible(hwnd) or _is_cloaked(handle):
                return 1
            title, class_name = _window_title(handle)
            if not title:
                title = f"[{class_name or '无标题窗口'}]"
            result.append(WindowInfo(handle, title, class_name))
            return 1

        user32.EnumWindows(callback, 0)
        return result

    def _z_order_windows(self) -> list[int]:
        handles: list[int] = []

        @ENUMPROC
        def callback(hwnd, _lparam):
            handles.append(_handle(hwnd))
            return 1

        user32.EnumWindows(callback, 0)
        return handles

    def show_menu(self) -> None:
        windows = self._enumerate_windows()
        menu = user32.CreatePopupMenu()
        submenu = user32.CreatePopupMenu()
        self.window_cache.clear()
        for index, info in enumerate(windows):
            command = self.CMD_SELECT_BASE + index
            self.window_cache[command] = info.hwnd
            marker = MF_CHECKED if info.hwnd == self.target else 0
            label = f"{info.title[:88]}  ({info.hwnd:#x})".replace("&", "&&")
            user32.AppendMenuW(submenu, MF_STRING | marker, command, label)
        if not windows:
            user32.AppendMenuW(submenu, MF_STRING | MF_DISABLED, 0, "没有可选择的窗口")
        user32.AppendMenuW(menu, MF_POPUP, submenu, "选择反相窗口")
        user32.AppendMenuW(menu, MF_STRING | (MF_CHECKED if self.enabled else 0),
                           self.CMD_TOGGLE, "关闭反相" if self.enabled else "开启反相")
        user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(menu, MF_STRING, self.CMD_EXIT, "退出")
        point = POINT()
        user32.GetCursorPos(ctypes.byref(point))
        user32.SetForegroundWindow(self.hwnd)
        command = 0
        self.menu_open = True
        try:
            command = user32.TrackPopupMenu(menu, TPM_RIGHTBUTTON | TPM_RETURNCMD,
                                            point.x, point.y, 0, self.hwnd, None)
        finally:
            self.menu_open = False
        user32.PostMessageW(self.hwnd, WM_NULL, 0, 0)
        user32.DestroyMenu(submenu)
        user32.DestroyMenu(menu)
        if command in self.window_cache:
            self.select_window(self.window_cache[command])
        elif command == self.CMD_TOGGLE:
            self.toggle()
        elif command == self.CMD_EXIT:
            self.shutdown()

    def select_window(self, hwnd: int) -> None:
        if not user32.IsWindow(HWND(hwnd)):
            return
        self.target = hwnd
        self.enabled = True
        self._set_tray_tip()
        self.refresh()

    def toggle(self) -> None:
        if not self.target or not user32.IsWindow(HWND(self.target)):
            ctypes.windll.user32.MessageBoxW(self.hwnd, "请先选择反相窗口。", "窗口反相", 0x40)
            self.target = None
            self.enabled = False
            self._set_tray_tip()
            return
        self.enabled = not self.enabled
        self._set_tray_tip()
        self.refresh()

    def _visible_boxes(self, target: int) -> list[Box]:
        target_box = _rect_for(target)
        if not target_box or user32.IsIconic(HWND(target)) or not user32.IsWindowVisible(HWND(target)):
            return []
        target_box = _clip_box(target_box, _virtual_screen())
        if not target_box:
            return []
        order = self._z_order_windows()
        try:
            target_index = order.index(target)
        except ValueError:
            return []
        visible = [target_box]
        own_hosts = {_handle(item.host) for item in self.overlays if item.host}
        # EnumWindows is top-to-bottom. Only windows preceding the target can occlude it.
        for hwnd in order[:target_index]:
            if hwnd in own_hosts or hwnd == _handle(self.hwnd):
                continue
            if not user32.IsWindowVisible(HWND(hwnd)) or user32.IsIconic(HWND(hwnd)) or _is_cloaked(hwnd):
                continue
            occluder = _rect_for(hwnd)
            if not occluder:
                continue
            next_visible: list[Box] = []
            for box in visible:
                next_visible.extend(_subtract_box(box, occluder))
            visible = next_visible
            if not visible:
                break
            # Avoid pathological overlay counts when many small windows overlap.
            # Pausing this frame is safer than drawing a region that could leak
            # over an occluding window.
            if len(visible) > 160:
                return []
        return visible

    def refresh(self) -> None:
        if not self.enabled or not self.target or not user32.IsWindow(HWND(self.target)):
            if self.target and not user32.IsWindow(HWND(self.target)):
                self.target = None
                self.enabled = False
                self._set_tray_tip()
            for item in self.overlays:
                item.hide()
            return
        target_box = _rect_for(self.target)
        if not target_box:
            for item in self.overlays:
                item.hide()
            return
        target_box = _clip_box(target_box, _virtual_screen())
        if not target_box:
            for item in self.overlays:
                item.hide()
            return
        boxes = self._visible_boxes(self.target)
        while len(self.overlays) < len(boxes):
            try:
                self.overlays.append(Overlay(self))
            except (OSError, RuntimeError):
                break
        if not boxes:
            for item in self.overlays:
                item.hide()
            return
        # PrintWindow renders the target into an off-screen bitmap, so the
        # already-visible overlays never become part of their own source.
        screen_dc = user32.GetDC(None)
        if not screen_dc:
            return
        source_dc = gdi32.CreateCompatibleDC(screen_dc)
        source_bitmap = gdi32.CreateCompatibleBitmap(screen_dc,
                                                     target_box.width, target_box.height)
        if not source_dc or not source_bitmap:
            if source_dc:
                gdi32.DeleteDC(source_dc)
            user32.ReleaseDC(None, screen_dc)
            return
        old_source_bitmap = gdi32.SelectObject(source_dc, source_bitmap)
        try:
            printed = user32.PrintWindow(HWND(self.target), source_dc, 2)
            if not printed:
                # Some windows only honor the legacy WM_PRINT path.
                printed = user32.PrintWindow(HWND(self.target), source_dc, 0)
            if not printed:
                return
            for index, item in enumerate(self.overlays):
                if index < len(boxes):
                    item.set_box(boxes[index])
                    item.update_pixels(source_dc, target_box)
                else:
                    item.hide()
        finally:
            gdi32.SelectObject(source_dc, old_source_bitmap)
            gdi32.DeleteObject(source_bitmap)
            gdi32.DeleteDC(source_dc)
            user32.ReleaseDC(None, screen_dc)

    def shutdown(self) -> None:
        if not self.running:
            return
        self.running = False
        user32.KillTimer(self.hwnd, self.TIMER_ID)
        for item in self.overlays:
            item.destroy()
        self.overlays.clear()
        self._remove_tray_icon()
        user32.DestroyWindow(self.hwnd)
        kernel32.CloseHandle(self.mutex)

    def run(self) -> None:
        msg = MSG()
        try:
            while self.running:
                result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if result <= 0:
                    break
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            self.shutdown()


def main() -> None:
    try:
        app = InvertApp()
    except Exception as exc:
        ctypes.windll.user32.MessageBoxW(None, f"工具启动失败：{exc}", "窗口反相", 0x10)
        return
    app.run()


if __name__ == "__main__":
    main()
