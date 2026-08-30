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
shcore = ctypes.WinDLL("shcore", use_last_error=True)

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
WS_EX_NOREDIRECTIONBITMAP = 0x00200000
GWL_EXSTYLE = -20
SW_HIDE = 0
SW_SHOW = 5
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_NOOWNERZORDER = 0x0200
HWND_TOPMOST = HWND(-1)
GW_OWNER = 4
GA_ROOTOWNER = 3

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
SRCCOPY = 0x00CC0020
STRETCH_HALFTONE = 4
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


@dataclass
class CaptureSurface:
    """A rendered window bitmap kept alive between refreshes."""

    dc: HDC
    bitmap: wintypes.HBITMAP
    old_bitmap: wintypes.HGDIOBJ
    box: Box
    dpi_signature: tuple[int, int]


@dataclass
class TargetState:
    """Per-window capture/cache state for a selected inversion target."""

    hwnd: int
    surface: Optional[CaptureSurface] = None
    surface_key: Optional[tuple[int, int, int, int]] = None
    last_capture_box: Optional[Box] = None
    last_boxes: Optional[tuple[Box, ...]] = None


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
    user32.GetDpiForWindow.argtypes = [HWND]
    user32.GetDpiForWindow.restype = wintypes.UINT
    user32.MonitorFromWindow.argtypes = [HWND, wintypes.DWORD]
    user32.MonitorFromWindow.restype = wintypes.HANDLE
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.GetSystemMetrics.restype = ctypes.c_int
    user32.GetWindowTextLengthW.argtypes = [HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.argtypes = [HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindow.argtypes = [HWND, wintypes.UINT]
    user32.GetWindow.restype = HWND
    user32.GetAncestor.argtypes = [HWND, wintypes.UINT]
    user32.GetAncestor.restype = HWND
    user32.GetWindowLongPtrW.argtypes = [HWND, ctypes.c_int]
    user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.GetWindowThreadProcessId.argtypes = [HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
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
    gdi32.StretchBlt.argtypes = [HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                 ctypes.c_int, HDC, ctypes.c_int, ctypes.c_int,
                                 ctypes.c_int, ctypes.c_int, wintypes.DWORD]
    gdi32.StretchBlt.restype = wintypes.BOOL
    gdi32.SetStretchBltMode.argtypes = [HDC, ctypes.c_int]
    gdi32.SetStretchBltMode.restype = ctypes.c_int
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = HINSTANCE
    kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                     wintypes.LPWSTR,
                                                     ctypes.POINTER(wintypes.DWORD)]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    user32.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
    user32.RegisterWindowMessageW.restype = wintypes.UINT
    shcore.GetDpiForMonitor.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                        ctypes.POINTER(wintypes.UINT),
                                        ctypes.POINTER(wintypes.UINT)]
    shcore.GetDpiForMonitor.restype = ctypes.c_long


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


def _window_rect_for(hwnd: int) -> Optional[Box]:
    """Return the full Win32 window rect, including invisible resize borders."""
    rect = RECT()
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


def _monitor_dpi(hwnd: int) -> int:
    """Get effective DPI for the monitor containing a window."""
    monitor = user32.MonitorFromWindow(HWND(hwnd), 2)  # MONITOR_DEFAULTTONEAREST
    if monitor:
        dpi_x = wintypes.UINT()
        dpi_y = wintypes.UINT()
        if shcore.GetDpiForMonitor(monitor, 0, ctypes.byref(dpi_x),
                                   ctypes.byref(dpi_y)) == 0 and dpi_x.value:
            return int(dpi_x.value)
    return 96


def _clip_box(box: Box, bounds: Box) -> Optional[Box]:
    clipped = Box(max(box.left, bounds.left), max(box.top, bounds.top),
                  min(box.right, bounds.right), min(box.bottom, bounds.bottom))
    return clipped if clipped.width > 0 and clipped.height > 0 else None


def _is_cloaked(hwnd: int) -> bool:
    value = wintypes.DWORD()
    result = dwmapi.DwmGetWindowAttribute(HWND(hwnd), DWMWA_CLOAKED,
                                          ctypes.byref(value), ctypes.sizeof(value))
    return result == 0 and value.value != 0


def _is_owned_by(hwnd: int, owner: int) -> bool:
    """Return whether a top-level window is owned by the target window."""
    if not hwnd or not owner or hwnd == owner:
        return False
    root_owner = _handle(user32.GetAncestor(HWND(hwnd), GA_ROOTOWNER))
    if root_owner == owner:
        return True
    # Some frameworks use an intermediate owner window. Walk that chain as a
    # fallback because GetAncestor can stop at the framework's helper window.
    current = hwnd
    visited: set[int] = set()
    while current and current not in visited:
        visited.add(current)
        current = _handle(user32.GetWindow(HWND(current), GW_OWNER))
        if current == owner:
            return True
    return False


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
    CMD_SPEED_BASE = 20
    CMD_TOGGLE = 10
    CMD_EXIT = 11
    RENDER_SPEEDS = (
        (15, 67, "15 FPS（省资源）"),
        (30, 33, "30 FPS（标准）"),
        (60, 16, "60 FPS（流畅）"),
    )

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
        self.target_surface: Optional[CaptureSurface] = None
        self.target_surface_key: Optional[tuple[int, int, int, int]] = None
        self.last_capture_box: Optional[Box] = None
        self.last_target_boxes: Optional[tuple[Box, ...]] = None
        self.process_name_cache: dict[int, tuple[int, str]] = {}
        self.render_fps = 30
        self.render_interval_ms = 33
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
        user32.SetTimer(self.hwnd, self.TIMER_ID, self.render_interval_ms, None)

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
            tip = f"窗口反相：开启（{self.render_fps} FPS）"
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
        speed_menu = user32.CreatePopupMenu()
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
        for index, (fps, _interval, label) in enumerate(self.RENDER_SPEEDS):
            marker = MF_CHECKED if fps == self.render_fps else 0
            user32.AppendMenuW(speed_menu, MF_STRING | marker,
                               self.CMD_SPEED_BASE + index, label)
        user32.AppendMenuW(menu, MF_POPUP, speed_menu, "渲染速度")
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
        user32.DestroyMenu(speed_menu)
        user32.DestroyMenu(menu)
        if command in self.window_cache:
            self.select_window(self.window_cache[command])
        elif command == self.CMD_TOGGLE:
            self.toggle()
        elif self.CMD_SPEED_BASE <= command < self.CMD_SPEED_BASE + len(self.RENDER_SPEEDS):
            self.set_render_speed(self.RENDER_SPEEDS[command - self.CMD_SPEED_BASE][0])
        elif command == self.CMD_EXIT:
            self.shutdown()

    def set_render_speed(self, fps: int) -> None:
        for option_fps, interval, _label in self.RENDER_SPEEDS:
            if option_fps != fps:
                continue
            self.render_fps = option_fps
            self.render_interval_ms = interval
            if self.hwnd and self.running:
                user32.KillTimer(self.hwnd, self.TIMER_ID)
                user32.SetTimer(self.hwnd, self.TIMER_ID,
                                self.render_interval_ms, None)
            self._set_tray_tip()
            return

    def select_window(self, hwnd: int) -> None:
        if not user32.IsWindow(HWND(hwnd)):
            return
        if self.target != hwnd:
            self._destroy_capture_surface(self.target_surface)
            self.target_surface = None
            self.target_surface_key = None
            self.last_capture_box = None
            self.last_target_boxes = None
        self.target = hwnd
        self.enabled = True
        self._set_tray_tip()
        self.refresh()

    def toggle(self) -> None:
        if not self.target or not user32.IsWindow(HWND(self.target)):
            ctypes.windll.user32.MessageBoxW(self.hwnd, "请先选择反相窗口。", "窗口反相", 0x40)
            self.target = None
            self.enabled = False
            self._destroy_capture_surface(self.target_surface)
            self.target_surface = None
            self.target_surface_key = None
            self.last_capture_box = None
            self.last_target_boxes = None
            self._set_tray_tip()
            return
        self.enabled = not self.enabled
        self._set_tray_tip()
        self.refresh()

    @staticmethod
    def _destroy_capture_surface(surface: Optional[CaptureSurface]) -> None:
        if not surface:
            return
        if surface.dc:
            gdi32.SelectObject(surface.dc, surface.old_bitmap)
            if surface.bitmap:
                gdi32.DeleteObject(surface.bitmap)
            gdi32.DeleteDC(surface.dc)

    def _dpi_signature(self, target: int) -> tuple[int, int]:
        monitor_dpi = _monitor_dpi(target)
        target_dpi = int(user32.GetDpiForWindow(HWND(target)) or monitor_dpi)
        return monitor_dpi, target_dpi

    def _process_name(self, hwnd: int) -> str:
        process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(HWND(hwnd), ctypes.byref(process_id))
        cached = self.process_name_cache.get(hwnd)
        if cached is not None and cached[0] == process_id.value:
            return cached[1]
        process = kernel32.OpenProcess(0x1000, False, process_id.value)
        name = ""
        if process:
            buffer = ctypes.create_unicode_buffer(512)
            length = wintypes.DWORD(len(buffer))
            if kernel32.QueryFullProcessImageNameW(process, 0, buffer,
                                                   ctypes.byref(length)):
                name = buffer.value.rsplit("\\", 1)[-1].lower()
            kernel32.CloseHandle(process)
        self.process_name_cache[hwnd] = (process_id.value, name)
        return name

    @staticmethod
    def _window_exstyle(hwnd: int) -> int:
        return int(user32.GetWindowLongPtrW(HWND(hwnd), GWL_EXSTYLE)) & 0xFFFFFFFF

    def _is_transient_shell_occluder(self, hwnd: int,
                                      box: Optional[Box] = None) -> bool:
        """Ignore the oversized transparent host used by Windows Snap Layouts."""
        if not box:
            box = _rect_for(hwnd)
        if not box:
            return False
        _, class_name = _window_title(hwnd)
        class_name = class_name.lower()
        virtual = _virtual_screen()
        near_top = box.top <= virtual.top + 32
        large_host = (box.width >= max(600, int(virtual.width * 0.70))
                      or box.height >= max(300, int(virtual.height * 0.35)))
        if not near_top or not large_host:
            return False

        exstyle = self._window_exstyle(hwnd)
        xaml_host = class_name.startswith("xamlexplorerhostislandwindow")
        if xaml_host and exstyle & WS_EX_NOREDIRECTIONBITMAP:
            return True

        shell_process = self._process_name(hwnd) in {
            "explorer.exe", "shellexperiencehost.exe",
            "startmenuexperiencehost.exe",
        }
        if (shell_process and exstyle & WS_EX_NOREDIRECTIONBITMAP
                and exstyle & WS_EX_TOOLWINDOW and exstyle & WS_EX_TOPMOST):
            return True

        # Depending on the Windows build, Snap Layouts can be hosted by a
        # CoreWindow in Explorer or ShellExperienceHost rather than the XAML
        # island class. Restrict this fallback to a system process and a
        # non-activating composition window to avoid skipping real app windows.
        return bool(shell_process
                    and class_name in {"windows.ui.core.corewindow", "applicationframewindow"}
                    and exstyle & WS_EX_NOACTIVATE
                    and exstyle & WS_EX_NOREDIRECTIONBITMAP)

    def _owned_windows_above(self, target: int,
                             order: Optional[list[int]] = None) -> list[int]:
        """Find visible owned popups (menus/dialogs) above the target."""
        order = order or self._z_order_windows()
        try:
            target_index = order.index(target)
        except ValueError:
            return []
        own_hosts = {_handle(item.host) for item in self.overlays if item.host}
        result: list[int] = []
        for hwnd in order[:target_index]:
            if hwnd in own_hosts or hwnd == _handle(self.hwnd):
                continue
            if not _is_owned_by(hwnd, target):
                continue
            if not user32.IsWindowVisible(HWND(hwnd)) or user32.IsIconic(HWND(hwnd)):
                continue
            if _is_cloaked(hwnd):
                continue
            if self._is_transient_shell_occluder(hwnd):
                continue
            if _rect_for(hwnd):
                result.append(hwnd)
        return result

    def _visible_boxes(self, target: int, target_box: Optional[Box] = None) -> list[Box]:
        target_box = target_box or _rect_for(target)
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
            if self._is_transient_shell_occluder(hwnd, occluder):
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

    def _render_target(self, target: int, physical_box: Box,
                       screen_dc: HDC, output_dc: HDC) -> bool:
        """Render a target window at physical size, compensating DPI-unaware apps."""
        monitor_dpi = _monitor_dpi(target)
        target_dpi = int(user32.GetDpiForWindow(HWND(target)) or monitor_dpi)
        scale = target_dpi / float(monitor_dpi or 96)
        render_width = max(1, int(round(physical_box.width * scale)))
        render_height = max(1, int(round(physical_box.height * scale)))

        render_dc = gdi32.CreateCompatibleDC(screen_dc)
        render_bitmap = gdi32.CreateCompatibleBitmap(screen_dc, render_width, render_height)
        if not render_dc or not render_bitmap:
            if render_dc:
                gdi32.DeleteDC(render_dc)
            return False
        old_bitmap = gdi32.SelectObject(render_dc, render_bitmap)
        try:
            printed = user32.PrintWindow(HWND(target), render_dc, 2)
            if not printed:
                printed = user32.PrintWindow(HWND(target), render_dc, 0)
            if not printed:
                return False
            if render_width == physical_box.width and render_height == physical_box.height:
                return bool(gdi32.BitBlt(output_dc, 0, 0, physical_box.width,
                                         physical_box.height, render_dc, 0, 0, SRCCOPY))
            gdi32.SetStretchBltMode(output_dc, STRETCH_HALFTONE)
            return bool(gdi32.StretchBlt(output_dc, 0, 0, physical_box.width,
                                         physical_box.height, render_dc, 0, 0,
                                         render_width, render_height, SRCCOPY))
        finally:
            gdi32.SelectObject(render_dc, old_bitmap)
            gdi32.DeleteObject(render_bitmap)
            gdi32.DeleteDC(render_dc)

    def _capture_window(self, target: int, capture_box: Box,
                        screen_dc: HDC) -> Optional[CaptureSurface]:
        source_dc = gdi32.CreateCompatibleDC(screen_dc)
        source_bitmap = gdi32.CreateCompatibleBitmap(screen_dc,
                                                     capture_box.width,
                                                     capture_box.height)
        if not source_dc or not source_bitmap:
            if source_dc:
                gdi32.DeleteDC(source_dc)
            if source_bitmap:
                gdi32.DeleteObject(source_bitmap)
            return None
        old_source_bitmap = gdi32.SelectObject(source_dc, source_bitmap)
        if not self._render_target(target, capture_box, screen_dc, source_dc):
            gdi32.SelectObject(source_dc, old_source_bitmap)
            gdi32.DeleteObject(source_bitmap)
            gdi32.DeleteDC(source_dc)
            return None
        return CaptureSurface(source_dc, source_bitmap, old_source_bitmap,
                              capture_box, self._dpi_signature(target))

    def refresh(self) -> None:
        if not self.enabled or not self.target or not user32.IsWindow(HWND(self.target)):
            if self.target and not user32.IsWindow(HWND(self.target)):
                self.target = None
                self.enabled = False
                self._destroy_capture_surface(self.target_surface)
                self.target_surface = None
                self.target_surface_key = None
                self.last_capture_box = None
                self.last_target_boxes = None
                self._set_tray_tip()
            for item in self.overlays:
                item.hide()
            return
        capture_box = _window_rect_for(self.target)
        visible_box = _rect_for(self.target)
        if not capture_box or not visible_box:
            for item in self.overlays:
                item.hide()
            return
        # Capture from the full Win32 rect, but place overlays against the DWM
        # visible bounds. This removes invisible resize-border offsets while
        # retaining correct content when the window crosses the left/top edge.
        boxes = self._visible_boxes(self.target, visible_box)
        boxes_snapshot = tuple(boxes)
        boxes_changed = self.last_target_boxes != boxes_snapshot
        order = self._z_order_windows()
        owned_windows = self._owned_windows_above(self.target, order)

        # During a mouse move/drag loop some applications return a partially
        # painted frame from PrintWindow. Reuse the last complete bitmap while
        # only the window position or occlusion changes; the next unchanged
        # frame refreshes it normally. This keeps the effect continuous without
        # hiding half of the overlay during a drag.
        dpi_signature = self._dpi_signature(self.target)
        surface_key = (capture_box.width, capture_box.height,
                       dpi_signature[0], dpi_signature[1])
        position_changed = bool(
            self.last_capture_box
            and (capture_box.left != self.last_capture_box.left
                 or capture_box.top != self.last_capture_box.top)
        )

        if not boxes and not owned_windows:
            for item in self.overlays:
                item.hide()
            self.last_capture_box = capture_box
            self.last_target_boxes = boxes_snapshot
            return

        screen_dc = user32.GetDC(None)
        if not screen_dc:
            return
        popup_surfaces: list[CaptureSurface] = []
        try:
            target_surface: Optional[CaptureSurface] = None
            if boxes:
                target_surface = self.target_surface
                need_capture = (
                    target_surface is None
                    or self.target_surface_key != surface_key
                    or (not position_changed and not boxes_changed)
                )
                if need_capture:
                    fresh_surface = self._capture_window(self.target, capture_box,
                                                         screen_dc)
                    if fresh_surface:
                        self._destroy_capture_surface(target_surface)
                        target_surface = fresh_surface
                        self.target_surface = fresh_surface
                        self.target_surface_key = surface_key
                    elif target_surface is None or self.target_surface_key != surface_key:
                        for item in self.overlays:
                            item.hide()
                        self.last_capture_box = capture_box
                        self.last_target_boxes = boxes_snapshot
                        return
                if target_surface:
                    # The bitmap pixels are relative to the window frame, so
                    # use the current frame origin even when reusing it after a
                    # pure move.
                    regions: list[tuple[Box, HDC, Box]] = [
                        (box, target_surface.dc, capture_box) for box in boxes
                    ]
                else:
                    regions = []
            else:
                regions = []

            # Owned top-level popups (for example a browser context menu) are
            # separate windows and therefore absent from PrintWindow(target).
            # Capture each one independently and keep its rectangle out of the
            # target's visible boxes so the two overlays do not overlap.
            for popup in owned_windows:
                popup_capture_box = _window_rect_for(popup)
                popup_visible_box = _rect_for(popup)
                if not popup_capture_box or not popup_visible_box:
                    continue
                popup_boxes = self._visible_boxes(popup, popup_visible_box)
                if not popup_boxes:
                    continue
                popup_surface = self._capture_window(popup, popup_capture_box,
                                                     screen_dc)
                if not popup_surface:
                    continue
                popup_surfaces.append(popup_surface)
                regions.extend((box, popup_surface.dc, popup_capture_box)
                               for box in popup_boxes)

            while len(self.overlays) < len(regions):
                try:
                    self.overlays.append(Overlay(self))
                except (OSError, RuntimeError):
                    break
            for index, item in enumerate(self.overlays):
                if index < len(regions):
                    box, source_dc, source_origin = regions[index]
                    item.set_box(box)
                    item.update_pixels(source_dc, source_origin)
                else:
                    item.hide()
            self.last_capture_box = capture_box
            self.last_target_boxes = boxes_snapshot
        finally:
            for popup_surface in popup_surfaces:
                self._destroy_capture_surface(popup_surface)
            user32.ReleaseDC(None, screen_dc)

    def shutdown(self) -> None:
        if not self.running:
            return
        self.running = False
        user32.KillTimer(self.hwnd, self.TIMER_ID)
        self._destroy_capture_surface(self.target_surface)
        self.target_surface = None
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
