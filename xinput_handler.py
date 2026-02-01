import ctypes
from ctypes import windll, wintypes

# --- XInput Structures ---
class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", wintypes.WORD),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
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

# --- Load DLL (Robust Logic) ---
xinput_dll = None
dll_name = "None"

# Try loading latest to oldest
dll_list = ["xinput1_4", "xinput9_1_0", "xinput1_3"]

for lib in dll_list:
    try:
        xinput_dll = getattr(windll, lib)
        dll_name = lib
        print(f"XInputHandler: Successfully loaded {lib}.dll")
        break
    except Exception as e:
        continue

if not xinput_dll:
    print("XInputHandler CRITICAL: Could not load any XInput DLL.")
else:
    # Define argument types to prevent ctypes confusion
    xinput_dll.XInputGetState.argtypes = [wintypes.DWORD, ctypes.POINTER(XINPUT_STATE)]
    xinput_dll.XInputGetState.restype = wintypes.DWORD

ERROR_SUCCESS = 0
ERROR_DEVICE_NOT_CONNECTED = 1167

class XInputHandler:
    def __init__(self):
        # We only print the connected message once per port to avoid spamming console
        self._logged_connections = set()

    def get_state(self, user_index):
        if not xinput_dll:
            return None

        state = XINPUT_STATE()
        result = xinput_dll.XInputGetState(user_index, ctypes.byref(state))
        
        if result == ERROR_SUCCESS:
            # Debug logging (Only prints once when a device is first seen)
            if user_index not in self._logged_connections:
                print(f"XInputHandler: Port {user_index} CONNECTED. (Packet: {state.dwPacketNumber})")
                self._logged_connections.add(user_index)
            return state
        
        elif result == ERROR_DEVICE_NOT_CONNECTED:
            # If device disconnects, remove from log so we notify if it reconnects
            if user_index in self._logged_connections:
                print(f"XInputHandler: Port {user_index} Disconnected.")
                self._logged_connections.remove(user_index)
            return None
            
        else:
            # Some other weird error (e.g. 5 = Access Denied by HidHide)
            print(f"XInputHandler: Port {user_index} Error Code {result}")
            return None

    def is_button_pressed(self, state):
        """
        Checks if ANY digital button is pressed. 
        Ignores Triggers and Analog Sticks.
        """
        if state is None:
            return False
        return state.Gamepad.wButtons > 0