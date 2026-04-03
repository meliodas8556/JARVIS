# JARVIS Neural AI Interface - Complete Setup Guide

## 🚀 Quick Start

### Windows Users
```cmd
jarvis.bat
```
Or via PowerShell:
```powershell
.\jarvis.ps1
```
Or from Start Menu: Search "JARVIS" after setup

### macOS Users
```bash
./jarvis.sh
```
Or from Spotlight: Search "JARVIS"

### Linux Users
```bash
./jarvis.sh
```
Or from application menu: Search "JARVIS"

---

## 📦 Installation

### One-Time Setup (Recommended)
```bash
python3 jarvis-setup.py
```

This will:
- ✅ Register JARVIS as a system application
- ✅ Create desktop/Start Menu shortcuts
- ✅ Set up proper environment variables
- ✅ Verify all dependencies

### What Gets Installed
- **Linux**: `.desktop` file in `~/.local/share/applications/`
- **macOS**: App bundle at `~/Applications/JARVIS.app`
- **Windows**: Start Menu shortcut + registry entry

---

## 📂 File Structure

```
JARVIS/
├── JARVIS.py                          # Main application
├── jarvis.sh                          # Unix launcher
├── jarvis.bat                         # Windows batch launcher
├── jarvis.ps1                         # Windows PowerShell launcher
├── jarvis-setup.py                    # Setup & registration script
├── jarvis_logo.svg                    # Futuristic logo
├── SETUP_README.md                    # Setup instructions
├── CROSS_PLATFORM_COMPATIBILITY.md    # OS compatibility details
└── README.md                          # This file
```

---

## 🎨 Futuristic Logo

The application features a custom SVG logo with:
- Pure neon colors (cyan #00ffff, green #66ff99, red #ff3366)
- Hexagonal neural core design
- Dynamic scanning lines
- Professional tech aesthetic

Logo appears in:
- Application launcher icons
- Desktop shortcuts
- Start Menu entries
- Taskbar (when running)

---

## 🌍 Cross-Platform Features

### Universal Support

| Feature | Windows | macOS | Linux |
|---------|---------|-------|-------|
| Local AI (Ollama) | ✅ | ✅ | ✅ |
| Terminal Execution | ✅ | ✅ | ✅ |
| Command Execution | ✅ | ✅ | ✅ |
| File Operations | ✅ | ✅ | ✅ |
| Security Scanning | ✅ | ✅ | ✅ |
| Notifications | ✅ | ✅ | ✅ |
| Screen Capture | ✅ | ✅ | ✅ |
| OCR (Optional) | ✅ | ✅ | ✅ |

### OS-Specific Optimizations

**Windows:**
- PowerShell 7+ for modern shell features
- UAC elevation for privileged operations
- Windows Defender integration
- WMI for detailed metrics
- Registry integration for app search

**macOS:**
- Native Spotlight integration
- Launchd for process management
- sysctl for system metrics
- osascript for native notifications
- App bundle with proper metadata

**Linux:**
- XDG Desktop integration
- Wayland session detection
- systemd support
- Traditional shell compatibility
- Multiple distro support

---

## 🔧 Environment Variables

When launched via official launchers, these variables are set:

```bash
JARVIS_HOME         # Installation directory
JARVIS_OS           # Operating system (windows|linux|macos)
JARVIS_VERSION      # Current version (2026.1)
JARVIS_LAUNCHER     # Set to 1 if using official launcher
```

Access these in JARVIS code:
```python
import os
home = os.getenv("JARVIS_HOME")
os_type = os.getenv("JARVIS_OS")
```

---

## 📋 System Requirements

### Minimum
- **Python**: 3.8 or higher
- **RAM**: 512 MB
- **Disk**: 500 MB
- **OS**: Windows 10+, macOS 10.13+, Linux 2021+

### Recommended
- **Python**: 3.10 or higher
- **RAM**: 2+ GB
- **Disk**: 2+ GB (for AI models)
- **Internet**: For initial model downloads

### Optional Dependencies
- **Ollama**: Local AI models
- **Pillow**: Screen capture
- **Tesseract**: OCR
- **WeasyPrint**: PDF export
- **pyttsx3**: Text-to-speech
- **SpeechRecognition**: Voice input

Install optional packages:
```bash
pip install pillow tesseract weasyprint pyttsx3 SpeechRecognition
```

---

## 🎯 Usage Modes

### Mode 1: Application Launcher

**Most User-Friendly**

- Windows: Start Menu → Search "JARVIS"
- macOS: Spotlight → Search "JARVIS"
- Linux: Application menu → Search "JARVIS"

**Benefits:**
- ✅ Integrated with OS
- ✅ Easy to find and launch
- ✅ Proper icon display
- ✅ Environment configured

### Mode 2: Terminal/Shell

**For Advanced Users**

```bash
# Launch from terminal
./jarvis.sh              # Unix-like
jarvis.bat              # Windows (cmd.exe)
.\jarvis.ps1            # Windows (PowerShell)

# Launch from anywhere
python3 /path/to/JARVIS.py

# With arguments (if supported)
./jarvis.sh --headless
```

### Mode 3: Python Import

**For Developers**

```python
import sys
sys.path.insert(0, '/path/to/JARVIS')
import JARVIS
```

---

## 🚨 Troubleshooting

### JARVIS Doesn't Appear in Application Menu

**Linux:**
```bash
# Refresh desktop database
update-desktop-database ~/.local/share/applications

# Verify .desktop file exists
cat ~/.local/share/applications/jarvis.desktop
```

**macOS:**
```bash
# Reindex Spotlight
mdimport ~/Applications/JARVIS.app

# Verify app permissions
xattr -lr ~/Applications/JARVIS.app
```

**Windows:**
```cmd
# Re-run setup with admin privileges
python jarvis-setup.py

# Or manually update Start Menu
python jarvis-setup.py --force-register
```

### Python Not Found

**Any OS:**
```bash
# Check Python installation
python3 --version

# On Windows, try:
py --version
```

**Windows Specific:**
- Download from https://www.python.org/downloads/
- Use Windows Package Manager: `winget install Python.Python.3.12`
- Use Microsoft Store search for "Python"

**macOS:**
```bash
brew install python3
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt update
sudo apt install python3 python3-pip
```

### Terminal Features Not Working

- Ensure shell/PowerShell is available
- Windows: PowerShell should be installed by default
- macOS/Linux: Verify `echo $SHELL` shows a valid shell
- Check file permissions: `ls -l jarvis.sh`

### Launcher Not Finding JARVIS.py

- Ensure JARVIS.py is in the same directory as launcher scripts
- On Windows, verify paths don't contain spaces or special characters
- Check relative vs absolute paths in launcher scripts

### GUI Display Issues

- Ensure Tkinter is installed
- Linux: `sudo apt install python3-tk`
- macOS: Should come with Python
- Windows: Included with Python installer

---

## 🔐 Security Features

### Built-In Security

- **Link Guard**: Blocks suspicious URLs before opening
- **File Scanning**: Integrates with platform-specific malware scanners
- **Sandboxed Execution**: Terminal runs in isolated context
- **Clipboard Protection**: Monitors clipboard for threats
- **Cryptographic Verification**: Validates downloaded models

### Windows-Specific
- Windows Defender integration for file scanning
- UAC elevation for sensitive operations
- Registry security checks
- PowerShell execution policy compliance

### macOS-Specific
- Gatekeeper compatibility
- Code signature verification
- Extended attributes preservation
- Native security framework integration

### Linux-Specific
- ClamAV integration (optional)
- AppArmor profile (if available)
- SELinux compliance (if available)
- iptables/firewall coordination

---

## 🎨 Customization

### Themes

JARVIS supports three color themes:

1. **Cyan** (Default): Pure neon blue
2. **Ice**: Bright white-cyan hybrid
3. **Red Alert**: Warning/hacker red

Switch themes in-application via UI settings.

### Configuration

Main config file: `~/.jarvis_ultra_config.json`

```json
{
  "theme": "cyan",
  "model": "qwen2.5",
  "boot_sound_enabled": false,
  "boot_fade_enabled": true,
  "terminal_lines_limit": 300
}
```

Edit directly or use JARVIS UI.

### Custom Logos

Replace `jarvis_logo.svg` with your own SVG file to customize branding.

---

## 📊 Performance Tips

### For Better Performance

1. **Close Other Applications**
   - Frees up RAM for AI models
   - Reduces CPU contention

2. **Use Lightweight Models**
   - Default: `qwen2.5` (good balance)
   - Fast: `small-7b` or similar
   - Powerful: `llama3` or larger

3. **Pre-Download Models**
   ```bash
   ollama pull qwen2.5
   ```

4. **Disable Animations** (if needed)
   - Settings → disable boot fade/scanlines
   - Frees GPU for model inference

### System Resource Usage

- **Idle**: ~150-200 MB RAM
- **Active Chat**: ~300-400 MB (before model loading)
- **Running Model**: +2GB+ (depends on model size)
- **CPU**: <5% idle, 40-80% during inference

---

## 🔄 Updating JARVIS

### Check Version
```bash
python3 -c "import JARVIS; print(JARVIS.APP_TITLE)"
```

### Update Procedure
1. Backup config: `cp ~/.jarvis_ultra_config.json ~/.jarvis_ultra_config.json.bak`
2. Replace JARVIS.py with newer version
3. Run setup: `python3 jarvis-setup.py`
4. Restart JARVIS

### Rollback
```bash
cp ~/.jarvis_ultra_config.json.bak ~/.jarvis_ultra_config.json
# Use previous JARVIS.py version
```

---

## 📞 Support & Reporting Issues

### Debug Mode

Run JARVIS with verbose output:
```bash
python3 JARVIS.py 2>&1 | tee jarvis_debug.log
```

Check the generated `jarvis_debug.log` file for errors.

### Gathering Information

When reporting issues, include:
1. OS and version: `uname -a` (Unix) or `systeminfo` (Windows)
2. Python version: `python3 --version`
3. JARVIS version: Check UI or config file
4. Error messages: Copy from terminal/log
5. JARVIS_HOME setting: `echo $JARVIS_HOME`

---

## 🎓 Learning Resources

### JARVIS Features

- **Local AI**: Uses Ollama for offline inference
- **Terminal**: Full command execution capability
- **Chat Interface**: Conversation with AI
- **Security**: Built-in protection against threats
- **Screen Capture**: Screenshot and analyze images
- **File Management**: Browse and manage files

### Getting Started

1. Launch JARVIS
2. Select AI model (default: qwen2.5)
3. Type commands or ask questions
4. Use terminal for advanced operations

---

## 📄 License & Credits

JARVIS Neural AI Interface v2026

Built with:
- Python 3.8+
- Tkinter (GUI)
- Ollama (AI)
- Open-source tools

---

## 🌟 Changelog

### v2026.1 (Current)
- ✅ Full cross-platform support (Windows/macOS/Linux)
- ✅ Official application launchers (.sh/.bat/.ps1)
- ✅ System application registration (all OS)
- ✅ Futuristic SVG logo
- ✅ Enhanced UI modernization (pure neon colors)
- ✅ 100% feature compatibility across platforms

### v2025.12
- Windows compatibility improvements
- OS detection system
- Terminal cross-platform support

---

**Enjoy JARVIS!** 🚀
