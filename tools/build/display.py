"""Set and record a real 1920x1080 Windows CI desktop before native tests."""
import ctypes
from ctypes import wintypes as w
import json
import os
from pathlib import Path


class DisplayMode(ctypes.Structure):
    _fields_ = [('device', w.WCHAR * 32), ('spec', w.WORD), ('driver', w.WORD),
                ('size', w.WORD), ('extra', w.WORD), ('fields', w.DWORD),
                ('position', w.POINT), ('orientation', w.DWORD), ('fixed_output', w.DWORD),
                ('color', ctypes.c_short), ('duplex', ctypes.c_short),
                ('y_resolution', ctypes.c_short), ('tt_option', ctypes.c_short),
                ('collate', ctypes.c_short), ('form', w.WCHAR * 32), ('log_pixels', w.WORD),
                ('bits', w.DWORD), ('width', w.DWORD), ('height', w.DWORD),
                ('flags', w.DWORD), ('frequency', w.DWORD), ('icm_method', w.DWORD),
                ('icm_intent', w.DWORD), ('media', w.DWORD), ('dither', w.DWORD),
                ('reserved1', w.DWORD), ('reserved2', w.DWORD),
                ('panning_width', w.DWORD), ('panning_height', w.DWORD)]


def main():
    if os.name != 'nt':
        raise SystemExit('This desktop setup runs on Windows only.')
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise SystemExit('This helper changes a dedicated GitHub Actions desktop only. For local verification use RENPY_ACCEPTANCE_WINDOWED=1; it adjusts only the test process and window.')
    user = ctypes.WinDLL('user32', use_last_error=True)
    enum = user.EnumDisplaySettingsW
    enum.argtypes = [w.LPCWSTR, w.DWORD, ctypes.POINTER(DisplayMode)]
    enum.restype = w.BOOL
    change = user.ChangeDisplaySettingsW
    change.argtypes = [ctypes.POINTER(DisplayMode), w.DWORD]
    change.restype = w.LONG
    modes, candidate = [], None
    index = 0
    while True:
        mode = DisplayMode(size=ctypes.sizeof(DisplayMode))
        if not enum(None, index, ctypes.byref(mode)):
            break
        modes.append([mode.width, mode.height, mode.bits, mode.frequency])
        if (mode.width, mode.height, mode.bits) == (1920, 1080, 32):
            candidate = mode
        index += 1
    if candidate is None:
        raise SystemExit(f'1920x1080 desktop mode unavailable: {modes}')
    result = change(ctypes.byref(candidate), 0)
    current = DisplayMode(size=ctypes.sizeof(DisplayMode))
    if result != 0 or not enum(None, 0xFFFFFFFF, ctypes.byref(current)):
        raise SystemExit(f'Display change failed: {result}')
    if (current.width, current.height) != (1920, 1080):
        raise SystemExit(f'Unexpected desktop size: {current.width}x{current.height}')
    report = {'desktop_pixels': [current.width, current.height], 'bits_per_pixel': current.bits,
              'frequency_hz': current.frequency, 'display_change_result': result, 'available_modes': modes,
              'scope': 'Windows CI desktop only; ordinary-PC 100%/150% DPI remains human review'}
    Path('reports').mkdir(exist_ok=True)
    Path('reports/display.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('Windows native-test desktop:', report['desktop_pixels'])


if __name__ == '__main__':
    main()
