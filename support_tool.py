"""
Unnamedtech Support Tool
A multi-page system diagnostics and support utility for Windows.
"""

import customtkinter as ctk
import tkinter as tk
import subprocess
import platform
import winreg
import ctypes
import os
import sys
import threading
import webbrowser
import json


# ─── Theme (red) ──────────────────────────────────────────────────────────────
BG_MAIN       = "#1a0d0f"
BG_CARD       = "#291518"
BG_CARD_HOVER = "#381c20"
BG_NAVBAR     = "#251113"
BG_NAVBAR_BTN = "#331a1d"
BG_NAV_ACTIVE = "#472528"
ACCENT        = "#c62828"
ACCENT_HOVER  = "#e53935"
TEXT_PRIMARY   = "#e8e0e0"
TEXT_SECONDARY = "#8a6b70"
TEXT_DIM       = "#6a4a4f"
GREEN_DOT     = "#00e676"
RED_DOT       = "#ff1744"
ORANGE_DOT    = "#ff9100"
BORDER        = "#401e22"
BTN_BG        = "#401e22"
BTN_HOVER     = "#542a2f"
SEND_BTN_BG   = "#5c2529"
SEND_BTN_FG   = TEXT_PRIMARY
DISABLED_BG   = "#2a1315"
DISABLED_FG   = "#553a3d"

# URLs
WEBSITE_URL   = "https://unnamedtech.cc/"
DISCORD_URL   = "https://discord.com/invite/unnamedtech"
TUTORIAL_URL  = "https://unnamed-tech.gitbook.io/unnamedtech/tutorial-error-fix"

WINDOW_WIDTH  = 860
WINDOW_HEIGHT = 580


# ─── Helpers ──────────────────────────────────────────────────────────────────

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_ps(cmd):
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=20,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return r.stdout.strip()
    except Exception as e:
        return f"Error: {e}"


def run_cmd(cmd):
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=20,
            creationflags=subprocess.CREATE_NO_WINDOW, shell=True,
        )
        return r.stdout.strip()
    except Exception as e:
        return f"Error: {e}"


def reg_read(hive, path, name):
    try:
        key = winreg.OpenKey(hive, path)
        val, _ = winreg.QueryValueEx(key, name)
        winreg.CloseKey(key)
        return val
    except Exception:
        return None


# ─── System Info Gathering (all via PowerShell for exe compatibility) ─────────

def get_windows_info():
    product = reg_read(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Microsoft\Windows NT\CurrentVersion", "ProductName") or "Unknown"
    ver = reg_read(winreg.HKEY_LOCAL_MACHINE,
                   r"SOFTWARE\Microsoft\Windows NT\CurrentVersion", "DisplayVersion")
    if not ver:
        ver = reg_read(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Microsoft\Windows NT\CurrentVersion", "ReleaseId") or ""
    build = reg_read(winreg.HKEY_LOCAL_MACHINE,
                     r"SOFTWARE\Microsoft\Windows NT\CurrentVersion", "CurrentBuildNumber") or "0"
    # Windows 11 is build 22000+, but registry ProductName often still says "Windows 10"
    try:
        if int(build) >= 22000 and "10" in product:
            product = product.replace("Windows 10", "Windows 11")
    except ValueError:
        pass
    return f"{product} ({ver})"


def get_cpu_info():
    out = run_ps("(Get-CimInstance Win32_Processor).Name")
    if out and "Error" not in out:
        return out.strip()
    return reg_read(winreg.HKEY_LOCAL_MACHINE,
                    r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
                    "ProcessorNameString") or "Unknown"


def get_gpu_info():
    """Returns all GPUs (internal + external) as comma-separated string."""
    out = run_ps("(Get-CimInstance Win32_VideoController).Name")
    if out and "Error" not in out:
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        return ", ".join(lines) if lines else "Unknown"
    return "Unknown"


def get_ram_info():
    out = run_ps(
        "$m = Get-CimInstance Win32_PhysicalMemory; "
        "$total = ($m | Measure-Object -Property Capacity -Sum).Sum; "
        "$gb = [math]::Round($total / 1GB); "
        "$mfr = ($m | Select-Object -First 1).Manufacturer; "
        "\"$gb GB - $mfr\""
    )
    if out and "Error" not in out:
        return out.strip()
    return "Unknown"


def get_baseboard_info():
    out = run_ps("(Get-CimInstance Win32_BaseBoard).Product")
    if out and "Error" not in out:
        return out.strip()
    return "Unknown"


def get_main_drive_serial():
    out = run_ps(
        "(Get-CimInstance Win32_DiskDrive | Where-Object {$_.Index -eq 0}).SerialNumber"
    )
    if out and "Error" not in out and out.strip():
        return out.strip()
    return "N/A"


def get_cpu_serial():
    out = run_ps("(Get-CimInstance Win32_Processor).ProcessorId")
    if out and "Error" not in out and out.strip():
        return out.strip()
    return "N/A"


def get_gpu_serial():
    """Returns all GPU PNP IDs (internal + external) joined with ' | '."""
    out = run_ps("(Get-CimInstance Win32_VideoController).PNPDeviceID")
    if out and "Error" not in out:
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        return " | ".join(lines) if lines else "N/A"
    return "N/A"


def get_ram_serial():
    out = run_ps(
        "(Get-CimInstance Win32_PhysicalMemory | Select-Object -First 1).SerialNumber"
    )
    if out and "Error" not in out and out.strip():
        return out.strip()
    return "00000000"


def get_baseboard_serial():
    out = run_ps("(Get-CimInstance Win32_BaseBoard).SerialNumber")
    if out and "Error" not in out and out.strip():
        return out.strip()
    return "Default string"


# ─── PC Checks ────────────────────────────────────────────────────────────────

def check_uac():
    val = reg_read(winreg.HKEY_LOCAL_MACHINE,
                   r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
                   "EnableLUA")
    if val == 1:
        return "UAC is enabled", True
    else:
        return "UAC is disabled", False


def check_realtime_protection():
    out = run_ps("(Get-MpComputerStatus).RealTimeProtectionEnabled")
    if out.strip().lower() == "true":
        return "Real-Time Protection is enabled", True
    else:
        return "Real-Time Protection is disabled", False


def check_virtualization():
    out = run_ps(
        "(Get-CimInstance -ClassName Win32_DeviceGuard "
        "-Namespace root\\Microsoft\\Windows\\DeviceGuard)."
        "VirtualizationBasedSecurityStatus"
    )
    if out.strip() == "2":
        return "Virtualization is enabled", True
    elif out.strip() == "1":
        return "Virtualization is enabled (not running)", True
    else:
        return "Virtualization is disabled (Enable in BIOS)", False


def check_secure_boot():
    out = run_ps("Confirm-SecureBootUEFI")
    if out.strip().lower() == "true":
        return "Secure Boot is enabled", True
    else:
        return "Secure Boot is disabled (Enable in BIOS)", False


def check_faceit():
    faceit_paths = [
        os.path.join(os.environ.get("ProgramFiles", ""), "FACEIT AC", "faceit.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "FACEIT", "faceit.exe"),
    ]
    svc = run_ps("Get-Service -Name 'FACEIT' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status")
    if "Running" in svc:
        return "FaceIt Boot is enabled", True
    for p in faceit_paths:
        if os.path.exists(p):
            return "FaceIt is installed (service not running)", False
    return "FaceIt Boot is disabled", False


def check_vanguard():
    svc = run_ps("Get-Service -Name 'vgc' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status")
    if "Running" in svc:
        return "Vanguard is enabled", True
    svc2 = run_ps("Get-Service -Name 'vgk' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status")
    if "Running" in svc2:
        return "Vanguard is enabled", True
    vg_path = os.path.join(os.environ.get("ProgramFiles", ""), "Riot Vanguard")
    if os.path.exists(vg_path):
        return "Vanguard is installed (not running)", False
    return "Vanguard is not installed", False


# ─── Action Functions ─────────────────────────────────────────────────────────

def enable_hyperv():
    run_ps("Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -NoRestart")


def disable_hyperv():
    run_ps("Disable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -NoRestart")


def enable_uac():
    run_ps('Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" -Name "EnableLUA" -Value 1')


def disable_uac():
    run_ps('Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" -Name "EnableLUA" -Value 0')


def clean_network():
    cmds = [
        "ipconfig /flushdns",
        "ipconfig /release",
        "ipconfig /renew",
        "netsh winsock reset",
        "netsh int ip reset",
    ]
    for c in cmds:
        run_cmd(c)


def open_windows_utility():
    subprocess.Popen(
        ["powershell", "-NoProfile", "-Command", "irm https://christitus.com/win | iex"],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )


def enable_defender_control():
    run_ps('Set-MpPreference -DisableRealtimeMonitoring $false')


def disable_defender_control():
    run_ps('Set-MpPreference -DisableRealtimeMonitoring $true')


def enable_update_blocker():
    run_ps('Stop-Service -Name "wuauserv" -Force; Set-Service -Name "wuauserv" -StartupType Disabled')


def disable_update_blocker():
    run_ps('Set-Service -Name "wuauserv" -StartupType Manual; Start-Service -Name "wuauserv"')


def run_sfc_dism():
    """Run SFC and DISM repair in a visible console window."""
    subprocess.Popen(
        ["powershell", "-NoProfile", "-Command",
         "Write-Host 'Running DISM...' -ForegroundColor Cyan; "
         "DISM /Online /Cleanup-Image /RestoreHealth; "
         "Write-Host ''; Write-Host 'Running SFC...' -ForegroundColor Cyan; "
         "sfc /scannow; "
         "Write-Host ''; Write-Host 'Done! Press any key to close.' -ForegroundColor Green; "
         "$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')"],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )


def run_disk_cleanup():
    """Open Windows Disk Cleanup utility."""
    subprocess.Popen(["cleanmgr", "/d", "C:"], creationflags=subprocess.CREATE_NO_WINDOW)


def run_temp_cleaner():
    """Aggressively clean all temp/cache files."""
    temp = os.environ.get("TEMP", "")
    localappdata = os.environ.get("LOCALAPPDATA", "")
    run_ps(f'Remove-Item -Path "{temp}\\*" -Recurse -Force -ErrorAction SilentlyContinue')
    run_ps(f'Remove-Item -Path "C:\\Windows\\Temp\\*" -Recurse -Force -ErrorAction SilentlyContinue')
    run_ps(f'Remove-Item -Path "{localappdata}\\Temp\\*" -Recurse -Force -ErrorAction SilentlyContinue')
    run_ps('Remove-Item -Path "C:\\Windows\\Prefetch\\*" -Force -ErrorAction SilentlyContinue')
    run_ps(f'Remove-Item -Path "{localappdata}\\Microsoft\\Windows\\INetCache\\*" -Recurse -Force -ErrorAction SilentlyContinue')
    run_ps(f'Remove-Item -Path "{localappdata}\\CrashDumps\\*" -Recurse -Force -ErrorAction SilentlyContinue')


def set_dns_google():
    """Set DNS to Google (8.8.8.8 / 8.8.4.4)."""
    run_ps(
        '$a = Get-NetAdapter | Where-Object {$_.Status -eq "Up"} | Select-Object -First 1; '
        'Set-DnsClientServerAddress -InterfaceIndex $a.ifIndex -ServerAddresses ("8.8.8.8","8.8.4.4")'
    )


def set_dns_cloudflare():
    """Set DNS to Cloudflare (1.1.1.1 / 1.0.0.1)."""
    run_ps(
        '$a = Get-NetAdapter | Where-Object {$_.Status -eq "Up"} | Select-Object -First 1; '
        'Set-DnsClientServerAddress -InterfaceIndex $a.ifIndex -ServerAddresses ("1.1.1.1","1.0.0.1")'
    )


def set_dns_auto():
    """Reset DNS to automatic (DHCP)."""
    run_ps(
        '$a = Get-NetAdapter | Where-Object {$_.Status -eq "Up"} | Select-Object -First 1; '
        'Set-DnsClientServerAddress -InterfaceIndex $a.ifIndex -ResetServerAddresses'
    )


def open_startup_manager():
    """Open Task Manager on the Startup tab."""
    subprocess.Popen(["taskmgr", "/startup"], creationflags=subprocess.CREATE_NO_WINDOW)


def open_device_manager():
    """Open Device Manager."""
    subprocess.Popen(["devmgmt.msc"], creationflags=subprocess.CREATE_NO_WINDOW, shell=True)


def open_event_viewer():
    """Open Event Viewer."""
    subprocess.Popen(["eventvwr.msc"], creationflags=subprocess.CREATE_NO_WINDOW, shell=True)


def reset_firewall():
    """Reset Windows Firewall to defaults."""
    run_ps("netsh advfirewall reset")



def _hive_name(hive):
    """Convert a winreg hive constant to a registry path prefix."""
    mapping = {
        winreg.HKEY_CURRENT_USER: "HKEY_CURRENT_USER",
        winreg.HKEY_LOCAL_MACHINE: "HKEY_LOCAL_MACHINE",
    }
    return mapping.get(hive, "HKEY_CURRENT_USER")


def _reg_key_exists(hive, path):
    try:
        key = winreg.OpenKey(hive, path)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def _service_exists(name):
    out = run_ps(f'Get-Service -Name "{name}" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name')
    return bool(out.strip())


# All known trace definitions, grouped by category
TRACE_DEFINITIONS = {
    "EasyAntiCheat": {
        "folders": [
            ("{ProgramData}", "EasyAntiCheat"),
            ("{TEMP}", "EasyAntiCheat"),
        ],
        "registry": [
            (winreg.HKEY_CURRENT_USER, r"Software\EasyAntiCheat"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\EasyAntiCheat"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\EasyAntiCheat"),
        ],
        "services": ["EasyAntiCheat", "EasyAntiCheatSys"],
    },
    "BattlEye": {
        "folders": [
            ("{ProgramData}", "BattlEye"),
            ("{TEMP}", "BattlEye"),
        ],
        "registry": [
            (winreg.HKEY_CURRENT_USER, r"Software\BattlEye"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\BattlEye"),
        ],
        "services": ["BEService", "BEDaisy"],
    },
    "Riot / Vanguard / Valorant": {
        "folders": [
            ("{ProgramFiles}", "Riot Vanguard"),
            ("{ProgramFiles(x86)}", "Riot Vanguard"),
            ("{ProgramData}", "Riot Games"),
            ("{LOCALAPPDATA}", "Riot Games"),
            ("{APPDATA}", "Riot Games"),
            ("{LOCALAPPDATA}", "VALORANT"),
        ],
        "registry": [
            (winreg.HKEY_CURRENT_USER, r"Software\Riot Games"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Riot Games"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Riot Games"),
        ],
        "services": ["vgc", "vgk"],
    },
    "FACEIT": {
        "folders": [
            ("{ProgramFiles}", "FACEIT AC"),
            ("{LOCALAPPDATA}", "FACEIT"),
            ("{APPDATA}", "FACEIT"),
        ],
        "registry": [
            (winreg.HKEY_CURRENT_USER, r"Software\FACEIT"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\FACEIT"),
        ],
        "services": ["faceit"],
    },
    "Epic Games / Fortnite": {
        "folders": [
            ("{LOCALAPPDATA}", "FortniteGame"),
            ("{LOCALAPPDATA}", "EpicGamesLauncher"),
            ("{ProgramData}", "Epic"),
        ],
        "registry": [
            (winreg.HKEY_CURRENT_USER, r"Software\Epic Games"),
        ],
        "services": [],
    },
    "Steam / Valve / CS2": {
        "folders": [
            ("{LOCALAPPDATA}", "Steam"),
            ("{APPDATA}", "Steam"),
        ],
        "registry": [
            (winreg.HKEY_CURRENT_USER, r"Software\Valve"),
        ],
        "services": [],
    },
    "FiveM / CitizenFX": {
        "folders": [
            ("{LOCALAPPDATA}", "FiveM"),
            ("{APPDATA}", "FiveM"),
            ("{LOCALAPPDATA}", "CitizenFX"),
            ("{APPDATA}", "CitizenFX"),
        ],
        "registry": [
            (winreg.HKEY_CURRENT_USER, r"Software\CitizenFX"),
            (winreg.HKEY_CURRENT_USER, r"Software\FiveM"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\CitizenFX"),
        ],
        "services": [],
    },
    "Activision / COD / Blizzard": {
        "folders": [
            ("{LOCALAPPDATA}", "Activision"),
            ("{APPDATA}", "Activision"),
            ("{LOCALAPPDATA}", "Call of Duty"),
            ("{ProgramData}", "Blizzard Entertainment"),
            ("{LOCALAPPDATA}", "Blizzard Entertainment"),
            ("{APPDATA}", "Battle.net"),
            ("{LOCALAPPDATA}", "Battle.net"),
        ],
        "registry": [
            (winreg.HKEY_CURRENT_USER, r"Software\Activision"),
            (winreg.HKEY_CURRENT_USER, r"Software\Blizzard Entertainment"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Activision"),
        ],
        "services": [],
    },
    "EA / Origin / Apex": {
        "folders": [
            ("{LOCALAPPDATA}", "Electronic Arts"),
            ("{ProgramData}", "Electronic Arts"),
            ("{LOCALAPPDATA}", "Origin"),
            ("{APPDATA}", "Origin"),
            ("{ProgramData}", "Origin"),
        ],
        "registry": [
            (winreg.HKEY_CURRENT_USER, r"Software\Electronic Arts"),
            (winreg.HKEY_CURRENT_USER, r"Software\Origin"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Electronic Arts"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Electronic Arts"),
        ],
        "services": [],
    },
    "Ubisoft / R6": {
        "folders": [
            ("{LOCALAPPDATA}", "Ubisoft Game Launcher"),
            ("{ProgramFiles(x86)}", "Ubisoft"),
        ],
        "registry": [
            (winreg.HKEY_CURRENT_USER, r"Software\Ubisoft"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Ubisoft"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Ubisoft"),
        ],
        "services": [],
    },
    "Minecraft": {
        "folders": [
            ("{APPDATA}", ".minecraft"),
            ("{LOCALAPPDATA}", "Packages", "Microsoft.MinecraftUWP_8wekyb3d8bbwe"),
        ],
        "registry": [],
        "services": [],
    },
    "System Traces (Prefetch / Temp / Logs)": {
        "folders": [
            ("{LOCALAPPDATA}", "CrashDumps"),
            ("C:\\Windows", "Prefetch"),
            ("{APPDATA}", "Microsoft", "Windows", "Recent"),
        ],
        "registry": [],
        "services": [],
        "extra_actions": ["clear_temp", "clear_event_logs"],
    },
}

ENV_MAP = {
    "{APPDATA}": os.environ.get("APPDATA", ""),
    "{LOCALAPPDATA}": os.environ.get("LOCALAPPDATA", ""),
    "{ProgramData}": os.environ.get("ProgramData", ""),
    "{ProgramFiles}": os.environ.get("ProgramFiles", ""),
    "{ProgramFiles(x86)}": os.environ.get("ProgramFiles(x86)", ""),
    "{TEMP}": os.environ.get("TEMP", ""),
    "{USERPROFILE}": os.environ.get("USERPROFILE", ""),
}


def _resolve_folder(parts):
    """Resolve a folder tuple like ('{APPDATA}', 'Steam') to an actual path."""
    first = parts[0]
    resolved = ENV_MAP.get(first, first)
    return os.path.join(resolved, *parts[1:])


def scan_game_traces():
    """Scan for existing game traces. Returns dict of {category: details} for found items only."""
    found = {}
    for category, defs in TRACE_DEFINITIONS.items():
        details = {"folders": [], "registry": [], "services": [], "extra_actions": []}

        for folder_parts in defs.get("folders", []):
            path = _resolve_folder(folder_parts)
            if os.path.isdir(path):
                details["folders"].append(path)

        for hive, key_path in defs.get("registry", []):
            if _reg_key_exists(hive, key_path):
                details["registry"].append((hive, key_path))

        for svc in defs.get("services", []):
            if _service_exists(svc):
                details["services"].append(svc)

        details["extra_actions"] = defs.get("extra_actions", [])

        has_traces = details["folders"] or details["registry"] or details["services"]
        if has_traces or details["extra_actions"]:
            details["has_real_traces"] = bool(details["folders"] or details["registry"] or details["services"])
            found[category] = details

    return found


def delete_selected_traces(selected):
    """Delete traces for the given dict of {category: details}."""
    import shutil
    temp = os.environ.get("TEMP", "")

    for category, details in selected.items():
        for folder in details.get("folders", []):
            try:
                if os.path.isdir(folder):
                    shutil.rmtree(folder, ignore_errors=True)
            except Exception:
                pass

        for hive, key_path in details.get("registry", []):
            try:
                run_ps(f'Remove-Item -Path "Registry::{_hive_name(hive)}\\{key_path}" -Recurse -Force -ErrorAction SilentlyContinue')
            except Exception:
                pass

        for svc in details.get("services", []):
            run_ps(f'Stop-Service -Name "{svc}" -Force -ErrorAction SilentlyContinue')
            run_ps(f'sc.exe delete "{svc}" 2>$null')

        for action in details.get("extra_actions", []):
            if action == "clear_temp":
                run_ps(f'Remove-Item -Path "{temp}\\*" -Recurse -Force -ErrorAction SilentlyContinue')
            elif action == "clear_event_logs":
                run_ps('wevtutil cl Application 2>$null')
                run_ps('wevtutil cl System 2>$null')


# ─── Status Checks for Settings Page ─────────────────────────────────────────

def check_hyperv_status():
    """Returns True if Hyper-V is enabled."""
    out = run_ps("(Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V).State")
    return "Enabled" in out if out else False


def check_defender_status():
    """Returns True if real-time protection is enabled."""
    out = run_ps("(Get-MpComputerStatus).RealTimeProtectionEnabled")
    return out.strip().lower() == "true"


def check_update_blocker_status():
    """Returns True if Windows Update service is disabled (blocker ON)."""
    out = run_ps('(Get-Service -Name "wuauserv").StartType')
    return out.strip().lower() == "disabled"


def check_windows_activated():
    """Returns True if Windows is activated."""
    out = run_ps("(Get-CimInstance SoftwareLicensingProduct | Where-Object {$_.PartialProductKey}).LicenseStatus")
    return out.strip() == "1"


# ─── Download URLs ────────────────────────────────────────────────────────────

DOWNLOADS = {
    "Redistributables x64": {
        "desc": "This is needed for most applications to run properly",
        "url": "https://aka.ms/vs/17/release/vc_redist.x64.exe",
    },
    "Proton VPN": {
        "desc": "A Free VPN that is useful to have",
        "url": "https://protonvpn.com/download",
    },
    "DirectX": {
        "desc": "Most overlays use this.",
        "url": "https://www.microsoft.com/en-us/download/details.aspx?id=35",
    },
    "Windows 10 ISO": {
        "desc": "Good to have when needing to re-install windows.",
        "url": "https://www.microsoft.com/en-us/software-download/windows10ISO",
    },
    "Revo Uninstaller": {
        "desc": "A good tool used for cleaning traces of a game",
        "url": "https://www.revouninstaller.com/revo-uninstaller-free-download/",
    },
    ".NET Runtime": {
        "desc": "Required by many modern applications and games",
        "url": "https://dotnet.microsoft.com/en-us/download/dotnet",
    },
    "7-Zip": {
        "desc": "Free file archiver, better than WinRAR",
        "url": "https://www.7-zip.org/download.html",
    },
    "NVIDIA Drivers": {
        "desc": "Latest GeForce GPU drivers from NVIDIA",
        "url": "https://www.nvidia.com/Download/index.aspx",
    },
    "AMD Drivers": {
        "desc": "Latest Radeon GPU drivers from AMD",
        "url": "https://www.amd.com/en/support",
    },
    "HWiNFO": {
        "desc": "Detailed hardware info and sensor monitoring",
        "url": "https://www.hwinfo.com/download/",
    },
    "Process Explorer": {
        "desc": "Advanced task manager from Microsoft Sysinternals",
        "url": "https://learn.microsoft.com/en-us/sysinternals/downloads/process-explorer",
    },
    "Malwarebytes": {
        "desc": "Malware scanner and removal tool",
        "url": "https://www.malwarebytes.com/mwb-download",
    },
    "DDU (Display Driver Uninstaller)": {
        "desc": "Cleanly removes GPU drivers for fresh install",
        "url": "https://www.wagnardsoft.com/display-driver-uninstaller-DDU-",
    },
}


# ─── UI Components ────────────────────────────────────────────────────────────

class InfoCard(ctk.CTkFrame):
    """A card showing a title and a value, with a copy button."""

    def __init__(self, parent, title, value="Loading...", **kwargs):
        super().__init__(parent, fg_color=BG_CARD, corner_radius=10, border_width=1,
                         border_color=BORDER, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure((0, 1), weight=0)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=15, pady=(12, 0))
        header.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(header, text=title,
                                         font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                                         text_color=TEXT_PRIMARY, anchor="w")
        self.title_label.grid(row=0, column=0, sticky="ew")

        self.copy_btn = ctk.CTkButton(header, text="\u2398", width=28, height=28,
                                       fg_color="transparent", hover_color=BTN_HOVER,
                                       text_color=TEXT_SECONDARY, font=ctk.CTkFont(size=14),
                                       command=self._copy)
        self.copy_btn.grid(row=0, column=1, sticky="e", padx=(0, 0))

        self.value_label = ctk.CTkLabel(self, text=value,
                                         font=ctk.CTkFont(family="Segoe UI", size=12),
                                         text_color=TEXT_SECONDARY, anchor="nw",
                                         wraplength=380, justify="left")
        self.value_label.grid(row=1, column=0, columnspan=2, sticky="nw", padx=15, pady=(2, 12))

    def set_value(self, val):
        self.value_label.configure(text=val)

    def _copy(self):
        self.clipboard_clear()
        self.clipboard_append(self.value_label.cget("text"))
        original = self.copy_btn.cget("text")
        self.copy_btn.configure(text="\u2713")
        self.after(1200, lambda: self.copy_btn.configure(text=original))


class CheckCard(ctk.CTkFrame):
    """A card for a PC check: title, description, and a status dot."""

    def __init__(self, parent, title, buttons=None, **kwargs):
        super().__init__(parent, fg_color=BG_CARD, corner_radius=10, border_width=1,
                         border_color=BORDER, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=15, pady=(12, 0))
        header.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(header, text=title,
                                         font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                                         text_color=TEXT_PRIMARY, anchor="w")
        self.title_label.grid(row=0, column=0, sticky="w")

        self.dot = ctk.CTkLabel(header, text="\u25CF", font=ctk.CTkFont(size=18),
                                 text_color=TEXT_DIM, anchor="e")
        self.dot.grid(row=0, column=1, sticky="e", padx=(5, 0))

        self.desc_label = ctk.CTkLabel(self, text="Checking...",
                                        font=ctk.CTkFont(family="Segoe UI", size=11),
                                        text_color=TEXT_SECONDARY, anchor="w")
        self.desc_label.grid(row=1, column=0, sticky="w", padx=15, pady=(2, 4))

        if buttons:
            btn_frame = ctk.CTkFrame(self, fg_color="transparent")
            btn_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(4, 12))
            for i, (label, cmd) in enumerate(buttons):
                b = ctk.CTkButton(btn_frame, text=label, width=120, height=32,
                                   fg_color=BTN_BG, hover_color=BTN_HOVER,
                                   text_color=TEXT_PRIMARY,
                                   font=ctk.CTkFont(family="Segoe UI", size=12),
                                   corner_radius=6, command=cmd)
                b.grid(row=0, column=i, padx=(0, 8))
        else:
            self.desc_label.grid_configure(pady=(2, 12))

    def set_status(self, text, is_ok):
        self.desc_label.configure(text=text)
        self.dot.configure(text_color=GREEN_DOT if is_ok else RED_DOT)


class DownloadCard(ctk.CTkFrame):
    """A card for a downloadable tool."""

    def __init__(self, parent, title, desc, url, **kwargs):
        super().__init__(parent, fg_color=BG_CARD, corner_radius=10, border_width=1,
                         border_color=BORDER, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(self, text=title,
                                         font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                                         text_color=TEXT_PRIMARY, anchor="w")
        self.title_label.grid(row=0, column=0, sticky="w", padx=15, pady=(12, 0))

        self.desc_label = ctk.CTkLabel(self, text=desc,
                                        font=ctk.CTkFont(family="Segoe UI", size=11),
                                        text_color=TEXT_SECONDARY, anchor="w")
        self.desc_label.grid(row=1, column=0, sticky="w", padx=15, pady=(2, 4))

        self.dl_btn = ctk.CTkButton(self, text="Download", width=130, height=32,
                                     fg_color=BTN_BG, hover_color=BTN_HOVER,
                                     text_color=TEXT_PRIMARY,
                                     font=ctk.CTkFont(family="Segoe UI", size=12),
                                     corner_radius=6,
                                     command=lambda: webbrowser.open(url))
        self.dl_btn.grid(row=2, column=0, sticky="w", padx=15, pady=(4, 12))


class ActionCard(ctk.CTkFrame):
    """A card for a settings action with status indicator and smart button states."""

    def __init__(self, parent, title, desc, buttons=None, **kwargs):
        super().__init__(parent, fg_color=BG_CARD, corner_radius=10, border_width=1,
                         border_color=BORDER, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=15, pady=(12, 0))
        header.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(header, text=title,
                                         font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                                         text_color=TEXT_PRIMARY, anchor="w")
        self.title_label.grid(row=0, column=0, sticky="w")

        self.dot = ctk.CTkLabel(header, text="\u25CF", font=ctk.CTkFont(size=18),
                                 text_color=TEXT_DIM, anchor="e")
        self.dot.grid(row=0, column=1, sticky="e", padx=(5, 0))

        self.status_label = ctk.CTkLabel(self, text="Checking...",
                                          font=ctk.CTkFont(family="Segoe UI", size=11),
                                          text_color=TEXT_SECONDARY, anchor="w")
        self.status_label.grid(row=1, column=0, sticky="w", padx=15, pady=(2, 0))

        self.desc_label = ctk.CTkLabel(self, text=desc,
                                        font=ctk.CTkFont(family="Segoe UI", size=10),
                                        text_color=TEXT_DIM, anchor="w")
        self.desc_label.grid(row=2, column=0, sticky="w", padx=15, pady=(0, 4))

        self.buttons = {}
        if buttons:
            btn_frame = ctk.CTkFrame(self, fg_color="transparent")
            btn_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=(4, 12))
            for i, (label, cmd) in enumerate(buttons):
                b = ctk.CTkButton(btn_frame, text=label, width=130, height=32,
                                   fg_color=BTN_BG, hover_color=BTN_HOVER,
                                   text_color=TEXT_PRIMARY,
                                   font=ctk.CTkFont(family="Segoe UI", size=12),
                                   corner_radius=6, command=cmd)
                b.grid(row=0, column=i, padx=(0, 8))
                self.buttons[label] = b

    def set_status(self, text, is_enabled, enabled_btn_label=None, disabled_btn_label=None):
        """Update status text/dot and grey out the button that matches current state."""
        self.status_label.configure(text=text)
        self.dot.configure(text_color=GREEN_DOT if is_enabled else RED_DOT)

        if enabled_btn_label and disabled_btn_label:
            if is_enabled:
                # Already enabled: grey out Enable, highlight Disable
                if enabled_btn_label in self.buttons:
                    self.buttons[enabled_btn_label].configure(
                        fg_color=DISABLED_BG, text_color=DISABLED_FG,
                        hover_color=DISABLED_BG, state="disabled")
                if disabled_btn_label in self.buttons:
                    self.buttons[disabled_btn_label].configure(
                        fg_color=BTN_BG, text_color=TEXT_PRIMARY,
                        hover_color=BTN_HOVER, state="normal")
            else:
                # Already disabled: grey out Disable, highlight Enable
                if disabled_btn_label in self.buttons:
                    self.buttons[disabled_btn_label].configure(
                        fg_color=DISABLED_BG, text_color=DISABLED_FG,
                        hover_color=DISABLED_BG, state="disabled")
                if enabled_btn_label in self.buttons:
                    self.buttons[enabled_btn_label].configure(
                        fg_color=BTN_BG, text_color=TEXT_PRIMARY,
                        hover_color=BTN_HOVER, state="normal")


# ─── Trace Selection Dialog ───────────────────────────────────────────────────

class TraceSelectionDialog(ctk.CTkToplevel):
    """Dialog that shows found game traces with checkboxes for selective deletion."""

    def __init__(self, parent, found_traces):
        super().__init__(parent)
        self.title("Game Traces Found")
        self.configure(fg_color=BG_MAIN)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        width, height = 620, 520
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

        self.result = None
        self.found_traces = found_traces
        self.checkboxes = {}

        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color=BG_CARD, height=50, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="Select traces to remove",
                     font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                     text_color=TEXT_PRIMARY).pack(side="left", padx=15, pady=12)

        count = sum(1 for d in self.found_traces.values() if d.get("has_real_traces", False))
        ctk.CTkLabel(header, text=f"{count} categories found",
                     font=ctk.CTkFont(family="Segoe UI", size=12),
                     text_color=GREEN_DOT if count > 0 else TEXT_SECONDARY
                     ).pack(side="right", padx=15, pady=12)

        # Scrollable list of traces
        scroll = ctk.CTkScrollableFrame(self, fg_color=BG_MAIN,
                                         scrollbar_button_color=BG_CARD,
                                         scrollbar_button_hover_color=BTN_HOVER)
        scroll.pack(fill="both", expand=True, padx=10, pady=(10, 5))
        scroll.grid_columnconfigure(0, weight=1)

        row = 0
        for category, details in self.found_traces.items():
            card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=8,
                                 border_width=1, border_color=BORDER)
            card.grid(row=row, column=0, sticky="ew", pady=4, padx=4)
            card.grid_columnconfigure(1, weight=1)

            var = ctk.BooleanVar(value=True)
            cb = ctk.CTkCheckBox(card, text="", variable=var, width=24,
                                  fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                  border_color=BORDER, checkmark_color=TEXT_PRIMARY)
            cb.grid(row=0, column=0, rowspan=2, padx=(12, 6), pady=10)
            self.checkboxes[category] = var

            ctk.CTkLabel(card, text=category,
                         font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                         text_color=TEXT_PRIMARY, anchor="w"
                         ).grid(row=0, column=1, sticky="w", padx=(0, 10), pady=(10, 0))

            # Build detail string
            parts = []
            n_folders = len(details.get("folders", []))
            n_reg = len(details.get("registry", []))
            n_svc = len(details.get("services", []))
            n_extra = len(details.get("extra_actions", []))
            if n_folders:
                parts.append(f"{n_folders} folder{'s' if n_folders > 1 else ''}")
            if n_reg:
                parts.append(f"{n_reg} registry key{'s' if n_reg > 1 else ''}")
            if n_svc:
                parts.append(f"{n_svc} service{'s' if n_svc > 1 else ''}")
            if n_extra:
                parts.append(f"{n_extra} cleanup action{'s' if n_extra > 1 else ''}")
            detail_text = "  \u2022  ".join(parts) if parts else "Cleanup actions only"

            ctk.CTkLabel(card, text=detail_text,
                         font=ctk.CTkFont(family="Segoe UI", size=11),
                         text_color=TEXT_SECONDARY, anchor="w"
                         ).grid(row=1, column=1, sticky="w", padx=(0, 10), pady=(0, 10))

            row += 1

        # Footer buttons
        footer = ctk.CTkFrame(self, fg_color=BG_MAIN)
        footer.pack(fill="x", padx=10, pady=10)

        select_frame = ctk.CTkFrame(footer, fg_color="transparent")
        select_frame.pack(side="left")

        ctk.CTkButton(select_frame, text="Select All", width=90, height=32,
                       fg_color=BTN_BG, hover_color=BTN_HOVER,
                       text_color=TEXT_PRIMARY, font=ctk.CTkFont(size=12),
                       corner_radius=6, command=self._select_all
                       ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(select_frame, text="Deselect All", width=90, height=32,
                       fg_color=BTN_BG, hover_color=BTN_HOVER,
                       text_color=TEXT_PRIMARY, font=ctk.CTkFont(size=12),
                       corner_radius=6, command=self._deselect_all
                       ).pack(side="left")

        btn_frame = ctk.CTkFrame(footer, fg_color="transparent")
        btn_frame.pack(side="right")

        ctk.CTkButton(btn_frame, text="Cancel", width=100, height=36,
                       fg_color=BTN_BG, hover_color=BTN_HOVER,
                       text_color=TEXT_PRIMARY, font=ctk.CTkFont(size=13),
                       corner_radius=6, command=self._cancel
                       ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(btn_frame, text="Delete Selected", width=140, height=36,
                       fg_color="#c62828", hover_color="#e53935",
                       text_color=TEXT_PRIMARY,
                       font=ctk.CTkFont(size=13, weight="bold"),
                       corner_radius=6, command=self._confirm
                       ).pack(side="left")

    def _select_all(self):
        for var in self.checkboxes.values():
            var.set(True)

    def _deselect_all(self):
        for var in self.checkboxes.values():
            var.set(False)

    def _cancel(self):
        self.result = None
        self.destroy()

    def _confirm(self):
        self.result = {}
        for category, var in self.checkboxes.items():
            if var.get():
                self.result[category] = self.found_traces[category]
        self.destroy()


# ─── Main App ─────────────────────────────────────────────────────────────────

class SupportToolApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.withdraw()  # Hidden until splash closes
        self.title("Unnamedtech Support Tool")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self.configure(fg_color=BG_MAIN)

        # Set window icon (deferred to override customtkinter's default)
        self._icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Unnamed_multi.ico")
        if getattr(sys, "frozen", False):
            self._icon_path = os.path.join(sys._MEIPASS, "Unnamed_multi.ico")
        self.after(50, self._set_icon)

        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() - WINDOW_WIDTH) // 2
        y = (self.winfo_screenheight() - WINDOW_HEIGHT) // 2
        self.geometry(f"+{x}+{y}")

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)

        # Page container
        self.page_container = ctk.CTkFrame(self, fg_color=BG_MAIN)
        self.page_container.grid(row=0, column=0, sticky="nsew")
        self.page_container.grid_rowconfigure(0, weight=1)
        self.page_container.grid_columnconfigure(0, weight=1)

        self.pages = {}
        self.current_page = None

        self._build_pages()
        self._build_navbar()
        self._show_page("home")

        # Load data
        self.after(200, self._load_home_data)
        self.after(300, self._load_checks_data)
        self.after(400, self._load_settings_status)

    # ── Icon ──────────────────────────────────────────────────────────────
    def _set_icon(self):
        if os.path.exists(self._icon_path):
            self.iconbitmap(self._icon_path)
            self.after(100, lambda: self.iconbitmap(self._icon_path))

    # ── Pages ─────────────────────────────────────────────────────────────
    def _build_pages(self):
        self._build_home_page()
        self._build_checks_page()
        self._build_downloads_page()
        self._build_settings_page()

    def _show_page(self, name):
        if self.current_page == name:
            return
        for pname, frame in self.pages.items():
            frame.grid_remove()
        self.pages[name].grid(row=0, column=0, sticky="nsew")
        self.current_page = name
        # Update nav button highlights
        for btn_name, btn in self.nav_buttons.items():
            if btn_name == name:
                btn.configure(fg_color=BG_NAV_ACTIVE)
            else:
                btn.configure(fg_color=BG_NAVBAR_BTN)

    # ── HOME PAGE ─────────────────────────────────────────────────────────
    def _build_home_page(self):
        page = ctk.CTkScrollableFrame(self.page_container, fg_color=BG_MAIN,
                                       scrollbar_button_color=BG_CARD,
                                       scrollbar_button_hover_color=BTN_HOVER)
        self.pages["home"] = page

        page.grid_columnconfigure((0, 1), weight=1)

        self.home_cards = {}
        # (display_title, data_key, row, col) - shorter titles avoid truncation
        items = [
            ("Windows", "Windows Information", 0, 0),
            ("Main Drive Serial", "Main Drive Serial Number", 0, 1),
            ("CPU", "CPU Information", 1, 0),
            ("CPU Serial", "CPU Serial Number", 1, 1),
            ("GPU", "GPU Information", 2, 0),
            ("GPU Serial", "GPU Serial Number", 2, 1),
            ("RAM", "RAM Information", 3, 0),
            ("RAM Serial", "RAM Serial Number", 3, 1),
            ("Baseboard", "Baseboard Information", 4, 0),
            ("Baseboard Serial", "Baseboard Serial Number", 4, 1),
        ]
        for display_title, data_key, row, col in items:
            card = InfoCard(page, display_title)
            card.grid(row=row, column=col, padx=8, pady=6, sticky="nsew")
            self.home_cards[data_key] = card

    def _load_home_data(self):
        def worker():
            data = {
                "Windows Information": get_windows_info(),
                "CPU Information": get_cpu_info(),
                "GPU Information": get_gpu_info(),
                "RAM Information": get_ram_info(),
                "Baseboard Information": get_baseboard_info(),
                "Main Drive Serial Number": get_main_drive_serial(),
                "CPU Serial Number": get_cpu_serial(),
                "GPU Serial Number": get_gpu_serial(),
                "RAM Serial Number": get_ram_serial(),
                "Baseboard Serial Number": get_baseboard_serial(),
            }
            self.after(0, lambda: self._apply_home_data(data))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_home_data(self, data):
        for key, val in data.items():
            if key in self.home_cards:
                self.home_cards[key].set_value(val)

    # ── CHECKS PAGE ───────────────────────────────────────────────────────
    def _build_checks_page(self):
        page = ctk.CTkScrollableFrame(self.page_container, fg_color=BG_MAIN,
                                       scrollbar_button_color=BG_CARD,
                                       scrollbar_button_hover_color=BTN_HOVER)
        self.pages["checks"] = page
        page.grid_columnconfigure((0, 1), weight=1)

        self.check_cards = {}

        uac_card = CheckCard(page, "UAC",
                              buttons=[("Enable", lambda: self._run_action(enable_uac)),
                                       ("Disable", lambda: self._run_action(disable_uac))])
        uac_card.grid(row=0, column=0, padx=8, pady=6, sticky="nsew")
        self.check_cards["uac"] = uac_card

        rtp_card = CheckCard(page, "Real-Time Protection")
        rtp_card.grid(row=0, column=1, padx=8, pady=6, sticky="nsew")
        self.check_cards["rtp"] = rtp_card

        virt_card = CheckCard(page, "Virtualization")
        virt_card.grid(row=1, column=0, padx=8, pady=6, sticky="nsew")
        self.check_cards["virt"] = virt_card

        sb_card = CheckCard(page, "Secure Boot")
        sb_card.grid(row=1, column=1, padx=8, pady=6, sticky="nsew")
        self.check_cards["sb"] = sb_card

        faceit_card = CheckCard(page, "FaceIT Anti-Cheat")
        faceit_card.grid(row=2, column=0, padx=8, pady=6, sticky="nsew")
        self.check_cards["faceit"] = faceit_card

        vanguard_card = CheckCard(page, "Vanguard Anti-Cheat")
        vanguard_card.grid(row=2, column=1, padx=8, pady=6, sticky="nsew")
        self.check_cards["vanguard"] = vanguard_card

    def _load_checks_data(self):
        def worker():
            checks = {
                "uac": check_uac(),
                "rtp": check_realtime_protection(),
                "virt": check_virtualization(),
                "sb": check_secure_boot(),
                "faceit": check_faceit(),
                "vanguard": check_vanguard(),
            }
            self.after(0, lambda: self._apply_checks_data(checks))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_checks_data(self, checks):
        for key, (text, is_ok) in checks.items():
            if key in self.check_cards:
                self.check_cards[key].set_status(text, is_ok)

    # ── DOWNLOADS PAGE ────────────────────────────────────────────────────
    def _build_downloads_page(self):
        page = ctk.CTkScrollableFrame(self.page_container, fg_color=BG_MAIN,
                                       scrollbar_button_color=BG_CARD,
                                       scrollbar_button_hover_color=BTN_HOVER)
        self.pages["downloads"] = page
        page.grid_columnconfigure((0, 1), weight=1)

        items = list(DOWNLOADS.items())
        for idx, (name, info) in enumerate(items):
            row = idx // 2
            col = idx % 2
            card = DownloadCard(page, name, info["desc"], info["url"])
            card.grid(row=row, column=col, padx=8, pady=6, sticky="nsew")

    # ── SETTINGS PAGE ─────────────────────────────────────────────────────
    def _build_settings_page(self):
        page = ctk.CTkScrollableFrame(self.page_container, fg_color=BG_MAIN,
                                       scrollbar_button_color=BG_CARD,
                                       scrollbar_button_hover_color=BTN_HOVER)
        self.pages["settings"] = page
        page.grid_columnconfigure((0, 1), weight=1)

        self.settings_cards = {}

        hyperv = ActionCard(page, "HyperV",
                             "Needs to be enabled for most IPC Cheats",
                             buttons=[("Enable", lambda: self._run_setting_action(
                                          "hyperv", enable_hyperv)),
                                      ("Disable", lambda: self._run_setting_action(
                                          "hyperv", disable_hyperv))])
        hyperv.grid(row=0, column=0, padx=8, pady=6, sticky="nsew")
        self.settings_cards["hyperv"] = hyperv

        activation = ActionCard(page, "Windows Activation",
                                 "Used to activate Windows 10 licenses",
                                 buttons=[("Select...", lambda: self._run_action(
                                     lambda: run_ps("slmgr /dlv"))),
                                          ("Activate", lambda: self._run_action(
                                     lambda: run_ps("irm https://get.activated.win | iex")))])
        activation.grid(row=0, column=1, padx=8, pady=6, sticky="nsew")
        self.settings_cards["activation"] = activation

        defender = ActionCard(page, "Defender Control",
                               "Used to disable windows anti virus",
                               buttons=[("Enable", lambda: self._run_setting_action(
                                            "defender", enable_defender_control)),
                                        ("Disable", lambda: self._run_setting_action(
                                            "defender", disable_defender_control))])
        defender.grid(row=1, column=0, padx=8, pady=6, sticky="nsew")
        self.settings_cards["defender"] = defender

        updater = ActionCard(page, "Update Blocker",
                              "Used to disable automatic windows updates",
                              buttons=[("Enable", lambda: self._run_setting_action(
                                           "updater", enable_update_blocker)),
                                       ("Disable", lambda: self._run_setting_action(
                                           "updater", disable_update_blocker))])
        updater.grid(row=1, column=1, padx=8, pady=6, sticky="nsew")
        self.settings_cards["updater"] = updater

        network = ActionCard(page, "Network Cleaner",
                              "This cleans and renews network information on the PC",
                              buttons=[("Clean Network", lambda: self._run_action(clean_network))])
        network.grid(row=2, column=0, padx=8, pady=6, sticky="nsew")
        self.settings_cards["network"] = network

        traces = ActionCard(page, "Game Trace Cleaner",
                             "Scans for game & anti-cheat traces, lets you pick what to remove",
                             buttons=[("Scan Traces", lambda: self._scan_and_show_traces())])
        traces.grid(row=2, column=1, padx=8, pady=6, sticky="nsew")
        self.settings_cards["traces"] = traces

        utility = ActionCard(page, "Windows Utility",
                              "This opens a program that has many useful tools.",
                              buttons=[("Open Utility", lambda: self._run_action(open_windows_utility))])
        utility.grid(row=3, column=0, padx=8, pady=6, sticky="nsew")
        self.settings_cards["utility"] = utility

        sfc_dism = ActionCard(page, "SFC / DISM Repair",
                               "Scans and repairs corrupted Windows system files",
                               buttons=[("Run Repair", lambda: self._run_action(run_sfc_dism))])
        sfc_dism.grid(row=3, column=1, padx=8, pady=6, sticky="nsew")
        self.settings_cards["sfc_dism"] = sfc_dism

        dns = ActionCard(page, "DNS Changer",
                          "Change DNS for better speed or privacy",
                          buttons=[("Google", lambda: self._run_action(set_dns_google)),
                                   ("Cloudflare", lambda: self._run_action(set_dns_cloudflare)),
                                   ("Auto", lambda: self._run_action(set_dns_auto))])
        dns.grid(row=4, column=0, padx=8, pady=6, sticky="nsew")
        self.settings_cards["dns"] = dns

        temp_clean = ActionCard(page, "Temp File Cleaner",
                                 "Clears all temp files, prefetch, cache, and crash dumps",
                                 buttons=[("Clean Temp", lambda: self._run_action(run_temp_cleaner))])
        temp_clean.grid(row=4, column=1, padx=8, pady=6, sticky="nsew")
        self.settings_cards["temp_clean"] = temp_clean

        disk = ActionCard(page, "Disk Cleanup",
                           "Opens Windows built-in disk cleanup utility",
                           buttons=[("Open Cleanup", lambda: self._run_action(run_disk_cleanup))])
        disk.grid(row=5, column=0, padx=8, pady=6, sticky="nsew")
        self.settings_cards["disk"] = disk

        startup = ActionCard(page, "Startup Manager",
                              "Manage programs that run at Windows startup",
                              buttons=[("Open Manager", lambda: self._run_action(open_startup_manager))])
        startup.grid(row=5, column=1, padx=8, pady=6, sticky="nsew")
        self.settings_cards["startup"] = startup

        devmgr = ActionCard(page, "Device Manager",
                              "Open Windows Device Manager to manage drivers",
                              buttons=[("Open", lambda: self._run_action(open_device_manager))])
        devmgr.grid(row=6, column=0, padx=8, pady=6, sticky="nsew")
        self.settings_cards["devmgr"] = devmgr

        firewall = ActionCard(page, "Firewall Reset",
                               "Resets Windows Firewall rules to factory defaults",
                               buttons=[("Reset Firewall", lambda: self._run_action(reset_firewall))])
        firewall.grid(row=6, column=1, padx=8, pady=6, sticky="nsew")
        self.settings_cards["firewall"] = firewall

        evtview = ActionCard(page, "Event Viewer",
                              "Open Windows Event Viewer for troubleshooting logs",
                              buttons=[("Open Viewer", lambda: self._run_action(open_event_viewer))])
        evtview.grid(row=7, column=0, padx=8, pady=6, sticky="nsew")
        self.settings_cards["evtview"] = evtview


    def _load_settings_status(self):
        """Check current status of each toggleable setting in a background thread."""
        def worker():
            statuses = {}
            statuses["hyperv"] = check_hyperv_status()
            statuses["defender"] = check_defender_status()
            statuses["updater"] = check_update_blocker_status()
            statuses["activation"] = check_windows_activated()
            self.after(0, lambda: self._apply_settings_status(statuses))
        threading.Thread(target=worker, daemon=True).start()

    def _apply_settings_status(self, statuses):
        # HyperV
        is_on = statuses.get("hyperv", False)
        self.settings_cards["hyperv"].set_status(
            "Hyper-V is enabled" if is_on else "Hyper-V is disabled",
            is_on, enabled_btn_label="Enable", disabled_btn_label="Disable")

        # Defender
        is_on = statuses.get("defender", False)
        self.settings_cards["defender"].set_status(
            "Defender is enabled" if is_on else "Defender is disabled",
            is_on, enabled_btn_label="Enable", disabled_btn_label="Disable")

        # Update Blocker (enabled = updates blocked = service disabled)
        is_on = statuses.get("updater", False)
        self.settings_cards["updater"].set_status(
            "Updates are blocked" if is_on else "Updates are allowed",
            is_on, enabled_btn_label="Enable", disabled_btn_label="Disable")

        # Windows Activation
        is_on = statuses.get("activation", False)
        self.settings_cards["activation"].set_status(
            "Windows is activated" if is_on else "Windows is not activated",
            is_on, enabled_btn_label="Activate", disabled_btn_label=None)


    # ── Game Trace Scanner ──────────────────────────────────────────────
    def _scan_and_show_traces(self):
        self._show_toast("Scanning for traces...")

        def worker():
            found = scan_game_traces()
            self.after(0, lambda: self._open_trace_dialog(found))

        threading.Thread(target=worker, daemon=True).start()

    def _open_trace_dialog(self, found):
        if not found or not any(d.get("has_real_traces") for d in found.values()):
            self._show_toast("No game traces found!")
            return

        dialog = TraceSelectionDialog(self, found)
        self.wait_window(dialog)

        if dialog.result:
            self._show_toast(f"Deleting {len(dialog.result)} categories...")

            def do_delete():
                delete_selected_traces(dialog.result)
                self.after(0, lambda: self._show_toast(
                    f"Deleted {len(dialog.result)} trace categories!"))

            threading.Thread(target=do_delete, daemon=True).start()

    # ── Run action in thread ──────────────────────────────────────────────
    def _run_action(self, func):
        def worker():
            try:
                func()
                self.after(0, lambda: self._show_toast("Done!"))
            except Exception as e:
                self.after(0, lambda: self._show_toast(f"Error: {e}"))
        threading.Thread(target=worker, daemon=True).start()

    def _run_setting_action(self, setting_key, func):
        """Run a settings action, then refresh statuses so buttons update."""
        def worker():
            try:
                func()
                self.after(0, lambda: self._show_toast("Done!"))
                self.after(500, self._load_settings_status)
            except Exception as e:
                self.after(0, lambda: self._show_toast(f"Error: {e}"))
        threading.Thread(target=worker, daemon=True).start()

    def _show_toast(self, msg):
        toast = ctk.CTkLabel(self, text=msg,
                              font=ctk.CTkFont(family="Segoe UI", size=12),
                              text_color=TEXT_PRIMARY, fg_color=BG_CARD,
                              corner_radius=8, padx=16, pady=8)
        toast.place(relx=0.5, rely=0.05, anchor="center")
        self.after(2000, toast.destroy)

    # ── NAVBAR ────────────────────────────────────────────────────────────
    def _build_navbar(self):
        navbar = ctk.CTkFrame(self, fg_color=BG_NAVBAR, height=70, corner_radius=0)
        navbar.grid(row=1, column=0, sticky="ew")
        navbar.grid_propagate(False)
        navbar.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6, 7), weight=1)

        # Send to support button
        send_btn = ctk.CTkButton(navbar, text="SEND TO SUPPORT", width=150, height=38,
                                  fg_color=SEND_BTN_BG, hover_color=BTN_HOVER,
                                  text_color=SEND_BTN_FG,
                                  font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                  corner_radius=6, command=self._send_to_support)
        send_btn.grid(row=0, column=0, padx=(15, 10), pady=16, sticky="w")

        self.nav_buttons = {}

        nav_items = [
            ("home", "\u2302", 2),       # Home
            ("checks", "\u25A3", 3),     # Square (distinct from settings)
            ("downloads", "\u2913", 4),  # Download
            ("settings", "\u2699", 5),   # Gear
        ]

        for name, icon, col in nav_items:
            btn = ctk.CTkButton(navbar, text=icon, width=48, height=42,
                                 fg_color=BG_NAVBAR_BTN, hover_color=BTN_HOVER,
                                 text_color=TEXT_PRIMARY,
                                 font=ctk.CTkFont(size=20),
                                 corner_radius=8,
                                 command=lambda n=name: self._show_page(n))
            btn.grid(row=0, column=col, padx=4, pady=14)
            self.nav_buttons[name] = btn

        # Back button
        back_btn = ctk.CTkButton(navbar, text="\u276E", width=48, height=42,
                                  fg_color=BG_NAVBAR_BTN, hover_color=BTN_HOVER,
                                  text_color=TEXT_PRIMARY,
                                  font=ctk.CTkFont(size=18),
                                  corner_radius=8,
                                  command=self._go_back)
        back_btn.grid(row=0, column=6, padx=4, pady=14)

        # Branding with clickable links
        brand_frame = ctk.CTkFrame(navbar, fg_color="transparent")
        brand_frame.grid(row=0, column=7, padx=(0, 15), sticky="e")

        def make_link(text, url):
            lbl = ctk.CTkLabel(brand_frame, text=text,
                               font=ctk.CTkFont(family="Segoe UI", size=10),
                               text_color=TEXT_DIM, cursor="hand2")
            lbl.bind("<Button-1>", lambda e: webbrowser.open(url))
            lbl.bind("<Enter>", lambda e: lbl.configure(text_color=TEXT_SECONDARY))
            lbl.bind("<Leave>", lambda e: lbl.configure(text_color=TEXT_DIM))
            return lbl

        make_link("unnamedtech.cc", WEBSITE_URL).pack(side="left")
        ctk.CTkLabel(brand_frame, text="  |  ", font=ctk.CTkFont(size=10),
                     text_color=TEXT_DIM).pack(side="left")
        make_link("Discord", DISCORD_URL).pack(side="left")
        ctk.CTkLabel(brand_frame, text="  |  ", font=ctk.CTkFont(size=10),
                     text_color=TEXT_DIM).pack(side="left")
        make_link("Tutorial", TUTORIAL_URL).pack(side="left")

    def _go_back(self):
        pages_order = ["home", "checks", "downloads", "settings"]
        if self.current_page in pages_order:
            idx = pages_order.index(self.current_page)
            if idx > 0:
                self._show_page(pages_order[idx - 1])

    # ── Send to Support ───────────────────────────────────────────────────
    def _send_to_support(self):
        lines = ["=== Unnamedtech Support Tool Report ===\n"]

        # Home info
        for title, card in self.home_cards.items():
            val = card.value_label.cget("text")
            lines.append(f"{title}: {val}")

        lines.append("")

        # Checks
        for key, card in self.check_cards.items():
            desc = card.desc_label.cget("text")
            lines.append(f"{card.title_label.cget('text')}: {desc}")

        report = "\n".join(lines)
        self.clipboard_clear()
        self.clipboard_append(report)
        webbrowser.open(DISCORD_URL)
        self._show_toast("Report copied! Opening Discord...")


# ─── Splash Screen ────────────────────────────────────────────────────────────

def show_splash(parent):
    """Show boot splash for ~2 seconds. Returns the splash window."""
    splash = ctk.CTkToplevel(parent)
    splash.title("")
    splash.overrideredirect(True)
    w, h = 420, 180
    x = (splash.winfo_screenwidth() - w) // 2
    y = (splash.winfo_screenheight() - h) // 2
    splash.geometry(f"{w}x{h}+{x}+{y}")
    splash.configure(fg_color=BG_MAIN)
    splash.attributes("-topmost", True)

    frame = ctk.CTkFrame(splash, fg_color=BG_CARD, corner_radius=12,
                         border_width=1, border_color=BORDER)
    frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.9, relheight=0.85)

    ctk.CTkLabel(frame, text="Unnamedtech Support Tool",
                 font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
                 text_color=TEXT_PRIMARY).pack(pady=(24, 8))
    ctk.CTkLabel(frame, text="unnamedtech.cc",
                 font=ctk.CTkFont(family="Segoe UI", size=13),
                 text_color=TEXT_DIM).pack(pady=(0, 24))

    splash.update()
    return splash


# ─── Entry Point ──────────────────────────────────────────────────────────────

def request_admin():
    if getattr(sys, "frozen", False):
        exe = sys.executable
    else:
        exe = sys.executable
    params = " ".join([f'"{a}"' for a in sys.argv])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)


def main():
    if not is_admin():
        try:
            request_admin()
            sys.exit(0)
        except Exception:
            pass

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    app = SupportToolApp()
    splash = show_splash(app)

    def _on_splash_done():
        try:
            splash.destroy()
        except tk.TclError:
            pass
        app.deiconify()
        app.focus_force()

    splash.after(2000, _on_splash_done)
    app.mainloop()


if __name__ == "__main__":
    main()
