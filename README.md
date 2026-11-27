# HAWKEYE — SEE MORE. DO MORE.

A fast, customizable terminal workspace built natively for Arch Linux using GTK4 and VTE.

Hawkeye combines a real multi-tab, split-pane Linux shell with live system telemetry, six visual themes (plus a live theme editor), and an optional AI Helper that can write code, edit files, and send commands straight to your terminal using your own API key.

![Hawkeye Screenshot](assets/screenshots/hawkeye.png)

## What You Get

- **Real Shell, Split & Tabbed:** Run `bash`, `zsh`, or any configured shell inside recursive horizontal/vertical split panes and multiple tabs. Drag and drop files straight into the prompt, search scrollback output (`Ctrl+Shift+F`), and pick up where you left off with automatic session restore.
- **Six Themes + Custom Theme Studio:** Switch on the fly between *Cyberpunk Neon*, *Dark Professional*, *Dracula Inspired*, *Amber Tactical*, *Matrix Terminal*, and *Light Modern* without restarting your running commands—or dial in your own colors, transparency, and corner radius.
- **Built-In System Telemetry & Home View:** Check CPU, RAM, disk usage, and live network speeds right from the status bar, or open the **Home** dashboard for a neofetch-style system overview and live resource graphs.
- **File Browser & Command History Search:** Browse directories, preview files, and search past shell commands without leaving the window.
- **BYOK AI Helper (Optional):** Bring your own free or paid API key to generate scripts, edit configuration files, or troubleshoot errors, then inject or run commands with one click. No key is required to use the terminal.

## Installation (Arch Linux)

### Option 1: Install System-Wide via `PKGBUILD` (Recommended)

1. **Install the required Arch packages:**

       sudo pacman -S --needed git base-devel python gtk4 vte4 python-gobject python-cairo python-psutil

   *(Optional: install `python-keyring` so your Helper API key is stored in your system keyring.)*

2. **Clone the repository and build the package:**

       git clone https://github.com/bravinevans/Hawkeye.git
       cd Hawkeye/packaging
       makepkg -si

3. **Launch Hawkeye:**
   Open **HAWKEYE** from your application menu or run `hawkeye` in any terminal.

### Option 2: Run Directly Without Installing

    git clone https://github.com/bravinevans/Hawkeye.git
    cd Hawkeye
    python3 main.py

## Configuring the AI Helper (BYOK)

Hawkeye does not ship with a shared or hardcoded API key. Everything in the terminal works out of the box, and you can connect your own AI provider whenever you want:

1. Open the **Helper** tab in the left sidebar (or press `Ctrl+Shift+A` to open the side drawer and click **API Setup**).
2. Click one of the built-in provider presets (**OpenRouter**, **Groq**, **Gemini**, **OpenAI**, or **Ollama**) to pre-fill the endpoint URL and default model—or enter any OpenAI-compatible `/v1/chat/completions` URL and model ID manually.
3. Paste your personal API key into the key field (leave blank if using a local **Ollama** server at `http://localhost:11434/v1/chat/completions`).
4. Click **Save Key**. Your endpoint and model are saved to `~/.config/hawkeye/user_settings.toml`, and your API key is stored securely via the system keyring (`python-keyring`) with local file fallback.
5. Type a request (e.g., *"Write a bash script to clean old pacman cache"* or *"Edit config.toml to use zsh"*), then click **Type in Terminal** to preview the command at your prompt or **Type & Run** to execute it immediately.

## Essential Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl+Shift+T` | Open a new terminal tab |
| `Ctrl+Shift+W` | Close the current tab |
| `Ctrl+Shift+D` | Split active pane horizontally |
| `Ctrl+Shift+E` | Split active pane vertically |
| `Ctrl+Shift+X` | Close active split pane |
| `Ctrl+Shift+F` | Search inside terminal output |
| `Ctrl+Shift+A` | Toggle the Helper side drawer |
| `Ctrl+Shift+P` | Open the Command Palette |
| `Ctrl+B` | Collapse or expand the sidebar |
| `Ctrl+,` | Open Settings & Theme Studio |

## License

MIT — see [LICENSE](LICENSE) for details.
