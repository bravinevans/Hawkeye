# HAWKEYE — SEE MORE. DO MORE.

Native GTK4 + VTE terminal environment engineered for Arch Linux.

![Hawkeye Screenshot](assets/screenshots/hawkeye.png)

## Features
- **Six Master Visual Identities + Custom Theme Studio**: Dark Professional, Cyberpunk Neon, Amber Tactical, Dracula Inspired, Light Modern, and Matrix Terminal — plus live color pickers, transparency, corner radius, and custom skin saving.
- **Multi-Tab & Recursive Split Workspace**: Open tabs (`Ctrl+Shift+T`), split horizontally/vertically (`Ctrl+Shift+D` / `Ctrl+Shift+E`), close panes (`Ctrl+Shift+X`), search scrollback (`Ctrl+Shift+F`), drag-and-drop paths, and restore sessions across restarts.
- **Home Hero & Live System Telemetry**: Hawk emblem, neofetch-style system summary, ANSI palette bar, and live Cairo sparklines for CPU, RAM, Disk, and Network I/O.
- **BYOK Helper Studio & Drawer**: Connect your own OpenRouter, Groq, Google Gemini, OpenAI, or local Ollama endpoint to write code, edit files, and inject commands directly into your shell.

## Installation Setup (Arch Linux)

### 1. Clone the repository
    git clone https://github.com/bravinevans/Hawkeye.git
    cd Hawkeye

### 2. Install runtime dependencies
    sudo pacman -S --needed python gtk4 vte4 python-gobject python-cairo python-psutil
    # Optional:
    # sudo pacman -S --needed python-keyring yay

### 3. Run locally
    python3 main.py

### 4. Build and install system-wide (`PKGBUILD`)
    cd packaging
    makepkg -si
    gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor 2>/dev/null || true
