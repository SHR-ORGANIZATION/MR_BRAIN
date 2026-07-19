"""
AMAZON AI - System Monitor Tool
Wraps psutil and environment_scanner for system monitoring.
"""
import sys
import logging
from pathlib import Path
from typing import List

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ai_assistant.tools.base_tool import BaseTool, ToolParameter, ToolResult

logger = logging.getLogger(__name__)


class SystemMonitorTool(BaseTool):
    """
    Tool for monitoring system resources.
    
    Capabilities:
    - CPU usage and info
    - RAM usage
    - Disk usage
    - Running processes
    - Battery status
    - Network info
    """
    
    @property
    def name(self) -> str:
        return "system_monitor"
    
    @property
    def description(self) -> str:
        return "Monitor system resources including CPU, RAM, disk, and processes"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="metric",
                type="string",
                description="What to monitor: 'cpu', 'ram', 'disk', 'processes', 'battery', 'all'",
                required=False,
                default="all"
            ),
            ToolParameter(
                name="top_n",
                type="integer",
                description="Number of top processes to show",
                required=False,
                default=10
            )
        ]
    
    @property
    def category(self) -> str:
        return "system"
    
    def execute(self, **kwargs) -> ToolResult:
        """Execute system monitoring."""
        try:
            import psutil
            from system.environment_scanner import get_environment_stats
            
            metric = kwargs.get("metric", "all")
            top_n = kwargs.get("top_n", 10)
            
            result = {}
            
            if metric in ["cpu", "all"]:
                result["cpu"] = {
                    "percent": psutil.cpu_percent(interval=0.5),
                    "cores": psutil.cpu_count(logical=True),
                    "physical_cores": psutil.cpu_count(logical=False),
                    "freq": self._get_cpu_freq()
                }
            
            if metric in ["ram", "memory", "all"]:
                ram = psutil.virtual_memory()
                result["ram"] = {
                    "total_gb": round(ram.total / (1024**3), 2),
                    "available_gb": round(ram.available / (1024**3), 2),
                    "used_gb": round(ram.used / (1024**3), 2),
                    "percent": ram.percent
                }
            
            if metric in ["disk", "storage", "all"]:
                disk = psutil.disk_usage('/')
                result["disk"] = {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent": disk.percent
                }
            
            if metric in ["processes", "all"]:
                processes = self._get_top_processes(top_n)
                result["processes"] = processes
            
            if metric in ["battery", "all"]:
                battery = self._get_battery_info()
                if battery:
                    result["battery"] = battery
            
            # Format response message
            message = self._format_response(result, metric)
            
            return ToolResult(
                success=True,
                data=result,
                message=message
            )
            
        except Exception as e:
            logger.error(f"System monitor error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message=f"Failed to monitor system: {str(e)}"
            )
    
    def _get_cpu_freq(self) -> dict:
        """Get CPU frequency info."""
        try:
            import psutil
            freq = psutil.cpu_freq()
            if freq:
                return {
                    "current_mhz": round(freq.current, 2),
                    "max_mhz": round(freq.max, 2) if freq.max else None
                }
        except Exception:
            pass
        return {}
    
    def _get_top_processes(self, n: int) -> list:
        """Get top N processes by CPU usage."""
        try:
            import psutil
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    info = proc.info
                    processes.append({
                        "pid": info['pid'],
                        "name": info['name'],
                        "cpu": info['cpu_percent'] or 0,
                        "memory": round(info['memory_percent'] or 0, 2)
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x['cpu'], reverse=True)
            return processes[:n]
        except Exception:
            return []
    
    def _get_battery_info(self) -> dict:
        """Get battery status if available."""
        try:
            import psutil
            battery = psutil.sensors_battery()
            if battery:
                return {
                    "percent": battery.percent,
                    "plugged": battery.power_plugged,
                    "secs_left": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None
                }
        except Exception:
            pass
        return None
    
    def _format_response(self, data: dict, metric: str) -> str:
        """Format the monitoring data into a readable message."""
        lines = ["💻 **System Status**\n"]
        
        if "cpu" in data:
            cpu = data["cpu"]
            lines.append(f"**CPU:** {cpu['percent']}% usage")
            lines.append(f"  • Cores: {cpu['cores']} ({cpu.get('physical_cores', '?')} physical)")
            if cpu.get('freq'):
                lines.append(f"  • Frequency: {cpu['freq'].get('current_mhz', '?')} MHz")
            lines.append("")
        
        if "ram" in data:
            ram = data["ram"]
            lines.append(f"**RAM:** {ram['percent']}% used")
            lines.append(f"  • Used: {ram['used_gb']} GB / {ram['total_gb']} GB")
            lines.append(f"  • Available: {ram['available_gb']} GB")
            lines.append("")
        
        if "disk" in data:
            disk = data["disk"]
            lines.append(f"**Disk:** {disk['percent']}% used")
            lines.append(f"  • Used: {disk['used_gb']} GB / {disk['total_gb']} GB")
            lines.append(f"  • Free: {disk['free_gb']} GB")
            lines.append("")
        
        if "processes" in data:
            lines.append(f"**Top Processes:** (showing {len(data['processes'])})")
            for proc in data['processes'][:5]:
                lines.append(f"  • {proc['name']}: CPU {proc['cpu']}%, RAM {proc['memory']}%")
            lines.append("")
        
        if "battery" in data:
            batt = data["battery"]
            status = "Charging" if batt.get("plugged") else "Discharging"
            lines.append(f"**Battery:** {batt['percent']}% ({status})")
        
        return "\n".join(lines)
