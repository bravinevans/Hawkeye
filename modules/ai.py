import json
import re
import threading
import urllib.error
import urllib.request
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib

from core.secrets import load_api_key, save_api_key

PROVIDER_PRESETS = [
    ("OpenRouter", "https://openrouter.ai/api/v1/chat/completions", "google/gemini-2.0-flash-exp:free"),
    ("Groq", "https://api.groq.com/openai/v1/chat/completions", "llama-3.3-70b-versatile"),
    ("Gemini", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "gemini-2.5-flash"),
    ("OpenAI", "https://api.openai.com/v1/chat/completions", "gpt-4o-mini"),
    ("Ollama", "http://localhost:11434/v1/chat/completions", "llama3.2"),
]


class HawkeyeHelperPanel(Gtk.Box):
    """Full AI Coding, File-Editing & Shell Assistant (BYOK)."""

    def __init__(self, on_inject_command, on_save_ai_config, config: dict | None = None, full_page: bool = False):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.on_inject_command = on_inject_command
        self.on_save_ai_config = on_save_ai_config
        self.config = config or {}
        self.full_page = full_page
        has_key = bool(load_api_key())

        if full_page:
            self.set_margin_top(20)
            self.set_margin_bottom(20)
            self.set_margin_start(24)
            self.set_margin_end(24)
            self.set_hexpand(True)
        else:
            self.add_css_class("hawkeye-sidebar")
            self.set_size_request(285, -1)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title = Gtk.Label(label="HAWKEYE // HELPER STUDIO" if full_page else "HAWKEYE // HELPER")
        title.add_css_class("hawkeye-brand")
        title.set_xalign(0.0)
        title.set_hexpand(True)

        self.cfg_toggle_btn = Gtk.Button(label="Edit Key" if has_key else "API Setup")
        self.cfg_toggle_btn.add_css_class("header-btn")
        self.cfg_toggle_btn.connect("clicked", lambda *_: self._toggle_config_box())

        header.append(title)
        header.append(self.cfg_toggle_btn)
        self.append(header)

        subtitle = Gtk.Label(
            label="Write code, edit files, debug shell output, or generate Arch Linux commands with your personal AI key."
        )
        subtitle.add_css_class("hawkeye-tagline")
        subtitle.set_xalign(0.0)
        subtitle.set_wrap(True)
        self.append(subtitle)

        # BYOK API Configuration Card: open if no key saved yet, collapsed if already saved
        self.config_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.config_card.add_css_class("panel-card")
        self.config_card.set_visible(not has_key)
        self._build_api_setup_ui(self.config_card)
        self.append(self.config_card)

        # Prompt input row
        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.prompt_entry = Gtk.Entry()
        self.prompt_entry.set_placeholder_text("Write a Python script, edit a config file, explain an error...")
        self.prompt_entry.add_css_class("hawkeye-input")
        self.prompt_entry.set_hexpand(True)
        self.prompt_entry.connect("activate", lambda *_: self._handle_ask())

        self.ask_btn = Gtk.Button(label="Send")
        self.ask_btn.add_css_class("accent-btn")
        self.ask_btn.connect("clicked", lambda *_: self._handle_ask())

        input_row.append(self.prompt_entry)
        input_row.append(self.ask_btn)
        self.append(input_row)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(scrolled)

        self.results_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        scrolled.set_child(self.results_box)

        self.refresh_status()

    def _build_api_setup_ui(self, container: Gtk.Box) -> None:
        hdr = Gtk.Label(label="HELPER API CONFIGURATION (BRING YOUR OWN KEY)")
        hdr.add_css_class("hawkeye-tagline")
        hdr.set_xalign(0.0)
        container.append(hdr)

        preset_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        for label, url, model in PROVIDER_PRESETS:
            p_btn = Gtk.Button(label=label)
            p_btn.add_css_class("flat-btn")
            p_btn.connect("clicked", lambda *_, u=url, m=model: self._apply_preset(u, m))
            preset_row.append(p_btn)
        container.append(preset_row)

        ai_cfg = self.config.get("ai", {})

        self.url_entry = Gtk.Entry()
        self.url_entry.add_css_class("hawkeye-input")
        self.url_entry.set_placeholder_text("OpenAI-compatible /chat/completions URL")
        self.url_entry.set_text(ai_cfg.get("api_url", "https://openrouter.ai/api/v1/chat/completions"))

        self.model_entry = Gtk.Entry()
        self.model_entry.add_css_class("hawkeye-input")
        self.model_entry.set_placeholder_text("Model ID")
        self.model_entry.set_text(ai_cfg.get("model", "google/gemini-2.0-flash-exp:free"))

        self.key_entry = Gtk.PasswordEntry()
        self.key_entry.set_show_peek_icon(True)
        self.key_entry.set_property("placeholder-text", "Paste your free or paid API key...")
        existing_key = load_api_key()
        if existing_key:
            self.key_entry.set_text(existing_key)

        save_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        save_btn = Gtk.Button(label="Save Key")
        save_btn.add_css_class("accent-btn")
        save_btn.connect("clicked", lambda *_: self._save_ai())

        self.ai_status_lbl = Gtk.Label(
            label="API key active in secure storage." if existing_key else "No API key configured yet."
        )
        self.ai_status_lbl.add_css_class("hawkeye-tagline")
        self.ai_status_lbl.set_wrap(True)

        save_row.append(save_btn)
        save_row.append(self.ai_status_lbl)

        container.append(self.url_entry)
        container.append(self.model_entry)
        container.append(self.key_entry)
        container.append(save_row)

    def _toggle_config_box(self) -> None:
        self.config_card.set_visible(not self.config_card.get_visible())

    def _apply_preset(self, url: str, model: str) -> None:
        self.url_entry.set_text(url)
        self.model_entry.set_text(model)

    def _save_ai(self) -> None:
        url = self.url_entry.get_text().strip()
        model = self.model_entry.get_text().strip()
        key = self.key_entry.get_text().strip()
        backend = save_api_key(key)
        self.on_save_ai_config(url, model)
        self.ai_status_lbl.set_text(f"Saved ({backend})." if key else "Key cleared.")
        self.cfg_toggle_btn.set_label("Edit Key" if key else "API Setup")
        if key:
            self.config_card.set_visible(False)
        self.refresh_status()

    def refresh_status(self) -> None:
        self._clear_results()
        has_key = bool(load_api_key())
        self.cfg_toggle_btn.set_label("Edit Key" if has_key else "API Setup")
        if has_key:
            self.config_card.set_visible(False)
        status = (
            "Helper AI connected. Ask me to write code, edit files in place, explain commands, or troubleshoot errors."
            if has_key
            else "No personal AI API key configured. Add your free or paid key in API Setup above to unlock full coding, file editing, and chat."
        )
        lbl = Gtk.Label(label=status)
        lbl.add_css_class("hawkeye-tagline")
        lbl.set_xalign(0.0)
        lbl.set_wrap(True)
        self.results_box.append(lbl)

    def _clear_results(self) -> None:
        child = self.results_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.results_box.remove(child)
            child = nxt

    def _handle_ask(self) -> None:
        query = self.prompt_entry.get_text().strip()
        if not query:
            return
        self.ask_btn.set_sensitive(False)
        self._clear_results()
        lbl = Gtk.Label(label="Thinking...")
        lbl.add_css_class("hawkeye-tagline")
        lbl.set_xalign(0.0)
        self.results_box.append(lbl)
        threading.Thread(target=self._worker, args=(query,), daemon=True).start()

    def _worker(self, query: str) -> None:
        cards = self._query_llm(query)
        GLib.idle_add(self._on_worker_done, cards)

    def _on_worker_done(self, cards: list[dict]) -> None:
        self.ask_btn.set_sensitive(True)
        self._render_cards(cards)

    def _query_llm(self, query: str) -> list[dict]:
        api_key = load_api_key()
        ai_cfg = self.config.get("ai", {})
        api_url = ai_cfg.get("api_url", "https://openrouter.ai/api/v1/chat/completions").strip()
        model = ai_cfg.get("model", "google/gemini-2.0-flash-exp:free").strip()

        if not api_key and "localhost" not in api_url and "127.0.0.1" not in api_url:
            return [
                {
                    "title": "API Key Required for Helper AI",
                    "explanation": "Hawkeye does not ship with a shared key. Open API Setup above and paste your free or paid OpenRouter, Groq, Gemini, OpenAI, or local Ollama endpoint.",
                    "command": "",
                }
            ]

        sys_prompt = (
            "You are Hawkeye Helper, an expert coding, file-editing, and Arch Linux terminal assistant. "
            "Respond ONLY with a valid JSON array of objects: "
            '[{"title": "Short heading", "explanation": "Clear answer or code explanation", "command": "Optional runnable shell command or heredoc file edit, or empty string if conversational"}]. '
            "When asked to write or edit a file, provide a clean shell command (e.g. cat << 'EOF' > file or python -c ...) in 'command' so the user can inject or run it directly in their terminal."
        )
        payload = json.dumps(
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": query},
                ],
                "temperature": 0.3,
            }
        ).encode("utf-8")

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        req = urllib.request.Request(api_url, data=payload, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"].strip()
                content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content)
                parsed = json.loads(content)
                if isinstance(parsed, list) and parsed:
                    return parsed
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                pass
            return [
                {
                    "title": "Helper Request Error",
                    "explanation": f"HTTP {exc.code} from {api_url} (model: {model}). {body}",
                    "command": "",
                }
            ]
        except Exception as exc:
            return [
                {
                    "title": "Helper Request Error",
                    "explanation": f"Could not reach AI provider: {exc}. Verify your API key, endpoint URL, and model name in Edit Key / API Setup.",
                    "command": "",
                }
            ]
        return []

    def _render_cards(self, cards: list[dict]) -> None:
        self._clear_results()
        for item in cards:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            card.add_css_class("panel-card")

            t_lbl = Gtk.Label(label=item.get("title", "Response"))
            t_lbl.add_css_class("hawkeye-brand")
            t_lbl.set_xalign(0.0)
            t_lbl.set_wrap(True)
            card.append(t_lbl)

            explanation = item.get("explanation", "").strip()
            if explanation:
                exp_lbl = Gtk.Label(label=explanation)
                exp_lbl.set_xalign(0.0)
                exp_lbl.set_wrap(True)
                exp_lbl.set_selectable(True)
                card.append(exp_lbl)

            cmd = item.get("command", "").strip()
            if cmd:
                cmd_lbl = Gtk.Label(label=cmd)
                cmd_lbl.add_css_class("cmd-code-box")
                cmd_lbl.set_xalign(0.0)
                cmd_lbl.set_selectable(True)
                cmd_lbl.set_wrap(True)
                card.append(cmd_lbl)

                btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

                inject_btn = Gtk.Button(label="Type in Terminal")
                inject_btn.add_css_class("flat-btn")
                inject_btn.connect(
                    "clicked",
                    lambda *_, c=cmd: self.on_inject_command(c, False),
                )

                run_btn = Gtk.Button(label="Type & Run")
                run_btn.add_css_class("accent-btn")
                run_btn.connect(
                    "clicked",
                    lambda *_, c=cmd: self.on_inject_command(c, True),
                )

                btn_row.append(inject_btn)
                btn_row.append(run_btn)
                card.append(btn_row)

            self.results_box.append(card)
