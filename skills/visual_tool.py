import psutil

async def generate_telemetry():
    """Generates a clean, standard-ASCII system telemetry readout."""
    try:
        # 1. Pull real system data
        cpu_cores = psutil.cpu_percent(interval=0.1, percpu=True)
        cpu_avg = sum(cpu_cores) / len(cpu_cores) if cpu_cores else 0
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # 2. Build the standard-character ASCII UI
        lines = []
        lines.append("╔══════════════════════════════════════════╗")
        lines.append("║        M.A.R.C.U.S. CORE TELEMETRY       ║")
        lines.append("╠══════════════════════════════════════════╣")
        
        # CPU Section
        lines.append(f"║ CPU OVERALL: {cpu_avg:05.1f}%                       ║")
        for i, core in enumerate(cpu_cores[:4]): # Limit to 4 cores to fit small UIs
            bar_len = int((core / 100) * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(f"║ CORE {i}: [{bar}] {core:05.1f}% ║")
        
        # RAM Section
        lines.append("╠══════════════════════════════════════════╣")
        ram_bar_len = int((ram.percent / 100) * 20)
        ram_bar = "█" * ram_bar_len + "░" * (20 - ram_bar_len)
        lines.append(f"║ MEMORY : [{ram_bar}] {ram.percent:05.1f}% ║")
        lines.append(f"║ USED   : {ram.used / (1024**3):05.1f} GB / {ram.total / (1024**3):05.1f} GB           ║")
        
        # Disk Section
        lines.append("╠══════════════════════════════════════════╣")
        lines.append(f"║ STORAGE: {disk.free / (1024**3):05.1f} GB Free                 ║")
        lines.append("╚══════════════════════════════════════════╝")

        return "\n".join(lines)
    except Exception as e:
        return f"[ Telemetry Error ]: {e}"