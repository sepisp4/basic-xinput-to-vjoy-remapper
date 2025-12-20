import ctypes
from ctypes import windll, wintypes

# --- XInput Structures ---
class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", wintypes.WORD),
        ("bLeftTrigger", ctypes.c_ubyte),  # CHANGED: wintypes.BYTE -> ctypes.c_ubyte (Fixes 50% cutoff)
        ("bRightTrigger", ctypes.c_ubyte), # CHANGED: wintypes.BYTE -> ctypes.c_ubyte (Fixes 50% cutoff)
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]

class XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", wintypes.DWORD),
        ("Gamepad", XINPUT_GAMEPAD),
    ]

# --- Load DLL ---
try:
    xinput_dll = windll.xinput1_4
except OSError:
    try:
        xinput_dll = windll.xinput9_1_0
    except OSError:
        xinput_dll = windll.xinput1_3

xinput_dll.XInputGetState.argtypes = [wintypes.DWORD, ctypes.POINTER(XINPUT_STATE)]
xinput_dll.XInputGetState.restype = wintypes.DWORD

ERROR_SUCCESS = 0

class XInputHandler:
    def __init__(self):
        pass

    def get_state(self, user_index):
        state = XINPUT_STATE()
        result = xinput_dll.XInputGetState(user_index, ctypes.byref(state))
        if result == ERROR_SUCCESS:
            return state
        return None

    def is_button_pressed(self, state):
        if state is None: return False
        return state.Gamepad.wButtons > 0