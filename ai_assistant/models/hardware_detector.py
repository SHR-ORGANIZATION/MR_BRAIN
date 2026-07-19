"""
AMAZON AI - Hardware Detector
Detects CPU, RAM, GPU capabilities and recommends appropriate AI models.
"""
import platform
import subprocess
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HardwareProfile:
    """Hardware capabilities profile."""
    cpu_cores: int
    cpu_name: str
    ram_total_gb: float
    ram_available_gb: float
    gpu_available: bool
    gpu_name: Optional[str] = None
    gpu_memory_gb: float = 0.0
    architecture: str = ""
    os_type: str = ""
    
    @property
    def tier(self) -> str:
        """Determine hardware tier for model selection."""
        if self.ram_total_gb >= 32 and self.gpu_available:
            return "high"
        elif self.ram_total_gb >= 16:
            return "medium"
        else:
            return "low"
    
    @property
    def recommended_models(self) -> list:
        """Get list of recommended model sizes."""
        if self.tier == "high":
            return ["llama2:13b", "mistral:7b", "codellama:13b", "phi:latest"]
        elif self.tier == "medium":
            return ["llama2:7b", "mistral:7b", "phi:latest", "tinyllama"]
        else:
            return ["phi:latest", "tinyllama", "stablelm:3b"]


class HardwareDetector:
    """
    Detects hardware capabilities for AI model optimization.
    
    Detects:
    - CPU cores and model
    - Total and available RAM
    - GPU availability (CUDA/Metal)
    - Architecture (x86_64, arm64)
    """
    
    def __init__(self):
        self._profile: Optional[HardwareProfile] = None
    
    def detect(self) -> HardwareProfile:
        """Detect hardware capabilities."""
        if self._profile:
            return self._profile
        
        import psutil
        
        # CPU info
        cpu_cores = psutil.cpu_count(logical=True)
        cpu_name = self._get_cpu_name()
        
        # RAM info
        ram = psutil.virtual_memory()
        ram_total_gb = ram.total / (1024**3)
        ram_available_gb = ram.available / (1024**3)
        
        # GPU info
        gpu_available, gpu_name, gpu_memory = self._detect_gpu()
        
        # Architecture
        architecture = platform.machine()
        os_type = platform.system()
        
        self._profile = HardwareProfile(
            cpu_cores=cpu_cores,
            cpu_name=cpu_name,
            ram_total_gb=ram_total_gb,
            ram_available_gb=ram_available_gb,
            gpu_available=gpu_available,
            gpu_name=gpu_name,
            gpu_memory_gb=gpu_memory,
            architecture=architecture,
            os_type=os_type
        )
        
        logger.info(f"Hardware detected: {self._profile.tier} tier")
        return self._profile
    
    def _get_cpu_name(self) -> str:
        """Get CPU model name."""
        try:
            if platform.system() == "Windows":
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                    r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                winreg.CloseKey(key)
                return name.strip()
            elif platform.system() == "Darwin":
                result = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True, text=True, timeout=5
                )
                return result.stdout.strip()
            else:
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "model name" in line:
                            return line.split(":")[1].strip()
        except Exception:
            pass
        return platform.processor() or "Unknown CPU"
    
    def _detect_gpu(self) -> tuple:
        """Detect GPU capabilities. Returns (available, name, memory_gb)."""
        # Check for NVIDIA GPU (CUDA)
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if lines:
                    parts = lines[0].split(",")
                    gpu_name = parts[0].strip()
                    gpu_mem_str = parts[1].strip() if len(parts) > 1 else "0 MiB"
                    # Parse memory (e.g., "8192 MiB" -> 8.0 GB)
                    gpu_mem = float(gpu_mem_str.split()[0]) / 1024
                    return True, gpu_name, gpu_mem
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Check for Apple Silicon (Metal)
        if platform.system() == "Darwin":
            try:
                result = subprocess.run(
                    ["system_profiler", "SPDisplaysDataType"],
                    capture_output=True, text=True, timeout=10
                )
                if "Chipset Model: Apple" in result.stdout or "Metal" in result.stdout:
                    # Apple Silicon has unified memory
                    import psutil
                    ram = psutil.virtual_memory()
                    return True, "Apple Silicon", ram.total / (1024**3)
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        
        return False, None, 0.0
    
    def get_model_recommendation(self) -> Dict[str, Any]:
        """Get AI model recommendations based on hardware."""
        profile = self.detect()
        
        return {
            "hardware_tier": profile.tier,
            "recommended_models": profile.recommended_models,
            "can_run_local_llm": profile.ram_total_gb >= 8,
            "gpu_acceleration": profile.gpu_available,
            "suggested_model": profile.recommended_models[0] if profile.recommended_models else None
        }
    
    def can_run_model(self, model_size_gb: float) -> bool:
        """Check if hardware can run a model of given size."""
        profile = self.detect()
        
        # Need at least model_size + 4GB for system
        required_ram = model_size_gb + 4.0
        
        if profile.gpu_available and profile.gpu_memory_gb >= model_size_gb:
            return True  # Can run on GPU
        
        return profile.ram_available_gb >= required_ram


# Singleton instance
_detector_instance = None

def get_hardware_detector() -> HardwareDetector:
    """Get or create the singleton hardware detector."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = HardwareDetector()
    return _detector_instance
