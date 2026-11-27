import os
from pathlib import Path
import pwd


def detect_shell(configured_shell: str = "") -> str:
    if configured_shell and os.path.isfile(configured_shell) and os.access(configured_shell, os.X_OK):
        return configured_shell

    env_shell = os.environ.get("SHELL", "")
    if env_shell and os.path.isfile(env_shell) and os.access(env_shell, os.X_OK):
        return env_shell

    try:
        pw_shell = pwd.getpwuid(os.getuid()).pw_shell
        if pw_shell and os.path.isfile(pw_shell) and os.access(pw_shell, os.X_OK):
            return pw_shell
    except KeyError:
        pass

    for candidate in ("/usr/bin/zsh", "/bin/zsh", "/usr/bin/bash", "/bin/bash", "/bin/sh"):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return "/bin/sh"


def get_working_directory(preferred_cwd: str | None = None) -> str:
    if preferred_cwd and os.path.isdir(preferred_cwd):
        return preferred_cwd
    try:
        cwd = os.getcwd()
        if os.path.isdir(cwd):
            return cwd
    except OSError:
        pass
    return str(Path.home())
