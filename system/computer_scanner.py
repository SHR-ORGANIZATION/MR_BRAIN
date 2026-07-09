"""
Computer Hardware & Peripheral Scanner for AMAZON AI
Automatically detects and catalogs:
- OS information
- CPU, RAM, GPU
- Storage devices
- Network interfaces
- Connected peripherals (USB, Bluetooth, etc.)
- Display information
- Audio devices
"""
import platform
import subprocess
import json
from pathlib import Path
from datetime import datetime


class ComputerScanner:
    """Scans and catalogs computer hardware and peripherals."""
    
    def __init__(self):
        self.system = platform.system()
        self.scan_results = {}
    
    def scan_all(self):
        """Run complete system scan."""
        print("[ComputerScanner] Starting full system scan...")
        
        self.scan_results = {
            "timestamp": datetime.now().isoformat(),
            "os_info": self.get_os_info(),
            "cpu_info": self.get_cpu_info(),
            "memory_info": self.get_memory_info(),
            "gpu_info": self.get_gpu_info(),
            "storage_info": self.get_storage_info(),
            "network_info": self.get_network_info(),
            "usb_devices": self.get_usb_devices(),
            "bluetooth_devices": self.get_bluetooth_devices(),
            "display_info": self.get_display_info(),
            "audio_devices": self.get_audio_devices(),
            "battery_info": self.get_battery_info(),
        }
        
        print(f"[ComputerScanner] Scan complete! Found:")
        print(f"  - OS: {self.scan_results['os_info'].get('system', 'Unknown')}")
        print(f"  - CPU: {self.scan_results['cpu_info'].get('brand', 'Unknown')}")
        print(f"  - RAM: {self.scan_results['memory_info'].get('total', 'Unknown')}")
        print(f"  - USB Devices: {len(self.scan_results['usb_devices'])}")
        print(f"  - Bluetooth Devices: {len(self.scan_results['bluetooth_devices'])}")
        
        return self.scan_results
    
    def get_os_info(self):
        """Get operating system information."""
        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
        }
    
    def get_cpu_info(self):
        """Get CPU information."""
        if self.system == "Darwin":  # macOS
            try:
                brand = subprocess.check_output(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    stderr=subprocess.DEVNULL
                ).decode().strip()
                cores = subprocess.check_output(
                    ["sysctl", "-n", "hw.ncpu"],
                    stderr=subprocess.DEVNULL
                ).decode().strip()
                return {
                    "brand": brand,
                    "cores": cores,
                    "architecture": platform.machine(),
                }
            except:
                pass
        elif self.system == "Windows":
            try:
                brand = subprocess.check_output(
                    ["wmic", "cpu", "get", "name"],
                    stderr=subprocess.DEVNULL
                ).decode().strip().split("\n")[1].strip()
                cores = subprocess.check_output(
                    ["wmic", "cpu", "get", "NumberOfCores"],
                    stderr=subprocess.DEVNULL
                ).decode().strip().split("\n")[1].strip()
                return {
                    "brand": brand,
                    "cores": cores,
                    "architecture": platform.machine(),
                }
            except:
                pass
        elif self.system == "Linux":
            try:
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "model name" in line:
                            brand = line.split(":")[1].strip()
                            break
                cores = subprocess.check_output(
                    ["nproc"],
                    stderr=subprocess.DEVNULL
                ).decode().strip()
                return {
                    "brand": brand,
                    "cores": cores,
                    "architecture": platform.machine(),
                }
            except:
                pass
        
        return {"brand": "Unknown", "cores": "Unknown", "architecture": platform.machine()}
    
    def get_memory_info(self):
        """Get RAM information."""
        if self.system == "Darwin":  # macOS
            try:
                total_bytes = subprocess.check_output(
                    ["sysctl", "-n", "hw.memsize"],
                    stderr=subprocess.DEVNULL
                ).decode().strip()
                total_gb = int(total_bytes) / (1024**3)
                return {
                    "total": f"{total_gb:.1f} GB",
                    "total_bytes": int(total_bytes),
                }
            except:
                pass
        elif self.system == "Windows":
            try:
                total_bytes = subprocess.check_output(
                    ["wmic", "ComputerSystem", "get", "TotalPhysicalMemory"],
                    stderr=subprocess.DEVNULL
                ).decode().strip().split("\n")[1].strip()
                total_gb = int(total_bytes) / (1024**3)
                return {
                    "total": f"{total_gb:.1f} GB",
                    "total_bytes": int(total_bytes),
                }
            except:
                pass
        elif self.system == "Linux":
            try:
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if "MemTotal" in line:
                            total_kb = int(line.split(":")[1].strip().split()[0])
                            total_gb = total_kb / (1024**2)
                            return {
                                "total": f"{total_gb:.1f} GB",
                                "total_bytes": total_kb * 1024,
                            }
            except:
                pass
        
        return {"total": "Unknown", "total_bytes": 0}
    
    def get_gpu_info(self):
        """Get GPU/Graphics information."""
        gpus = []
        
        if self.system == "Darwin":  # macOS
            try:
                result = subprocess.check_output(
                    ["system_profiler", "SPDisplaysDataType", "-json"],
                    stderr=subprocess.DEVNULL
                ).decode()
                data = json.loads(result)
                for gpu in data.get("SPDisplaysDataType", []):
                    gpus.append({
                        "name": gpu.get("sppci_model", "Unknown"),
                        "vendor": gpu.get("spdisplays_vendor", "Unknown"),
                        "vram": gpu.get("spdisplays_vram_shared", "Unknown"),
                    })
            except:
                pass
        elif self.system == "Windows":
            try:
                result = subprocess.check_output(
                    ["wmic", "path", "win32_VideoController", "get", "Name"],
                    stderr=subprocess.DEVNULL
                ).decode()
                lines = result.strip().split("\n")[1:]
                for line in lines:
                    if line.strip():
                        gpus.append({"name": line.strip(), "vendor": "Unknown", "vram": "Unknown"})
            except:
                pass
        elif self.system == "Linux":
            try:
                result = subprocess.check_output(
                    ["lspci"],
                    stderr=subprocess.DEVNULL
                ).decode()
                for line in result.split("\n"):
                    if "VGA" in line or "3D" in line or "Display" in line:
                        gpus.append({"name": line.split(":")[2].strip() if ":" in line else line.strip(), "vendor": "Unknown", "vram": "Unknown"})
            except:
                pass
        
        return gpus if gpus else [{"name": "Unknown", "vendor": "Unknown", "vram": "Unknown"}]
    
    def get_storage_info(self):
        """Get storage/disk information."""
        drives = []
        
        if self.system == "Darwin":  # macOS
            try:
                result = subprocess.check_output(
                    ["diskutil", "list", "-plist"],
                    stderr=subprocess.DEVNULL
                ).decode()
                # Simplified: just get main disk info
                total = subprocess.check_output(
                    ["df", "-h", "/"],
                    stderr=subprocess.DEVNULL
                ).decode().strip().split("\n")[1]
                parts = total.split()
                drives.append({
                    "name": "Macintosh HD",
                    "total": parts[1],
                    "used": parts[2],
                    "available": parts[3],
                    "use_percent": parts[4],
                })
            except:
                pass
        elif self.system == "Windows":
            try:
                result = subprocess.check_output(
                    ["wmic", "logicaldisk", "get", "DeviceID,Size,FreeSpace"],
                    stderr=subprocess.DEVNULL
                ).decode()
                lines = result.strip().split("\n")[1:]
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3:
                            drives.append({
                                "name": parts[0],
                                "total": f"{int(parts[1])/(1024**3):.1f} GB",
                                "free": f"{int(parts[2])/(1024**3):.1f} GB",
                            })
            except:
                pass
        elif self.system == "Linux":
            try:
                result = subprocess.check_output(
                    ["df", "-h"],
                    stderr=subprocess.DEVNULL
                ).decode()
                lines = result.strip().split("\n")[1:]
                for line in lines:
                    if line.startswith("/dev/"):
                        parts = line.split()
                        drives.append({
                            "name": parts[0],
                            "total": parts[1],
                            "used": parts[2],
                            "available": parts[3],
                            "use_percent": parts[4],
                            "mount": parts[5] if len(parts) > 5 else "",
                        })
            except:
                pass
        
        return drives if drives else [{"name": "Unknown", "total": "Unknown"}]
    
    def get_network_info(self):
        """Get network interfaces information."""
        interfaces = []
        
        try:
            if self.system == "Darwin":  # macOS
                result = subprocess.check_output(
                    ["networksetup", "-listallnetworkservices"],
                    stderr=subprocess.DEVNULL
                ).decode()
                for line in result.strip().split("\n")[1:]:
                    if line.strip() and "*" not in line:
                        interfaces.append({"name": line.strip(), "type": "Unknown"})
            elif self.system == "Windows":
                result = subprocess.check_output(
                    ["ipconfig", "/all"],
                    stderr=subprocess.DEVNULL
                ).decode()
                # Simplified parsing
                interfaces.append({"name": "Ethernet", "type": "Unknown"})
            elif self.system == "Linux":
                result = subprocess.check_output(
                    ["ip", "link", "show"],
                    stderr=subprocess.DEVNULL
                ).decode()
                for line in result.split("\n"):
                    if ": " in line and "LOOPBACK" not in line.upper():
                        name = line.split(": ")[1].split("@")[0] if "@" in line else line.split(": ")[1]
                        interfaces.append({"name": name, "type": "Unknown"})
        except:
            pass
        
        return interfaces if interfaces else [{"name": "Unknown", "type": "Unknown"}]
    
    def get_usb_devices(self):
        """Get connected USB devices."""
        devices = []
        
        if self.system == "Darwin":  # macOS
            try:
                result = subprocess.check_output(
                    ["system_profiler", "SPUSBDataType", "-json"],
                    stderr=subprocess.DEVNULL
                ).decode()
                data = json.loads(result)
                for device in data.get("SPUSBDataType", []):
                    devices.append({
                        "name": device.get("_name", "Unknown"),
                        "manufacturer": device.get("spusb_manufacturer", "Unknown"),
                        "product_id": device.get("spusb_productID", "Unknown"),
                        "vendor_id": device.get("spusb_vendorID", "Unknown"),
                    })
            except:
                pass
        elif self.system == "Windows":
            try:
                result = subprocess.check_output(
                    ["wmic", "path", "Win32_PnPEntity", "where", "DeviceID like '%USB%'", "get", "Name"],
                    stderr=subprocess.DEVNULL
                ).decode()
                for line in result.strip().split("\n")[1:]:
                    if line.strip():
                        devices.append({"name": line.strip(), "manufacturer": "Unknown"})
            except:
                pass
        elif self.system == "Linux":
            try:
                result = subprocess.check_output(
                    ["lsusb"],
                    stderr=subprocess.DEVNULL
                ).decode()
                for line in result.strip().split("\n"):
                    if ":" in line:
                        parts = line.split(":", 1)
                        devices.append({"name": parts[1].strip() if len(parts) > 1 else line.strip(), "manufacturer": "Unknown"})
            except:
                pass
        
        return devices
    
    def get_bluetooth_devices(self):
        """Get connected Bluetooth devices."""
        devices = []
        
        if self.system == "Darwin":  # macOS
            try:
                result = subprocess.check_output(
                    ["system_profiler", "SPBluetoothDataType", "-json"],
                    stderr=subprocess.DEVNULL
                ).decode()
                data = json.loads(result)
                for device_name, device_info in data.get("SPBluetoothDataType", {}).items():
                    if device_name != "_items":
                        devices.append({
                            "name": device_name,
                            "connected": device_info.get("device_connected", "No"),
                            "type": device_info.get("device_type", "Unknown"),
                        })
            except:
                pass
        elif self.system == "Windows":
            try:
                result = subprocess.check_output(
                    ["powershell", "Get-PnpDevice", "-Class", "Bluetooth"],
                    stderr=subprocess.DEVNULL
                ).decode()
                for line in result.strip().split("\n")[2:]:
                    if line.strip():
                        devices.append({"name": line.split()[0], "connected": "Unknown"})
            except:
                pass
        elif self.system == "Linux":
            try:
                result = subprocess.check_output(
                    ["bluetoothctl", "devices", "Connected"],
                    stderr=subprocess.DEVNULL
                ).decode()
                for line in result.strip().split("\n"):
                    if line.strip():
                        devices.append({"name": line.split(" ", 1)[1] if " " in line else line, "connected": "Yes"})
            except:
                pass
        
        return devices
    
    def get_display_info(self):
        """Get display/monitor information."""
        displays = []
        
        if self.system == "Darwin":  # macOS
            try:
                result = subprocess.check_output(
                    ["system_profiler", "SPDisplaysDataType", "-json"],
                    stderr=subprocess.DEVNULL
                ).decode()
                data = json.loads(result)
                for display in data.get("SPDisplaysDataType", []):
                    displays.append({
                        "name": display.get("sppci_model", "Unknown"),
                        "resolution": display.get("spdisplays_main", "Unknown"),
                        "type": display.get("spdisplays_display_type", "Unknown"),
                    })
            except:
                pass
        elif self.system == "Windows":
            try:
                result = subprocess.check_output(
                    ["wmic", "path", "Win32_DesktopMonitor", "get", "Name,ScreenWidth,ScreenHeight"],
                    stderr=subprocess.DEVNULL
                ).decode()
                for line in result.strip().split("\n")[1:]:
                    if line.strip():
                        displays.append({"name": line.strip(), "resolution": "Unknown"})
            except:
                pass
        elif self.system == "Linux":
            try:
                result = subprocess.check_output(
                    ["xrandr"],
                    stderr=subprocess.DEVNULL
                ).decode()
                for line in result.split("\n"):
                    if " connected" in line:
                        name = line.split(" ")[0]
                        displays.append({"name": name, "resolution": "Unknown"})
            except:
                pass
        
        return displays if displays else [{"name": "Unknown", "resolution": "Unknown"}]
    
    def get_audio_devices(self):
        """Get audio input/output devices."""
        devices = []
        
        if self.system == "Darwin":  # macOS
            try:
                result = subprocess.check_output(
                    ["system_profiler", "SPAudioDataType", "-json"],
                    stderr=subprocess.DEVNULL
                ).decode()
                data = json.loads(result)
                for device in data.get("SPAudioDataType", []):
                    devices.append({
                        "name": device.get("_name", "Unknown"),
                        "type": device.get("spaudio_type", "Unknown"),
                    })
            except:
                pass
        elif self.system == "Windows":
            try:
                result = subprocess.check_output(
                    ["wmic", "path", "Win32_SoundDevice", "get", "Name"],
                    stderr=subprocess.DEVNULL
                ).decode()
                for line in result.strip().split("\n")[1:]:
                    if line.strip():
                        devices.append({"name": line.strip(), "type": "Unknown"})
            except:
                pass
        elif self.system == "Linux":
            try:
                result = subprocess.check_output(
                    ["aplay", "-l"],
                    stderr=subprocess.DEVNULL
                ).decode()
                for line in result.split("\n"):
                    if "card" in line:
                        devices.append({"name": line.split(":")[1].strip() if ":" in line else line.strip(), "type": "Output"})
            except:
                pass
        
        return devices if devices else [{"name": "Unknown", "type": "Unknown"}]
    
    def get_battery_info(self):
        """Get battery information (for laptops)."""
        if self.system == "Darwin":  # macOS
            try:
                result = subprocess.check_output(
                    ["pmset", "-g", "batt"],
                    stderr=subprocess.DEVNULL
                ).decode()
                return {
                    "present": "Battery" in result or "AC" in result,
                    "status": result.strip() if result else "Unknown",
                }
            except:
                pass
        elif self.system == "Windows":
            try:
                result = subprocess.check_output(
                    ["powercfg", "/batteryreport"],
                    stderr=subprocess.DEVNULL
                ).decode()
                return {"present": True, "status": "Report generated"}
            except:
                pass
        elif self.system == "Linux":
            try:
                with open("/sys/class/power_supply/BAT0/capacity", "r") as f:
                    capacity = f.read().strip()
                return {"present": True, "capacity": f"{capacity}%"}
            except:
                pass
        
        return {"present": False, "status": "No battery detected"}
    
    def save_scan_results(self, output_path=None):
        """Save scan results to JSON file."""
        if not output_path:
            output_path = Path(__file__).resolve().parent.parent / "learning" / "computer_scan.json"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.scan_results, f, indent=2, default=str)
        
        print(f"[ComputerScanner] Results saved to: {output_path}")
        return output_path


# Singleton scanner
_scanner = None


def get_scanner():
    """Get or create the global scanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = ComputerScanner()
    return _scanner


def scan_computer():
    """Quick function to scan the computer."""
    scanner = get_scanner()
    return scanner.scan_all()


if __name__ == "__main__":
    # Run scan when executed directly
    scanner = ComputerScanner()
    results = scanner.scan_all()
    scanner.save_scan_results()
    
    print("\n" + "="*60)
    print("COMPUTER SCAN SUMMARY")
    print("="*60)
    print(f"OS: {results['os_info']['system']} {results['os_info']['release']}")
    print(f"CPU: {results['cpu_info']['brand']} ({results['cpu_info']['cores']} cores)")
    print(f"RAM: {results['memory_info']['total']}")
    print(f"GPU: {', '.join([g['name'] for g in results['gpu_info']])}")
    print(f"Storage: {len(results['storage_info'])} drive(s)")
    print(f"Network: {len(results['network_info'])} interface(s)")
    print(f"USB Devices: {len(results['usb_devices'])}")
    print(f"Bluetooth: {len(results['bluetooth_devices'])} device(s)")
    print(f"Displays: {len(results['display_info'])}")
    print(f"Audio: {len(results['audio_devices'])} device(s)")
    print(f"Battery: {'Yes' if results['battery_info'].get('present') else 'No'}")
    print("="*60)
