# Unnamedtech Support Tool

A Windows system diagnostics and support utility with a dark-themed GUI.

## Features

- **Home** — System info (Windows, CPU, GPU, RAM, baseboard) and serial numbers
- **PC Checks** — UAC, Real-Time Protection, Virtualization, Secure Boot, FaceIT, Vanguard status
- **Downloads** — Quick links to useful tools (Redistributables, DirectX, VPN, etc.)
- **Settings** — HyperV, Defender, Update Blocker, Network Cleaner, Game Trace Cleaner, SFC/DISM, DNS Changer, and more

## Requirements

- Windows 10 or 11
- Run as Administrator for full functionality

## Build

```bash
pip install -r requirements.txt
python -m PyInstaller --onefile --noconsole --name "Unnamedtech Support Tool" --uac-admin --icon="Unnamed_multi.ico" --add-data="Unnamed_multi.ico;." --collect-all customtkinter support_tool.py
```

Or run `build.bat`.

Output: `dist\Unnamedtech Support Tool.exe`

## Usage

Run the .exe — no Python or dependencies required. The tool is self-contained.
