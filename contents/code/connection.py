#!/usr/bin/env python3
"""User-initiated local connection actions for the quota widget."""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def respond(message):
    print(json.dumps({"message": message}, ensure_ascii=False))


def status():
    parts = []
    parts.append("Codex CLI hazır" if shutil.which("codex") else "Codex CLI bulunamadı")
    settings = Path.home() / ".claude" / "settings.json"
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
        command = (data.get("statusLine") or {}).get("command", "")
    except (OSError, ValueError, AttributeError):
        command = ""
    parts.append("Claude bağlı" if "claude_capture.py" in command else "Claude bağlantısı kurulmadı")
    default_source = Path.home() / ".config" / "quota-panel" / "antigravity.json"
    agy_settings = Path.home() / ".gemini" / "antigravity-cli" / "settings.json"
    try:
        agy_data = json.loads(agy_settings.read_text(encoding="utf-8"))
        agy_command = (agy_data.get("statusLine") or {}).get("command", "")
    except (OSError, ValueError, AttributeError):
        agy_command = ""
    parts.append("Antigravity verisi var" if default_source.is_file()
                 else ("Antigravity bağlı; CLI oturumu bekleniyor" if "antigravity_capture.py" in agy_command
                       else ("Antigravity CLI hazır" if (shutil.which("agy") or
                             (Path.home() / ".local" / "bin" / "agy").exists())
                             else "Antigravity CLI kurulu değil")))
    respond(" · ".join(parts))


def login_codex():
    binary = shutil.which("codex")
    terminal = shutil.which("konsole")
    if not binary:
        respond("Codex CLI bulunamadı.")
    elif not terminal:
        respond("Konsole bulunamadı. Terminalde 'codex login' çalıştır.")
    else:
        subprocess.Popen([terminal, "-e", binary, "login"],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
        respond("Codex giriş penceresi açıldı.")


def setup_claude():
    if not (shutil.which("claude") or (Path.home() / ".local" / "bin" / "claude").exists()):
        respond("Claude Code CLI bulunamadı.")
        return
    settings = Path.home() / ".claude" / "settings.json"
    try:
        data = json.loads(settings.read_text(encoding="utf-8")) if settings.exists() else {}
        if not isinstance(data, dict):
            raise ValueError("settings.json nesne değil")
        existing = data.get("statusLine") or {}
        if isinstance(existing, dict) and existing.get("command") and "claude_capture.py" not in existing["command"]:
            respond("Claude'da farklı bir durum satırı var; üzerine yazılmadı.")
            return
        capture = Path(__file__).with_name("claude_capture.py")
        new_status_line = {"type": "command", "command": f"python3 {capture}",
                           "refreshInterval": 120}
        if data.get("statusLine") == new_status_line:
            respond("Claude bağlantısı zaten kurulu.")
            return
        data["statusLine"] = new_status_line
        settings.parent.mkdir(parents=True, exist_ok=True)
        if settings.exists():
            backup = settings.with_name(f"settings.quota-panel-backup-{int(time.time())}.json")
            backup.write_bytes(settings.read_bytes())
            os.chmod(backup, 0o600)
        temp = settings.with_suffix(".quota-panel.tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(temp, 0o600)
        temp.replace(settings)
        respond("Claude bağlantısı kuruldu; sonraki Claude Code oturumunda veri gelecek.")
    except (OSError, ValueError, TypeError) as error:
        respond(f"Claude bağlantısı kurulamadı: {error}")


def open_antigravity():
    launcher = shutil.which("gtk-launch")
    desktop = Path.home() / ".local" / "share" / "applications" / "antigravity.desktop"
    if launcher and desktop.exists():
        subprocess.Popen([launcher, "antigravity.desktop"], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        respond("Antigravity açılıyor.")
    else:
        respond("Antigravity başlatıcısı bulunamadı.")


def open_antigravity_cli():
    binary = shutil.which("agy") or str(Path.home() / ".local" / "bin" / "agy")
    terminal = shutil.which("konsole")
    if not Path(binary).exists():
        respond("Antigravity CLI bulunamadı.")
    elif not terminal:
        respond("Konsole bulunamadı. Terminalde 'agy' çalıştır.")
    else:
        subprocess.Popen([terminal, "-e", binary], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        respond("Antigravity CLI açıldı. /usage ile kotayı yenile.")


def setup_antigravity_cli():
    if not (shutil.which("agy") or (Path.home() / ".local" / "bin" / "agy").exists()):
        respond("Antigravity CLI kurulu değil. Resmî kurulumdan sonra tekrar dene.")
        return
    settings = Path.home() / ".gemini" / "antigravity-cli" / "settings.json"
    try:
        data = json.loads(settings.read_text(encoding="utf-8")) if settings.exists() else {}
        if not isinstance(data, dict):
            raise ValueError("settings.json nesne değil")
        existing = data.get("statusLine") or {}
        if isinstance(existing, dict) and existing.get("command") and "antigravity_capture.py" not in existing["command"]:
            respond("Antigravity CLI'da farklı bir durum satırı var; üzerine yazılmadı.")
            return
        capture = Path(__file__).with_name("antigravity_capture.py")
        new_status_line = {"type": "command", "command": f"python3 {capture}",
                           "enabled": True, "stack_with_default": True}
        if data.get("statusLine") == new_status_line:
            respond("Bağlantı kurulu. CLI'yi yeniden aç ve /usage çalıştır.")
            return
        data["statusLine"] = new_status_line
        settings.parent.mkdir(parents=True, exist_ok=True)
        if settings.exists():
            backup = settings.with_name(f"settings.quota-panel-backup-{int(time.time())}.json")
            backup.write_bytes(settings.read_bytes())
            os.chmod(backup, 0o600)
        temp = settings.with_suffix(".quota-panel.tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(temp, 0o600)
        temp.replace(settings)
        respond("Bağlantı kuruldu. CLI'yi aç ve /usage çalıştır.")
    except (OSError, ValueError, TypeError) as error:
        respond(f"Antigravity CLI bağlantısı kurulamadı: {error}")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "status":
        status()
    elif action == "login-codex":
        login_codex()
    elif action == "setup-claude":
        setup_claude()
    elif action == "open-antigravity":
        open_antigravity()
    elif action == "setup-antigravity-cli":
        setup_antigravity_cli()
    elif action == "open-antigravity-cli":
        open_antigravity_cli()
    else:
        respond("Bilinmeyen işlem.")
