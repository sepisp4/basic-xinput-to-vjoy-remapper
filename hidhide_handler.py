import os
import subprocess
import sys
import wmi
import pythoncom

class HidHideHandler:
    def __init__(self, cli_path=None):
        self.cli_path = cli_path
        
        # clean path (remove quotes if user pasted them)
        if self.cli_path:
            self.cli_path = self.cli_path.strip('"').strip("'")

        if not self.cli_path:
            # Default location
            default = r"C:\Program Files\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe"
            if os.path.exists(default):
                self.cli_path = default

    def is_installed(self):
        return self.cli_path and os.path.exists(self.cli_path)

    def get_connected_devices_set(self):
        """Returns a set of all PnP Device Instance Paths currently on the system."""
        try:
            pythoncom.CoInitialize() 
            c = wmi.WMI()
            devices = c.Win32_PnPEntity()
            return set([d.DeviceID.upper() for d in devices if d.DeviceID])
        except Exception as e:
            print(f"WMI Error: {e}")
            return set()
        finally:
            pythoncom.CoUninitialize()

    def run_command(self, args):
        """Runs a command with HidHideCLI."""
        if not self.is_installed(): 
            print("HidHideCLI not found. Check path.")
            return
        
        cmd = [self.cli_path] + args
        
        # Hide console window
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        try:
            # DEBUG: Uncomment this to see exactly what is running
            # print(f"CMD: {cmd}") 
            subprocess.run(cmd, startupinfo=startupinfo, check=False)
        except Exception as e:
            print(f"HidHide Execution Error: {e}")

    def whitelist_application(self, path_to_exe):
        self.run_command(["--app-reg", path_to_exe])

    def unwhitelist_application(self, path_to_exe):
        self.run_command(["--app-unreg", path_to_exe])

    def hide_devices(self, device_instance_ids):
        for dev_id in device_instance_ids:
            self.run_command(["--dev-hide", dev_id])

    def unhide_devices(self, device_instance_ids):
        for dev_id in device_instance_ids:
            self.run_command(["--dev-unhide", dev_id])

    def set_cloaking(self, enable=True):
        # CORRECTED COMMANDS based on your help output
        if enable:
            self.run_command(["--cloak-on"])
        else:
            self.run_command(["--cloak-off"])