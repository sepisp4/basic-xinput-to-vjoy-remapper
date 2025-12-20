import json
import math
import os
import sys
import pyvjoy
from hidhide_handler import HidHideHandler

DEFAULT_PROFILE = "mapping_profile.json"

VJOY_AXES = {
    "X": pyvjoy.HID_USAGE_X, "Y": pyvjoy.HID_USAGE_Y, "Z": pyvjoy.HID_USAGE_Z,
    "RX": pyvjoy.HID_USAGE_RX, "RY": pyvjoy.HID_USAGE_RY, "RZ": pyvjoy.HID_USAGE_RZ,
    "SL0": pyvjoy.HID_USAGE_SL0, "SL1": pyvjoy.HID_USAGE_SL1,
}

class WindingStickLogic:
    def __init__(self):
        self.current_winding_angle = 0.0
        self.previous_stick_pos = (0.0, 0.0)

    def process(self, stick_x, stick_y, dt, config):
        try:
            w_range = float(config.get("range", 900.0))
            buffer = float(config.get("buffer", 45.0))
            unwind_rate = float(config.get("unwind", 1800.0))
        except: return 0.0
        sx, sy = stick_x / 32768.0, stick_y / 32768.0
        mag = math.sqrt(sx**2 + sy**2)
        if mag > 0.1 and self.previous_stick_pos != (0.0, 0.0):
            current_angle = math.atan2(-sx, sy) * 180.0 / math.pi
            prev_angle = math.atan2(-self.previous_stick_pos[0], self.previous_stick_pos[1]) * 180.0 / math.pi
            diff = (current_angle - prev_angle + 180) % 360 - 180
            self.current_winding_angle += diff * mag
        if mag < 0.95:
            unwind_factor = 1.0 - mag
            unwind_amt = unwind_rate * unwind_factor * dt
            if abs(unwind_amt) >= abs(self.current_winding_angle): self.current_winding_angle = 0.0
            else: self.current_winding_angle -= unwind_amt * (1.0 if self.current_winding_angle > 0 else -1.0)
        max_angle = (w_range / 2.0) + buffer
        self.current_winding_angle = max(min(self.current_winding_angle, max_angle), -max_angle)
        output = self.current_winding_angle * 2.0 / w_range
        self.previous_stick_pos = (sx, sy) if mag > 0.1 else (0.0, 0.0)
        return max(-1.0, min(1.0, output))

class MappingEngine:
    def __init__(self, vjoy_device_id=1):
        self.vjoy_active = False
        try:
            self.vjoy_device = pyvjoy.VJoyDevice(vjoy_device_id)
            self.vjoy_active = True
        except Exception as e:
            print(f"vJoy Init Failed: {e}")
            self.vjoy_device = None

        self.config = self.load_config()
        self.winding_logic = WindingStickLogic()
        self.hidhide = HidHideHandler(self.config.get("hidhide_path", ""))
        
        # Live Data for Viewer
        self.latest_output = {"axes": {}, "buttons": []}
        
    def load_config(self):
        config = self.get_default_config()
        if os.path.exists(DEFAULT_PROFILE):
            try:
                with open(DEFAULT_PROFILE, "r") as f:
                    loaded = json.load(f)
                    self._recursive_update(config, loaded)
            except: pass
        return config

    def _recursive_update(self, default, loaded):
        for key, value in loaded.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self._recursive_update(default[key], value)
            else: default[key] = value

    def save_config(self):
        self.config["hidhide_path"] = self.hidhide.cli_path
        with open(DEFAULT_PROFILE, "w") as f:
            json.dump(self.config, f, indent=4)
        print("Configuration Saved.")

    def apply_hiding(self):
        if not self.hidhide.is_installed(): return
        self.hidhide.whitelist_application(sys.executable)
        devices = self.config.get("hidden_devices", [])
        if devices: self.hidhide.hide_devices(devices)
        self.hidhide.set_cloaking(True)
        print("HidHide: Devices Hidden.")

    def disable_hiding(self):
        if not self.hidhide.is_installed(): return
        self.hidhide.set_cloaking(False)
        print("HidHide: Cloaking Disabled.")

    def reset_to_defaults(self):
        self.config = self.get_default_config()
        self.save_config()

    def unmap_all(self):
        for btn in self.config["buttons"]: self.config["buttons"][btn] = "None"
        for axis in self.config["axes"]: self.config["axes"][axis]["target"] = "None"
        self.save_config()

    def get_default_config(self):
        return {
            "global_settings": { "update_rate": 1000 },
            "hidhide_path": r"C:\Program Files\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe",
            "hidden_devices": [],
            "use_hidhide": True,
            "scripts": {
                "winding_steering": { "enabled_for": "Disabled", "target_axis": "X", "range": "900", "buffer": "45", "unwind": "1800" },
                "range_modifier": { "enabled": False, "modifier_key": "X", "mute_key": False, "modified_axis": "X", "press_mult": 1.0, "release_mult": 0.5 },
                "auto_clutch": { "enabled": False, "upshift_btn": "RB", "downshift_btn": "LB", "throttle_axis": "RZ", "clutch_axis": "RY", "auto_blip": False, "auto_lift": False }
            },
            "buttons": {
                "A": 1, "B": 2, "X": 3, "Y": 4, "LB": 5, "RB": 6, "Back": 7, "Start": 8, 
                "LS_Click": 9, "RS_Click": 10, "DPad_Up": 11, "DPad_Down": 12, "DPad_Left": 13, "DPad_Right": 14
            },
            "axes": {
                "LT": {"target": "Z", "dz_in": 0.0, "dz_out": 0.0, "start": -1.0, "end": 1.0, "lin": 0},
                "RT": {"target": "RZ", "dz_in": 0.0, "dz_out": 0.0, "start": -1.0, "end": 1.0, "lin": 0},
                "LX": {"target": "X", "dz_in": 0.0, "dz_out": 0.0, "anti_dz": 0.0, "lin": 0, "inv": False, "square": False},
                "LY": {"target": "Y", "dz_in": 0.0, "dz_out": 0.0, "anti_dz": 0.0, "lin": 0, "inv": False, "square": False},
                "RX": {"target": "RX", "dz_in": 0.0, "dz_out": 0.0, "anti_dz": 0.0, "lin": 0, "inv": False, "square": False},
                "RY": {"target": "RY", "dz_in": 0.0, "dz_out": 0.0, "anti_dz": 0.0, "lin": 0, "inv": False, "square": False}
            }
        }

    def apply_linearity(self, norm_val, linearity):
        if linearity == 0: return norm_val
        if linearity > 0: curved_val = math.sin(norm_val * (math.pi / 2))
        else: curved_val = 1.0 - math.cos(norm_val * (math.pi / 2))
        strength = abs(linearity) / 100.0
        return (norm_val * (1.0 - strength)) + (curved_val * strength)

    def apply_deadzone_stick(self, value, dz_in, dz_out, anti_dz, linearity, invert=False):
        sign = 1 if value >= 0 else -1
        val_abs = abs(value)
        if val_abs < dz_in: return 0.0
        if val_abs > (1.0 - dz_out): val_abs = 1.0
        else: val_abs = (val_abs - dz_in) / ((1.0 - dz_out) - dz_in)
        val_abs = self.apply_linearity(val_abs, linearity)
        if val_abs > 0: val_abs = anti_dz + (val_abs * (1.0 - anti_dz))
        result = val_abs * sign
        return -result if invert else result

    def apply_deadzone_trigger(self, value, dz_in, dz_out, out_start, out_end, linearity):
        if value < dz_in: return out_start
        if value > (1.0 - dz_out): norm_val = 1.0
        else: norm_val = (value - dz_in) / ((1.0 - dz_out) - dz_in)
        norm_val = self.apply_linearity(norm_val, linearity)
        return out_start + (norm_val * (out_end - out_start))

    def squarify(self, val_x, val_y):
        nx, ny = val_x / 32768.0, val_y / 32768.0
        mag = math.sqrt(nx*nx + ny*ny)
        if mag < 0.01: return nx, ny
        max_c = max(abs(nx), abs(ny))
        if max_c < 0.001: return nx, ny
        scale = mag / max_c
        return max(-1.0, min(1.0, nx * scale)), max(-1.0, min(1.0, ny * scale))

    def update_vjoy(self, xinput_state, dt):
        if not self.vjoy_active: return
        
        gamepad = xinput_state.Gamepad
        xinput_masks = {
            "A": 0x1000, "B": 0x2000, "X": 0x4000, "Y": 0x8000,
            "LB": 0x0100, "RB": 0x0200, "Back": 0x0020, "Start": 0x0010,
            "LS_Click": 0x0040, "RS_Click": 0x0080,
            "DPad_Up": 0x0001, "DPad_Down": 0x0002, "DPad_Left": 0x0004, "DPad_Right": 0x0008
        }
        output_axes_values = {} 
        axes_conf = self.config["axes"]

        lx, ly = gamepad.sThumbLX, gamepad.sThumbLY
        if axes_conf["LX"].get("square", False): lx_proc, ly_proc = self.squarify(lx, ly)
        else: lx_proc, ly_proc = lx / 32768.0, ly / 32768.0
        
        conf_lx = axes_conf["LX"]
        if conf_lx["target"] != "None": output_axes_values[conf_lx["target"]] = self.apply_deadzone_stick(lx_proc, conf_lx["dz_in"], conf_lx["dz_out"], conf_lx["anti_dz"], conf_lx["lin"], conf_lx.get("inv", False))
        conf_ly = axes_conf["LY"]
        if conf_ly["target"] != "None": output_axes_values[conf_ly["target"]] = self.apply_deadzone_stick(ly_proc, conf_ly["dz_in"], conf_ly["dz_out"], conf_ly["anti_dz"], conf_ly["lin"], conf_ly.get("inv", False))

        rx, ry = gamepad.sThumbRX, gamepad.sThumbRY
        if axes_conf["RX"].get("square", False): rx_proc, ry_proc = self.squarify(rx, ry)
        else: rx_proc, ry_proc = rx / 32768.0, ry / 32768.0
        conf_rx = axes_conf["RX"]
        if conf_rx["target"] != "None": output_axes_values[conf_rx["target"]] = self.apply_deadzone_stick(rx_proc, conf_rx["dz_in"], conf_rx["dz_out"], conf_rx["anti_dz"], conf_rx["lin"], conf_rx.get("inv", False))
        conf_ry = axes_conf["RY"]
        if conf_ry["target"] != "None": output_axes_values[conf_ry["target"]] = self.apply_deadzone_stick(ry_proc, conf_ry["dz_in"], conf_ry["dz_out"], conf_ry["anti_dz"], conf_ry["lin"], conf_ry.get("inv", False))

        for axis, raw_val in [("LT", gamepad.bLeftTrigger), ("RT", gamepad.bRightTrigger)]:
            conf = axes_conf[axis]
            if conf["target"] != "None": output_axes_values[conf["target"]] = self.apply_deadzone_trigger(raw_val/255.0, conf["dz_in"], conf["dz_out"], conf["start"], conf["end"], conf["lin"])

        w_conf = self.config["scripts"].get("winding_steering", {})
        if w_conf.get("enabled_for", "Disabled") != "Disabled":
            target = w_conf.get("target_axis", "X")
            if w_conf["enabled_for"] == "Left Stick": sx, sy = gamepad.sThumbLX, gamepad.sThumbLY
            else: sx, sy = gamepad.sThumbRX, gamepad.sThumbRY
            winding_val = self.winding_logic.process(sx, sy, dt, w_conf)
            if target != "None": output_axes_values[target] = winding_val

        rm_conf = self.config["scripts"].get("range_modifier", {})
        mute_key_active = False 
        if rm_conf.get("enabled", False):
            mod_key = rm_conf.get("modifier_key", "X")
            target_axis = rm_conf.get("modified_axis", "X")
            is_mod_pressed = False
            if mod_key in xinput_masks: is_mod_pressed = (gamepad.wButtons & xinput_masks[mod_key]) != 0
            mult = float(rm_conf.get("press_mult", 1.0)) if is_mod_pressed else float(rm_conf.get("release_mult", 0.5))
            if target_axis in output_axes_values:
                new_val = output_axes_values[target_axis] * mult
                output_axes_values[target_axis] = max(-1.0, min(1.0, new_val))
            if rm_conf.get("mute_key", False): mute_key_active = True; muted_btn_name = mod_key

        ac_conf = self.config["scripts"].get("auto_clutch", {})
        if ac_conf.get("enabled", False):
            up_btn = ac_conf.get("upshift_btn", "RB")
            dn_btn = ac_conf.get("downshift_btn", "LB")
            is_up = (gamepad.wButtons & xinput_masks.get(up_btn, 0)) != 0
            is_dn = (gamepad.wButtons & xinput_masks.get(dn_btn, 0)) != 0
            if is_up or is_dn:
                output_axes_values[ac_conf.get("clutch_axis", "RY")] = 1.0
                if is_dn and ac_conf.get("auto_blip", False): output_axes_values[ac_conf.get("throttle_axis", "RZ")] = 1.0
                if is_up and ac_conf.get("auto_lift", False): output_axes_values[ac_conf.get("throttle_axis", "RZ")] = -1.0

        # --- Capture State for Viewer (AND Send to vJoy) ---
        active_buttons_list = []
        for name, vjoy_btn_id in self.config["buttons"].items():
            if vjoy_btn_id == "None" or name not in xinput_masks: continue
            if mute_key_active and name == muted_btn_name:
                self.vjoy_device.set_button(int(vjoy_btn_id), 0)
                continue
            is_pressed = (gamepad.wButtons & xinput_masks[name]) != 0
            self.vjoy_device.set_button(int(vjoy_btn_id), 1 if is_pressed else 0)
            if is_pressed: active_buttons_list.append(int(vjoy_btn_id))

        # Update viewer data
        self.latest_output = {
            "axes": output_axes_values.copy(),
            "buttons": sorted(active_buttons_list)
        }

        def float_to_vjoy(f_val): return int((max(-1.0, min(1.0, f_val)) + 1.0) * 16383.5 + 1)
        for axis_name, val in output_axes_values.items():
            if axis_name in VJOY_AXES: self.vjoy_device.set_axis(VJOY_AXES[axis_name], float_to_vjoy(val))