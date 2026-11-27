import os

SERVICE_NAME = "hawkeye-terminal"
KEY_ACCOUNT = "helper_api_key"


def save_api_key(api_key: str) -> str:
    key = api_key.strip()
    try:
        import keyring
        if key:
            keyring.set_password(SERVICE_NAME, KEY_ACCOUNT, key)
        else:
            try:
                keyring.delete_password(SERVICE_NAME, KEY_ACCOUNT)
            except Exception:
                pass
        return "keyring"
    except Exception:
        # Fallback to restricted user file (chmod 600) if no D-Bus secret service is running
        from pathlib import Path
        secret_file = Path.home() / ".config" / "hawkeye" / ".secret_key"
        secret_file.parent.mkdir(parents=True, exist_ok=True)
        if key:
            secret_file.write_text(key, encoding="utf-8")
            os.chmod(secret_file, 0o600)
        elif secret_file.exists():
            secret_file.unlink()
        return "restricted-file"


def load_api_key() -> str:
    env_key = os.environ.get("HAWKEYE_AI_KEY", "").strip()
    if env_key:
        return env_key
    try:
        import keyring
        stored = keyring.get_password(SERVICE_NAME, KEY_ACCOUNT)
        if stored:
            return stored.strip()
    except Exception:
        pass
    from pathlib import Path
    secret_file = Path.home() / ".config" / "hawkeye" / ".secret_key"
    if secret_file.exists():
        return secret_file.read_text(encoding="utf-8").strip()
    return ""
