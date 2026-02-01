import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import sys
import webbrowser
import pythoncom 
import winreg 
import ctypes 

from xinput_handler import XInputHandler
from mapping_engine import MappingEngine

# Lists
VJOY_BUTTONS = ["None"] + [str(i) for i in range(1, 129)]
VJOY_AXES_LIST = ["None", "X", "Y", "Z", "RX", "RY", "RZ", "SL0", "SL1"]
STICK_OPTIONS = ["Disabled", "Left Stick", "Right Stick"]
XINPUT_BUTTONS = ["A", "B", "X", "Y", "LB", "RB", "Back", "Start", "LS_Click", "RS_Click", "DPad_Up", "DPad_Down", "DPad_Left", "DPad_Right"]
SCRIPT_AXIS_OPTIONS = ["X", "Y", "Z", "RX", "RY", "RZ", "SL0", "SL1"]

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

# --- INPUT VIEWER ---
class InputViewerWindow(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.title("vJoy Input Viewer")
        self.geometry("300x450")
        self.app = app
        self.mapper = app.mapper
        self.lbl_status = tk.Label(self, text="Status: ???", font=("Arial", 12, "bold"))
        self.lbl_status.pack(pady=10)
        frame_axes = tk.LabelFrame(self, text="Axes Output (-1.0 to 1.0)", padx=10, pady=5)
        frame_axes.pack(fill="x", padx=10)
        self.axis_labels = {}
        self.axis_names = ["X", "Y", "Z", "RX", "RY", "RZ", "SL0", "SL1"]
        for ax in self.axis_names:
            row = tk.Frame(frame_axes); row.pack(fill="x", pady=1)
            tk.Label(row, text=f"{ax}:", width=5, anchor="w", font=("Consolas", 10)).pack(side="left")
            l = tk.Label(row, text="0.000", fg="blue", font=("Consolas", 10)); l.pack(side="right")
            self.axis_labels[ax] = l
        frame_btns = tk.LabelFrame(self, text="Pressed Buttons", padx=10, pady=5)
        frame_btns.pack(fill="both", expand=True, padx=10, pady=10)
        self.lbl_btns = tk.Label(frame_btns, text="None", wraplength=250, justify="center", font=("Consolas", 10))
        self.lbl_btns.pack()
        self.update_loop()
    def update_loop(self):
        if not self.winfo_exists(): return
        if self.app.is_running:
            self.lbl_status.config(text="Status: MAPPING RUNNING", fg="green")
            data = self.mapper.latest_output
            current_axes = data.get("axes", {})
            for ax in self.axis_names: self.axis_labels[ax].config(text=f"{current_axes.get(ax, 0.0): .3f}")
            btns = data.get("buttons", [])
            self.lbl_btns.config(text=(", ".join(map(str, btns)) if btns else "None"))
        else:
            self.lbl_status.config(text="Status: STOPPED (No Data)", fg="red")
            for ax in self.axis_names: self.axis_labels[ax].config(text="0.000")
            self.lbl_btns.config(text="-")
        self.after(50, self.update_loop) 

# --- ERROR & WARNING WINDOWS ---
class VJoyMissingWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("vJoy Not Detected")
        self.geometry("400x200")
        self.parent = parent
        self.transient(parent)
        self.focus_set()
        tk.Label(self, text="Critical Error: vJoy Driver Not Detected", fg="red", font=("Arial", 12, "bold")).pack(pady=10)
        tk.Label(self, text="The program cannot map inputs without vJoy.\nPlease install it to continue.\nOnce installed, open 'configure vjoy' and set the number of buttons to at least 14", justify="center").pack(pady=5)
        btn_frame = tk.Frame(self); btn_frame.pack(side="bottom", fill="x", pady=20)
        tk.Button(btn_frame, text="Download vJoy", command=self.download).pack(side="left", padx=20)
        tk.Button(btn_frame, text="Continue Anyway (Demo Mode)", command=self.destroy).pack(side="left", padx=20)
        tk.Button(btn_frame, text="Close Program", command=self.close_app).pack(side="right", padx=20)
        self.protocol("WM_DELETE_WINDOW", self.close_app)
    def download(self): webbrowser.open("https://sourceforge.net/projects/vjoystick/files/Beta%202.x/2.1.9.1-160719/")
    def close_app(self): self.parent.destroy(); sys.exit()

class HidHideWarningWindow(tk.Toplevel):
    def __init__(self, parent, mapper):
        super().__init__(parent)
        self.title("HidHide Issue")
        self.geometry("400x250")
        self.mapper = mapper
        self.transient(parent)
        self.focus_set()
        tk.Label(self, text="HidHide Warning", fg="orange", font=("Arial", 12, "bold")).pack(pady=10)
        tk.Label(self, text="You have 'Hide Physical Controller' enabled,\nbut HidHide is missing or no devices are configured.", justify="center").pack(pady=5)
        tk.Label(self, text="The program will run WITHOUT hiding the device.\nThis may cause double inputs in games.", justify="center", fg="#555").pack(pady=5)
        btn_frame = tk.Frame(self); btn_frame.pack(side="bottom", fill="x", pady=20)
        tk.Button(btn_frame, text="Download HidHide", command=self.download).pack(side="left", padx=20)
        tk.Button(btn_frame, text="Continue Anyway", command=self.continue_run).pack(side="right", padx=20)
    def download(self): webbrowser.open("https://ds4-windows.com/download/hidhide/")
    def continue_run(self): self.mapper.config["use_hidhide"] = False; self.destroy()

# --- CONFIGURATION WINDOWS ---
class HidHideConfigWindow(tk.Toplevel):
    def __init__(self, parent, mapper):
        super().__init__(parent)
        self.title("HidHide Configuration")
        self.geometry("500x550")
        self.mapper = mapper
        self.hidhide = mapper.hidhide
        self.transient(parent)
        self.focus_set()
        
        # Download Button
        tk.Button(self, text="Download HidHide Driver", fg="blue", cursor="hand2",
                  command=lambda: webbrowser.open("https://ds4-windows.com/download/hidhide/")
                  ).pack(pady=10)

        # Path
        tk.Label(self, text="HidHideCLI Path:", font=("Arial", 10, "bold")).pack(pady=(5,5))
        f_path = tk.Frame(self); f_path.pack(fill="x", padx=20)
        self.path_var = tk.StringVar(value=self.hidhide.cli_path)
        self.path_var.trace("w", self.on_path_change)
        tk.Entry(f_path, textvariable=self.path_var).pack(side="left", fill="x", expand=True)
        tk.Button(f_path, text="Browse", command=self.browse_path).pack(side="left", padx=5)
        
        # Instructions
        instr_frame = tk.LabelFrame(self, text="Detection Instructions", padx=10, pady=10)
        instr_frame.pack(fill="x", padx=20, pady=15)
        
        instr_text = (
            "1. UNPLUG your controller from the computer.\n"
            "2. Click 'Start Detection' below.\n"
            "3. You have 10 seconds to PLUG IT BACK IN.\n"
            "4. The tool will automatically find the device instance."
        )
        tk.Label(instr_frame, text=instr_text, justify="left", font=("Arial", 9)).pack(anchor="w")

        self.lbl_status = tk.Label(self, text="Status: Ready", fg="blue", font=("Arial", 11)); self.lbl_status.pack(pady=5)
        self.btn_detect = tk.Button(self, text="Start Detection (10s)", command=self.start_detection_thread, bg="#4CAF50", fg="white", font=("Arial", 11, "bold")); self.btn_detect.pack(pady=5)
        
        # List
        tk.Label(self, text="Hidden Instance Paths:", font=("Arial", 10, "bold")).pack(pady=(20, 5))
        frame_list = tk.Frame(self); frame_list.pack(fill="both", expand=True, padx=20)
        scrollbar = tk.Scrollbar(frame_list); scrollbar.pack(side="right", fill="y")
        self.listbox = tk.Listbox(frame_list, height=6, yscrollcommand=scrollbar.set); self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)
        for dev in self.mapper.config.get("hidden_devices", []): self.listbox.insert("end", dev)
        
        # Buttons
        btn_frame = tk.Frame(self); btn_frame.pack(side="bottom", fill="x", pady=20, padx=20)
        tk.Button(btn_frame, text="Clear List", command=self.clear_list, bg="#ffdddd").pack(side="left")
        tk.Button(btn_frame, text="Save & Close", command=self.save_and_close, width=20).pack(side="right")

    def on_path_change(self, *args): p = self.path_var.get().strip('"').strip("'"); self.hidhide.cli_path = p; self.mapper.config["hidhide_path"] = p
    def browse_path(self):
        f = filedialog.askopenfilename(filetypes=[("HidHideCLI", "HidHideCLI.exe")])
        if f: self.path_var.set(f)
    def clear_list(self): self.listbox.delete(0, "end"); self.mapper.config["hidden_devices"] = []
    def start_detection_thread(self): self.btn_detect.config(state="disabled"); threading.Thread(target=self.detect_logic, daemon=True).start()
    def detect_logic(self):
        self.lbl_status.config(text="Scanning current...", fg="blue")
        before = self.hidhide.get_connected_devices_set()
        for i in range(10, 0, -1): self.lbl_status.config(text=f"PLUG IN CONTROLLER: {i}s", fg="red"); time.sleep(1)
        self.lbl_status.config(text="Scanning new...", fg="blue")
        after = self.hidhide.get_connected_devices_set()
        new = after - before
        if new:
            self.lbl_status.config(text=f"Found {len(new)} devices.", fg="green")
            cur = self.mapper.config.get("hidden_devices", [])
            for d in new: 
                if d not in cur: cur.append(d); self.listbox.insert("end", d)
            self.mapper.config["hidden_devices"] = cur
        else: self.lbl_status.config(text="No new devices.", fg="orange")
        self.btn_detect.config(state="normal")
    def save_and_close(self): self.mapper.save_config(); self.destroy()

class AxisSettingsWindow(tk.Toplevel):
    def __init__(self, parent, title, axis_key, axis_data, is_trigger=False, is_stick=False):
        super().__init__(parent)
        self.title(f"Settings: {title}")
        self.geometry("400x500")
        self.axis_data = axis_data
        self.create_slider("Input Inner Deadzone (0-0.5)", "dz_in", 0.0, 0.5)
        self.create_slider("Input Outer Deadzone (0-0.5)", "dz_out", 0.0, 0.5)
        if is_trigger:
            self.create_slider("Output Start Value (-1 to 1)", "start", -1.0, 1.0)
            self.create_slider("Output End Value (-1 to 1)", "end", -1.0, 1.0)
        else:
            self.create_slider("Output Anti-Deadzone (0-0.5)", "anti_dz", 0.0, 0.5)
        self.create_slider("Linearity (-100 to 100)", "lin", -100, 100, resolution=1)
        if is_stick:
            var_inv = tk.BooleanVar(value=self.axis_data.get("inv", False))
            tk.Checkbutton(self, text="Invert Output", variable=var_inv, command=lambda: self.axis_data.update({"inv": var_inv.get()})).pack(pady=10)
        tk.Button(self, text="Close", command=self.destroy).pack(pady=20)
    def create_slider(self, label_text, key, min_val, max_val, resolution=0.01):
        frame = tk.Frame(self)
        frame.pack(fill="x", padx=20, pady=5)
        tk.Label(frame, text=label_text).pack(anchor="w")
        var = tk.DoubleVar(value=self.axis_data.get(key, 0))
        tk.Scale(frame, from_=min_val, to=max_val, orient="horizontal", variable=var, resolution=resolution, command=lambda v: self.axis_data.update({key: float(v)})).pack(fill="x")

class ProgramSettingsWindow(tk.Toplevel):
    def __init__(self, parent, config_ref):
        super().__init__(parent)
        self.title("Program Settings")
        self.geometry("400x250")
        self.config_ref = config_ref
        tk.Label(self, text="General Options", font=("Arial", 12, "bold")).pack(pady=10)
        frame_rate = tk.Frame(self)
        frame_rate.pack(fill="x", padx=20, pady=10)
        tk.Label(frame_rate, text="Update Rate (Hz)").pack(anchor="w")
        current_rate = self.config_ref["global_settings"].get("update_rate", 1000)
        self.var_rate = tk.IntVar(value=current_rate)
        tk.Scale(frame_rate, from_=60, to=2000, orient="horizontal", variable=self.var_rate, resolution=10, command=self.update_rate).pack(fill="x")
        self.lbl_val = tk.Label(frame_rate, text=f"{current_rate} Hz")
        self.lbl_val.pack(anchor="e")
        tk.Button(self, text="Close", command=self.destroy).pack(side="bottom", pady=20)
    def update_rate(self, val): val = int(val); self.config_ref["global_settings"]["update_rate"] = val; self.lbl_val.config(text=f"{val} Hz")

class WindingSettingsWindow(tk.Toplevel):
    def __init__(self, parent, config_ref):
        super().__init__(parent)
        self.title("Script: Winding Stick Steering")
        self.geometry("450x400")
        if "winding_steering" not in config_ref["scripts"]: config_ref["scripts"]["winding_steering"] = {}
        self.data = config_ref["scripts"]["winding_steering"]
        tk.Label(self, text="Winding Stick Settings", font=("Arial", 12, "bold")).pack(pady=10)
        self.create_dropdown("Enable for:", "enabled_for", STICK_OPTIONS)
        self.create_dropdown("Output to vJoy Axis:", "target_axis", VJOY_AXES_LIST)
        self.create_entry("Winding Range (deg):", "range", "900")
        self.create_entry("Over-Rotation Buffer (deg):", "buffer", "45")
        self.create_entry("Unwind Rate (deg/sec):", "unwind", "1800")
        tk.Button(self, text="Done", command=self.destroy).pack(side="bottom", pady=20)
    def create_dropdown(self, label, key, values):
        f = tk.Frame(self)
        f.pack(fill="x", padx=20, pady=5)
        tk.Label(f, text=label, width=20, anchor="w").pack(side="left")
        var = tk.StringVar(value=self.data.get(key, values[0]))
        cb = ttk.Combobox(f, textvariable=var, values=values, state="readonly"); cb.pack(side="left", fill="x", expand=True)
        cb.bind("<<ComboboxSelected>>", lambda e: self.data.update({key: var.get()}))
    def create_entry(self, label, key, default):
        f = tk.Frame(self); f.pack(fill="x", padx=20, pady=5)
        tk.Label(f, text=label, width=25, anchor="w").pack(side="left")
        var = tk.StringVar(value=str(self.data.get(key, default)))
        entry = tk.Entry(f, textvariable=var); entry.pack(side="left", fill="x", expand=True)
        entry.bind("<KeyRelease>", lambda e: self.data.update({key: var.get()}))

class RangeModifierWindow(tk.Toplevel):
    def __init__(self, parent, config_ref):
        super().__init__(parent)
        self.title("Script: Range Modifier")
        self.geometry("450x400")
        if "range_modifier" not in config_ref["scripts"]: config_ref["scripts"]["range_modifier"] = {}
        self.data = config_ref["scripts"]["range_modifier"]
        tk.Label(self, text="Range Modifier Settings", font=("Arial", 12, "bold")).pack(pady=10)
        var_enabled = tk.BooleanVar(value=self.data.get("enabled", False))
        tk.Checkbutton(self, text="Enable Script", variable=var_enabled, command=lambda: self.data.update({"enabled": var_enabled.get()})).pack(pady=5)
        self.create_dropdown("Modifier Key (XInput):", "modifier_key", XINPUT_BUTTONS)
        var_mute = tk.BooleanVar(value=self.data.get("mute_key", False))
        tk.Checkbutton(self, text="Mute Modifier Key (Don't map to vJoy)", variable=var_mute, command=lambda: self.data.update({"mute_key": var_mute.get()})).pack(pady=5)
        self.create_dropdown("Target vJoy Axis:", "modified_axis", SCRIPT_AXIS_OPTIONS)
        self.create_entry("On-Press Multiplier (0-1):", "press_mult", "1.0")
        self.create_entry("On-Release Multiplier (0-1):", "release_mult", "0.5")
        tk.Button(self, text="Done", command=self.destroy).pack(side="bottom", pady=20)
    def create_dropdown(self, label, key, values):
        f = tk.Frame(self); f.pack(fill="x", padx=20, pady=5)
        tk.Label(f, text=label, width=25, anchor="w").pack(side="left")
        current_val = self.data.get(key, values[0]); var = tk.StringVar(value=current_val)
        cb = ttk.Combobox(f, textvariable=var, values=values, state="readonly"); cb.pack(side="left", fill="x", expand=True)
        cb.bind("<<ComboboxSelected>>", lambda e: self.data.update({key: var.get()}))
    def create_entry(self, label, key, default):
        f = tk.Frame(self); f.pack(fill="x", padx=20, pady=5)
        tk.Label(f, text=label, width=25, anchor="w").pack(side="left")
        var = tk.StringVar(value=str(self.data.get(key, default))); entry = tk.Entry(f, textvariable=var); entry.pack(side="left", fill="x", expand=True)
        entry.bind("<KeyRelease>", lambda e: self.data.update({key: var.get()}))

class AutoClutchSettingsWindow(tk.Toplevel):
    def __init__(self, parent, config_ref):
        super().__init__(parent)
        self.title("Script: Auto-Clutch (Sequential)")
        self.geometry("450x450")
        if "auto_clutch" not in config_ref["scripts"]: config_ref["scripts"]["auto_clutch"] = {}
        self.data = config_ref["scripts"]["auto_clutch"]
        tk.Label(self, text="Auto-Clutch Settings", font=("Arial", 12, "bold")).pack(pady=10)
        var_enabled = tk.BooleanVar(value=self.data.get("enabled", False))
        tk.Checkbutton(self, text="Enable Script", variable=var_enabled, command=lambda: self.data.update({"enabled": var_enabled.get()})).pack(pady=5)
        self.create_dropdown("Upshift Button:", "upshift_btn", XINPUT_BUTTONS)
        self.create_dropdown("Downshift Button:", "downshift_btn", XINPUT_BUTTONS)
        self.create_dropdown("Throttle Axis (vJoy):", "throttle_axis", SCRIPT_AXIS_OPTIONS)
        self.create_dropdown("Clutch Axis (vJoy):", "clutch_axis", SCRIPT_AXIS_OPTIONS)
        var_blip = tk.BooleanVar(value=self.data.get("auto_blip", False))
        tk.Checkbutton(self, text="Auto Blip", variable=var_blip, command=lambda: self.data.update({"auto_blip": var_blip.get()})).pack(pady=5, anchor="w", padx=40)
        var_lift = tk.BooleanVar(value=self.data.get("auto_lift", False))
        tk.Checkbutton(self, text="Auto Lift", variable=var_lift, command=lambda: self.data.update({"auto_lift": var_lift.get()})).pack(pady=5, anchor="w", padx=40)
        tk.Button(self, text="Done", command=self.destroy).pack(side="bottom", pady=20)
    def create_dropdown(self, label, key, values):
        f = tk.Frame(self); f.pack(fill="x", padx=20, pady=5)
        tk.Label(f, text=label, width=25, anchor="w").pack(side="left")
        current_val = self.data.get(key, values[0]); var = tk.StringVar(value=current_val)
        cb = ttk.Combobox(f, textvariable=var, values=values, state="readonly"); cb.pack(side="left", fill="x", expand=True)
        cb.bind("<<ComboboxSelected>>", lambda e: self.data.update({key: var.get()}))

# --- MAIN APP ---
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Basic Xinput to vJoy Remapper")
        self.root.geometry("600x800")
        self.xi = XInputHandler()
        self.mapper = MappingEngine() 
        if not self.mapper.vjoy_active:
            self.root.after(100, lambda: VJoyMissingWindow(self.root))
        self.selected_port = -1
        self.is_running = False
        self.stop_event = threading.Event()
        self.frame_step1 = tk.Frame(root)
        self.frame_step2 = tk.Frame(root)
        self.frame_step3 = tk.Frame(root)
        self.setup_step1()
        self.frame_step1.pack(fill="both", expand=True)

    # --- STEP 1 ---
    def setup_step1(self):
        tk.Label(self.frame_step1, text="Step 1: Select Controller", font=("Arial", 14, "bold")).pack(pady=10)
        self.lbl_status = tk.Label(self.frame_step1, text="Waiting for input...", fg="blue")
        self.lbl_status.pack()
        self.step1_combo = ttk.Combobox(self.frame_step1, state="readonly", width=30)
        self.step1_combo.pack(pady=5)
        self.step1_combo.bind("<<ComboboxSelected>>", self.manual_select)
        tk.Button(self.frame_step1, text="⚙ Configure HidHide (Double Input Fix)", command=lambda: HidHideConfigWindow(self.root, self.mapper)).pack(pady=10)
        self.btn_next = tk.Button(self.frame_step1, text="Next >", state="disabled", command=self.goto_step2)
        self.btn_next.pack(pady=20)
        self.root.after(50, self.poll_step1)
    
    def poll_step1(self):
        # CHECK: If widget is destroyed or not existing, stop. 
        # CHANGED: We use winfo_exists() instead of viewable() to prevent early exit.
        if not self.frame_step1.winfo_exists(): return
        
        try:
            connected = []
            for i in range(4):
                state = self.xi.get_state(i)
                if state:
                    connected.append(f"Port {i}")
                    if self.xi.is_button_pressed(state) and self.selected_port != i:
                        self.selected_port = i
                        self.lbl_status.config(text=f"Auto-Detected Port {i}!", fg="green")
                        self.btn_next.config(state="normal")
                        self.step1_combo.set(f"Port {i}")
            
            # Update Dropdown List
            if list(self.step1_combo['values']) != connected:
                self.step1_combo['values'] = connected
                if self.step1_combo.get() not in connected:
                    self.step1_combo.set("")
        except Exception as e:
            print(f"POLLING ERROR: {e}")

        # Recursion
        self.root.after(50, self.poll_step1)

    def manual_select(self, event):
        val = self.step1_combo.get()
        if val:
            self.selected_port = int(val.split(" ")[1])
            self.btn_next.config(state="normal")

    def goto_step2(self):
        self.frame_step1.pack_forget()
        self.setup_step2()
        self.frame_step2.pack(fill="both", expand=True)

    # --- STEP 2 ---
    def setup_step2(self):
        for widget in self.frame_step2.winfo_children(): widget.destroy()
        header_frame = tk.Frame(self.frame_step2)
        header_frame.pack(side="top", fill="x")
        tk.Label(header_frame, text="Step 2: Map Buttons & Axes", font=("Arial", 14, "bold")).pack(pady=10)
        qol_frame = tk.Frame(header_frame)
        qol_frame.pack(pady=5)
        tk.Button(qol_frame, text="Reset Defaults", command=self.action_reset_defaults).pack(side="left", padx=5)
        tk.Button(qol_frame, text="Unmap All", command=self.action_unmap_all).pack(side="left", padx=5)
        nav_frame = tk.Frame(self.frame_step2, bg="#f0f0f0", bd=1, relief="sunken")
        nav_frame.pack(side="bottom", fill="x", ipadx=10, ipady=10)
        tk.Button(nav_frame, text="Next Step >", bg="#4CAF50", fg="white", font=("Arial", 11, "bold"), command=self.goto_step3).pack(side="right", padx=20)
        canvas = tk.Canvas(self.frame_step2)
        scrollbar = ttk.Scrollbar(self.frame_step2, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=10)
        scrollbar.pack(side="right", fill="y")
        tk.Label(scroll_frame, text="Buttons & D-Pad", font=("Arial", 10, "bold")).pack(anchor="w", pady=(5,0))
        for btn_name, current_val in self.mapper.config["buttons"].items():
            row = tk.Frame(scroll_frame)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{btn_name}:", width=15, anchor="w").pack(side="left")
            var = tk.StringVar(value=current_val)
            cb = ttk.Combobox(row, textvariable=var, values=VJOY_BUTTONS, width=10, state="readonly")
            cb.pack(side="left")
            cb.bind("<<ComboboxSelected>>", lambda e, k=btn_name, v=var: self.mapper.config["buttons"].update({k: v.get()}))
        def draw_axis_group(title, axes_keys, is_trigger=False, is_stick=False):
            tk.Label(scroll_frame, text=title, font=("Arial", 10, "bold"), fg="#333").pack(anchor="w", pady=(15,0))
            for axis_name in axes_keys:
                row = tk.Frame(scroll_frame)
                row.pack(fill="x", pady=2)
                tk.Label(row, text=f"{axis_name}:", width=15, anchor="w").pack(side="left")
                data = self.mapper.config["axes"][axis_name]
                var_target = tk.StringVar(value=data["target"])
                cb = ttk.Combobox(row, textvariable=var_target, values=VJOY_AXES_LIST, width=10, state="readonly")
                cb.pack(side="left")
                cb.bind("<<ComboboxSelected>>", lambda e, k=axis_name, v=var_target: self.mapper.config["axes"][k].update({"target": v.get()}))
                tk.Button(row, text="⚙ Settings", command=lambda k=axis_name, d=data, t=is_trigger, s=is_stick: AxisSettingsWindow(self.root, k, k, d, t, s)).pack(side="left", padx=10)
            if is_stick:
                current_sq = self.mapper.config["axes"][axes_keys[0]].get("square", False)
                var_sq = tk.BooleanVar(value=current_sq)
                def update_square():
                    for k in axes_keys: self.mapper.config["axes"][k]["square"] = var_sq.get()
                tk.Checkbutton(scroll_frame, text="Square Output (Circle to Square)", variable=var_sq, command=update_square).pack(anchor="w", padx=20, pady=2)
        draw_axis_group("Triggers", ["LT", "RT"], is_trigger=True)
        draw_axis_group("Left Analog Stick", ["LX", "LY"], is_stick=True)
        draw_axis_group("Right Analog Stick", ["RX", "RY"], is_stick=True)

    def action_reset_defaults(self):
        if messagebox.askyesno("Reset", "Reset all mappings to default?"):
            self.mapper.reset_to_defaults()
            self.setup_step2() 
    def action_unmap_all(self):
        if messagebox.askyesno("Unmap", "Set all inputs to 'None'?"):
            self.mapper.unmap_all()
            self.setup_step2() 
    def goto_step3(self):
        self.mapper.save_config()
        self.frame_step2.pack_forget()
        self.setup_step3()
        self.frame_step3.pack(fill="both", expand=True)

    # --- STEP 3 ---
    def setup_step3(self):
        for widget in self.frame_step3.winfo_children(): widget.destroy()
        tk.Label(self.frame_step3, text="Step 3: Advanced & Run", font=("Arial", 14, "bold")).pack(pady=10)
        opts_frame = tk.LabelFrame(self.frame_step3, text="Options", padx=10, pady=10)
        opts_frame.pack(fill="x", padx=20, pady=5)
        
        # Options Row 1
        f_o1 = tk.Frame(opts_frame); f_o1.pack(fill="x")
        tk.Button(f_o1, text="Program Settings (Hz)", command=self.open_program_settings).pack(side="left", padx=5)
        tk.Button(f_o1, text="Mask vJoy as Steering Wheel (Recommended)", command=self.apply_wheel_mask).pack(side="left", padx=5)
        
        # Options Row 2
        f_o2 = tk.Frame(opts_frame); f_o2.pack(fill="x", pady=5)
        tk.Button(f_o2, text="Open vJoy Input Viewer", command=lambda: InputViewerWindow(self.root, self)).pack(side="left", padx=5)

        scripts_frame = tk.LabelFrame(self.frame_step3, text="Custom Scripts", padx=10, pady=10)
        scripts_frame.pack(fill="both", expand=True, padx=20, pady=5)
        def add_script_row(name, config_key, command):
            s_row = tk.Frame(scripts_frame)
            s_row.pack(fill="x", pady=5)
            tk.Label(s_row, text=name, font=("Arial", 10, "bold"), width=25, anchor="w").pack(side="left")
            tk.Button(s_row, text="Configure", command=command).pack(side="right")
            conf = self.mapper.config["scripts"].get(config_key, {})
            if "enabled_for" in conf: is_on = conf.get("enabled_for", "Disabled") != "Disabled"
            else: is_on = conf.get("enabled", False)
            tk.Label(s_row, text=f"({'Enabled' if is_on else 'Disabled'})", fg=("green" if is_on else "gray")).pack(side="right", padx=10)
        add_script_row("Winding Stick Steering", "winding_steering", self.open_winding_settings)
        add_script_row("Range Modifier", "range_modifier", self.open_range_settings)
        add_script_row("Auto-Clutch (Sequential)", "auto_clutch", self.open_autoclutch_settings)

        ctrl_frame = tk.Frame(self.frame_step3)
        ctrl_frame.pack(side="bottom", fill="x", pady=20)
        var_hid = tk.BooleanVar(value=self.mapper.config.get("use_hidhide", True))
        chk_hid = tk.Checkbutton(ctrl_frame, text="Hide Physical Controller (Fixes Double Input)", variable=var_hid, font=("Arial", 10, "bold"), command=lambda: self.mapper.config.update({"use_hidhide": var_hid.get()}))
        chk_hid.pack(pady=10)
        self.btn_run = tk.Button(ctrl_frame, text="START MAPPING", bg="green", fg="white", font=("Arial", 12, "bold"), command=self.start_mapping_loop)
        self.btn_run.pack(pady=5, ipadx=20)
        self.btn_stop = tk.Button(ctrl_frame, text="STOP", state="disabled", bg="red", fg="white", font=("Arial", 12, "bold"), command=self.stop_mapping_loop)
        self.btn_stop.pack(pady=5, ipadx=20)
        tk.Button(ctrl_frame, text="< Back to Settings", command=self.go_back_to_step2).pack(pady=10)

    # --- REGISTRY LOGIC ---
    def apply_wheel_mask(self):
        if not messagebox.askyesno("Registry Modification", "This will modify the Windows Registry to make vJoy appear as a Wheel Device.\nRequires Administrator. It is recommended to backup your Windows Registry.\n\nProceed?"): return
        if not is_admin(): messagebox.showerror("Permission Denied", "Please restart as Administrator."); return
        key_path = r"System\CurrentControlSet\Control\MediaProperties\PrivateProperties\Joystick\OEM\VID_1234&PID_BEAD"
        binary_data = bytes([0x43, 0x00, 0x88, 0x01, 0xfe, 0x00, 0x00, 0x00])
        name_data = "vJoy Wheel"
        try:
            key_curr = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            winreg.SetValueEx(key_curr, "OEMData", 0, winreg.REG_BINARY, binary_data)
            winreg.SetValueEx(key_curr, "OEMName", 0, winreg.REG_SZ, name_data)
            winreg.CloseKey(key_curr)
            key_local = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path)
            winreg.SetValueEx(key_local, "OEMData", 0, winreg.REG_BINARY, binary_data)
            winreg.CloseKey(key_local)
            messagebox.showinfo("Success", "Registry updated!\nYou won't need to do this again.")
        except Exception as e: messagebox.showerror("Registry Error", f"{e}")

    def open_program_settings(self): ProgramSettingsWindow(self.root, self.mapper.config)
    def open_winding_settings(self): WindingSettingsWindow(self.root, self.mapper.config); self.root.after(100, lambda: self.wait_for_window_close())
    def open_range_settings(self): RangeModifierWindow(self.root, self.mapper.config); self.root.after(100, lambda: self.wait_for_window_close())
    def open_autoclutch_settings(self): AutoClutchSettingsWindow(self.root, self.mapper.config); self.root.after(100, lambda: self.wait_for_window_close())
    def wait_for_window_close(self):
        child_wins = self.root.winfo_children()
        popup_open = any(isinstance(x, (WindingSettingsWindow, RangeModifierWindow, AutoClutchSettingsWindow)) for x in child_wins)
        if popup_open: self.root.after(500, self.wait_for_window_close)
        else:
            self.mapper.save_config()
            if self.frame_step3.winfo_viewable(): self.setup_step3()

    def go_back_to_step2(self):
        if self.is_running: self.stop_mapping_loop()
        self.frame_step3.pack_forget()
        self.setup_step2()
        self.frame_step2.pack(fill="both", expand=True)

    def start_mapping_loop(self):
        use_hidhide = self.mapper.config.get("use_hidhide", True)
        hidhide_ok = self.mapper.hidhide.is_installed()
        device_list = self.mapper.config.get("hidden_devices", [])
        if use_hidhide and (not hidhide_ok or not device_list):
            win = HidHideWarningWindow(self.root, self.mapper)
            self.root.wait_window(win)
            if self.mapper.config.get("use_hidhide", True): pass
        self.is_running = True
        self.stop_event.clear()
        if self.mapper.config.get("use_hidhide", True): self.mapper.apply_hiding()
        self.btn_run.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.thread = threading.Thread(target=self.mapping_worker)
        self.thread.daemon = True
        self.thread.start()

    def stop_mapping_loop(self):
        self.is_running = False
        self.stop_event.set()
        self.mapper.disable_hiding()
        self.btn_run.config(state="normal")
        self.btn_stop.config(state="disabled")

    def mapping_worker(self):
        print("Mapping Worker Started")
        last_time = time.perf_counter()
        while not self.stop_event.is_set():
            current_time = time.perf_counter()
            dt = current_time - last_time
            last_time = current_time
            rate = self.mapper.config["global_settings"].get("update_rate", 1000)
            target_sleep = 1.0 / rate
            state = self.xi.get_state(self.selected_port)
            if state: self.mapper.update_vjoy(state, dt)
            elapsed = time.perf_counter() - current_time
            sleep_needed = target_sleep - elapsed
            if sleep_needed > 0: time.sleep(sleep_needed)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()