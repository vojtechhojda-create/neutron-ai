#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Neutron AI v1.20
================
Terminalovy AI asistent. Umi pracovat s lokalnimi modely (.gguf, slozka /models)
nebo s online API (Anthropic / OpenAI / Gemini) podle settings.json.
Kazdy provider ma 3 sloty na modely, mezi kterymi lze prepinat primo v menu.

Umi na pozadani AI:
  - otevrit / zavrit aplikaci v PC
  - otevrit web / stranku
  - vyhledat na internetu
  - najit a otevrit video (YouTube)
  - napsat / odeslat email (pres vychozi mailovy klient)
  - vytvorit / zapsat / smazat soubor
  - spustit prikaz v shellu
  - zkopirovat text do schranky

Slozka projektu (na Windows):
  C:\\neutron-ai\\neutron-ai.py
  C:\\neutron-ai\\settings.json
  C:\\neutron-ai\\models\\*.gguf
"""

import os
import sys
import json
import re
import glob
import time
import shutil
import difflib
import threading
import subprocess
import urllib.parse
import urllib.request
import urllib.error

VERSION = "1.20"

# ----------------------------------------------------------------------------
# Zakladni cesty
# ----------------------------------------------------------------------------

def _base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = _base_dir()
MODELS_DIR = os.path.join(BASE_DIR, "models")
SETTINGS_PATH = os.path.join(BASE_DIR, "settings.json")

IS_WINDOWS = os.name == "nt"

if IS_WINDOWS:
    try:
        import msvcrt
    except ImportError:
        msvcrt = None
    try:
        import winreg
    except ImportError:
        winreg = None
else:
    msvcrt = None
    winreg = None

# ----------------------------------------------------------------------------
# Barvy (ANSI) - oranzovy theme
# ----------------------------------------------------------------------------

ESC = "\033"
RESET = ESC + "[0m"
BOLD = ESC + "[1m"
DIM = ESC + "[2m"

ORANGE = ESC + "[38;5;208m"
ORANGE_BOLD = ESC + "[1;38;5;208m"
ORANGE_BG = ESC + "[48;5;208m"
BLACK = ESC + "[30m"
WHITE = ESC + "[97m"
GRAY = ESC + "[38;5;245m"
RED = ESC + "[38;5;203m"
GREEN = ESC + "[38;5;113m"

# Odstiny pro gradient hlavicky a pro "dychajici" spinner
ORANGE_SHADES = [208, 209, 215, 214, 208, 202, 208]


def shade(code):
    return ESC + f"[38;5;{code}m"


if IS_WINDOWS:
    try:
        os.system("chcp 65001 >nul")
    except Exception:
        pass
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass
    os.system("")  # zapne ANSI escape sekvence v cmd.exe / PowerShell


def clear():
    os.system("cls" if IS_WINDOWS else "clear")


def term_width(default=78):
    try:
        return shutil.get_terminal_size((default, 24)).columns
    except Exception:
        return default


# ----------------------------------------------------------------------------
# ASCII header "NEUTRON" (gradient)
# ----------------------------------------------------------------------------

NEUTRON_HEADER = r"""
███╗   ██╗███████╗██╗   ██╗████████╗██████╗  ██████╗ ███╗   ██╗
████╗  ██║██╔════╝██║   ██║╚══██╔══╝██╔══██╗██╔═══██╗████╗  ██║
██╔██╗ ██║█████╗  ██║   ██║   ██║   ██████╔╝██║   ██║██╔██╗ ██║
██║╚██╗██║██╔══╝  ██║   ██║   ██║   ██╔══██╗██║   ██║██║╚██╗██║
██║ ╚████║███████╗╚██████╔╝   ██║   ██║  ██║╚██████╔╝██║ ╚████║
╚═╝  ╚═══╝╚══════╝ ╚═════╝    ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
"""


def print_header():
    clear()
    w = term_width()
    lines = NEUTRON_HEADER.strip("\n").split("\n")
    n = len(lines)
    for i, line in enumerate(lines):
        # jemny gradient shora dolu pres paletu oranzovych odstinu
        code = ORANGE_SHADES[i % len(ORANGE_SHADES)]
        print((shade(code) + BOLD + line + RESET).center(w + len(shade(code)) + len(BOLD) + len(RESET)))
    subtitle = f"v{VERSION}"
    print((DIM + subtitle + RESET).center(w + len(DIM) + len(RESET)))
    print()


# ----------------------------------------------------------------------------
# Settings.json
# ----------------------------------------------------------------------------

DEFAULT_MODELS = {
    "anthropic": ["claude-sonnet-5", "claude-opus-4-8", "claude-haiku-4-5-20251001"],
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
    "gemini": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
}

PROVIDER_LABELS = {
    "anthropic": "Claude",
    "openai": "ChatGPT",
    "gemini": "Gemini",
}

DEFAULT_SETTINGS = {
    "version": VERSION,
    "active_provider": "anthropic",
    "active_model_index": 0,
    "providers": {
        "anthropic": {"api_key": "", "models": list(DEFAULT_MODELS["anthropic"])},
        "openai": {"api_key": "", "models": list(DEFAULT_MODELS["openai"])},
        "gemini": {"api_key": "", "models": list(DEFAULT_MODELS["gemini"])},
    },
    "n_ctx": 4096,
    "n_gpu_layers": 0,
}


def _normalize_provider_block(name, block):
    """Zajisti, ze provider blok ma api_key + presne 3 modely (doplni z default)."""
    if not isinstance(block, dict):
        block = {}
    api_key = block.get("api_key", "")
    models = block.get("models")
    defaults = DEFAULT_MODELS.get(name, ["", "", ""])
    if not isinstance(models, list):
        models = []
    models = list(models)[:3]
    while len(models) < 3:
        models.append(defaults[len(models)] if len(models) < len(defaults) else "")
    return {"api_key": api_key, "models": models}


def _migrate_legacy(data):
    """Podpora starych plochych klicu (anthropic_api_key apod.) z drivejsich verzi."""
    if "providers" in data:
        return data
    migrated = {
        "version": VERSION,
        "active_provider": "anthropic",
        "active_model_index": 0,
        "providers": {
            "anthropic": {
                "api_key": data.get("anthropic_api_key", ""),
                "models": [data.get("anthropic_model", DEFAULT_MODELS["anthropic"][0]), "", ""],
            },
            "openai": {
                "api_key": data.get("openai_api_key", ""),
                "models": [data.get("openai_model", DEFAULT_MODELS["openai"][0]), "", ""],
            },
            "gemini": {
                "api_key": data.get("gemini_api_key", ""),
                "models": [data.get("gemini_model", DEFAULT_MODELS["gemini"][0]), "", ""],
            },
        },
        "n_ctx": data.get("n_ctx", 4096),
        "n_gpu_layers": data.get("n_gpu_layers", 0),
    }
    return migrated


def load_settings():
    if not os.path.exists(SETTINGS_PATH):
        save_settings(DEFAULT_SETTINGS)
        return json.loads(json.dumps(DEFAULT_SETTINGS))

    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(RED + f"Chyba při čtení settings.json: {e}" + RESET)
        return json.loads(json.dumps(DEFAULT_SETTINGS))

    data = _migrate_legacy(data)

    merged = json.loads(json.dumps(DEFAULT_SETTINGS))
    merged["version"] = VERSION
    merged["active_provider"] = data.get("active_provider", merged["active_provider"])
    merged["active_model_index"] = data.get("active_model_index", 0)
    merged["n_ctx"] = data.get("n_ctx", merged["n_ctx"])
    merged["n_gpu_layers"] = data.get("n_gpu_layers", merged["n_gpu_layers"])

    providers = data.get("providers", {})
    for name in ("anthropic", "openai", "gemini"):
        merged["providers"][name] = _normalize_provider_block(name, providers.get(name, {}))

    # kompatibilita se starsim tvarem "active_model" (jmeno modelu, ne index)
    legacy_active_model = data.get("active_model")
    if legacy_active_model and merged["active_provider"] in merged["providers"]:
        models = merged["providers"][merged["active_provider"]]["models"]
        if legacy_active_model in models:
            merged["active_model_index"] = models.index(legacy_active_model)

    save_settings(merged)
    return merged


def save_settings(data):
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(RED + f"Nelze uložit settings.json: {e}" + RESET)


def get_api_key(settings, provider):
    return settings["providers"].get(provider, {}).get("api_key", "")


# ----------------------------------------------------------------------------
# Vyber polozky sipkami (Up/Down + Enter)
# ----------------------------------------------------------------------------

def get_key():
    """Vrati 'UP', 'DOWN', 'ENTER', 'ESC' nebo None."""
    if IS_WINDOWS and msvcrt:
        ch = msvcrt.getch()
        if ch in (b"\xe0", b"\x00"):
            ch2 = msvcrt.getch()
            return {b"H": "UP", b"P": "DOWN"}.get(ch2)
        if ch in (b"\r", b"\n"):
            return "ENTER"
        if ch == b"\x1b":
            return "ESC"
        if ch == b"\x03":
            raise KeyboardInterrupt
        return None
    else:
        # fallback pro Linux/Mac terminal (bez msvcrt) - cte raw escape sekvence
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                ch2 = sys.stdin.read(2)
                if ch2 == "[A":
                    return "UP"
                if ch2 == "[B":
                    return "DOWN"
                return "ESC"
            if ch in ("\r", "\n"):
                return "ENTER"
            if ch == "\x03":
                raise KeyboardInterrupt
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def read_line_hidden(prompt):
    """Skryty vstup pro API klice (getpass), s fallbackem."""
    try:
        import getpass
        return getpass.getpass(prompt)
    except Exception:
        return input(prompt)


def select_menu(title, items, hint="↑ ↓ výběr   Enter potvrdit   Esc zpět"):
    """items: list of (label, value). Vrátí vybranou 'value' nebo None při ESC."""
    if not items:
        return None
    idx = 0
    w = term_width()
    while True:
        print_header()
        print((ORANGE + title + RESET).center(w + len(ORANGE) + len(RESET)))
        print()
        for i, (label, _val) in enumerate(items):
            if i == idx:
                line = f"{ORANGE_BG}{BLACK}{BOLD} > {label} {RESET}"
                print(line.center(w + len(ORANGE_BG) + len(BLACK) + len(BOLD) + len(RESET)))
            else:
                print((GRAY + f"   {label}" + RESET).center(w + len(GRAY) + len(RESET)))
        print()
        print((DIM + hint + RESET).center(w + len(DIM) + len(RESET)))

        key = get_key()
        if key == "UP":
            idx = (idx - 1) % len(items)
        elif key == "DOWN":
            idx = (idx + 1) % len(items)
        elif key == "ENTER":
            return items[idx][1]
        elif key == "ESC":
            return None


# ----------------------------------------------------------------------------
# Vyhledani modelu (lokalni .gguf + online providery x 3 sloty)
# ----------------------------------------------------------------------------

class ModelChoice:
    def __init__(self, kind, name, path=None, provider=None, model=None):
        self.kind = kind        # "local" nebo "online"
        self.name = name
        self.path = path
        self.provider = provider  # "anthropic" / "openai" / "gemini"
        self.model = model        # konkretni nazev modelu (pro online)


def discover_models(settings):
    choices = []

    os.makedirs(MODELS_DIR, exist_ok=True)
    for path in sorted(glob.glob(os.path.join(MODELS_DIR, "*.gguf"))):
        name = os.path.splitext(os.path.basename(path))[0]
        choices.append(ModelChoice("local", name, path=path))

    for provider in ("anthropic", "openai", "gemini"):
        block = settings["providers"].get(provider, {})
        api_key = block.get("api_key", "")
        if not api_key:
            continue
        label = PROVIDER_LABELS[provider]
        for slot_i, model_name in enumerate(block.get("models", [])):
            if not model_name:
                continue
            display = f"{label} - {model_name}"
            choices.append(ModelChoice("online", display, provider=provider, model=model_name))

    return choices


# ----------------------------------------------------------------------------
# Akce - vyhledavani/otevirani aplikaci, webu, emailu, videa + automatizace
# ----------------------------------------------------------------------------

def _windows_search_dirs():
    dirs = []
    appdata = os.environ.get("APPDATA")
    programdata = os.environ.get("PROGRAMDATA")
    if appdata:
        dirs.append(os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs"))
    if programdata:
        dirs.append(os.path.join(programdata, r"Microsoft\Windows\Start Menu\Programs"))
    return [d for d in dirs if os.path.isdir(d)]


def _list_shortcuts():
    """Vrati dict {nazev_bez_diakritiky_lower: cesta_k_lnk}."""
    result = {}
    for base in _windows_search_dirs():
        for root, _dirs, files in os.walk(base):
            for fn in files:
                if fn.lower().endswith((".lnk", ".exe")):
                    name = os.path.splitext(fn)[0]
                    result[name.lower()] = os.path.join(root, fn)
    return result


def _registry_installed_apps():
    """Vrati dict {nazev_lower: install_path_or_displayicon} z registru (Windows)."""
    apps = {}
    if not winreg:
        return apps
    roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for hive, path in roots:
        try:
            key = winreg.OpenKey(hive, path)
        except OSError:
            continue
        for i in range(winreg.QueryInfoKey(key)[0]):
            try:
                sub_name = winreg.EnumKey(key, i)
                sub = winreg.OpenKey(key, sub_name)
                try:
                    display_name = winreg.QueryValueEx(sub, "DisplayName")[0]
                except OSError:
                    continue
                icon = None
                for val in ("DisplayIcon", "InstallLocation"):
                    try:
                        icon = winreg.QueryValueEx(sub, val)[0]
                        if icon:
                            break
                    except OSError:
                        pass
                apps[display_name.lower()] = icon
            except OSError:
                continue
    return apps


def find_app_path(query):
    """Najde nejlepsi shodu pro nazev aplikace. Vrati cestu nebo None."""
    query_l = query.strip().lower()

    if IS_WINDOWS:
        shortcuts = _list_shortcuts()
        if query_l in shortcuts:
            return shortcuts[query_l]
        match = difflib.get_close_matches(query_l, shortcuts.keys(), n=1, cutoff=0.5)
        if match:
            return shortcuts[match[0]]

        apps = _registry_installed_apps()
        if query_l in apps and apps[query_l]:
            return apps[query_l].split(",")[0].strip('"')
        match = difflib.get_close_matches(query_l, apps.keys(), n=1, cutoff=0.5)
        if match and apps[match[0]]:
            return apps[match[0]].split(",")[0].strip('"')

    return None


def action_open_app(name):
    path = find_app_path(name)
    try:
        if path and os.path.exists(path):
            if IS_WINDOWS:
                os.startfile(path)
            else:
                subprocess.Popen([path])
            return f"Otevírám aplikaci: {os.path.basename(path)}"
        else:
            if IS_WINDOWS:
                subprocess.Popen(f'start "" "{name}"', shell=True)
            else:
                subprocess.Popen([name])
            return f"Zkouším spustit: {name}"
    except Exception as e:
        return f"Nepodařilo se otevřít '{name}': {e}"


def action_close_app(name):
    """Zavre/ukonci beziici aplikaci podle nazvu procesu (napr. 'chrome' -> chrome.exe)."""
    proc_name = name.strip()
    if not proc_name.lower().endswith(".exe") and IS_WINDOWS:
        proc_name_full = proc_name + ".exe"
    else:
        proc_name_full = proc_name
    try:
        if IS_WINDOWS:
            result = subprocess.run(
                ["taskkill", "/IM", proc_name_full, "/F"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return f"Zavřeno: {proc_name_full}"
            return f"Nepodařilo se zavřít '{proc_name_full}': {result.stderr.strip() or 'proces nenalezen'}"
        else:
            result = subprocess.run(["pkill", "-f", proc_name], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return f"Zavřeno: {proc_name}"
            return f"Proces '{proc_name}' nebyl nalezen nebo se nepodařilo ukončit."
    except Exception as e:
        return f"Chyba při zavírání '{proc_name}': {e}"


def action_open_web(url):
    import webbrowser
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    webbrowser.open(url)
    return f"Otevírám web: {url}"


def action_search(query):
    import webbrowser
    url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
    webbrowser.open(url)
    return f"Hledám na internetu: {query}"


def action_video(query):
    import webbrowser
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
    webbrowser.open(url)
    return f"Hledám video: {query}"


def action_email(to, subject, body):
    import webbrowser
    params = urllib.parse.urlencode({"subject": subject, "body": body})
    url = f"mailto:{to}?{params}"
    webbrowser.open(url)
    return f"Připravuji email pro: {to}"


def _resolve_user_path(path):
    """Relativni cesty resi vuci slozce, odkud program bezi (BASE_DIR)."""
    if os.path.isabs(path):
        return path
    return os.path.join(BASE_DIR, path)


def action_create_file(path, content=""):
    if not path:
        return "Chybí cesta k souboru."
    full_path = _resolve_user_path(path)
    try:
        os.makedirs(os.path.dirname(full_path) or ".", exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content.replace("\\n", "\n"))
        return f"Vytvořen soubor: {full_path}"
    except Exception as e:
        return f"Nepodařilo se vytvořit soubor '{full_path}': {e}"


def action_append_file(path, content=""):
    if not path:
        return "Chybí cesta k souboru."
    full_path = _resolve_user_path(path)
    try:
        os.makedirs(os.path.dirname(full_path) or ".", exist_ok=True)
        with open(full_path, "a", encoding="utf-8") as f:
            f.write(content.replace("\\n", "\n"))
        return f"Připsáno do souboru: {full_path}"
    except Exception as e:
        return f"Nepodařilo se zapsat do souboru '{full_path}': {e}"


def action_delete_file(path):
    if not path:
        return "Chybí cesta k souboru."
    full_path = _resolve_user_path(path)
    try:
        if os.path.isfile(full_path):
            os.remove(full_path)
            return f"Smazán soubor: {full_path}"
        return f"Soubor neexistuje: {full_path}"
    except Exception as e:
        return f"Nepodařilo se smazat soubor '{full_path}': {e}"


def action_run_command(command):
    if not command:
        return "Chybí příkaz ke spuštění."
    try:
        if IS_WINDOWS:
            # podrizeny cmd.exe bezi ve vlastnim kodovani (OEM codepage),
            # bez tohoto prepnuti by se cestina a oddelovace cisel rozbily
            full_command = f"chcp 65001>nul & {command}"
        else:
            full_command = command

        result = subprocess.run(
            full_command, shell=True, capture_output=True, timeout=60, cwd=BASE_DIR
        )
        output = (result.stdout or b"").decode("utf-8", errors="replace").strip()
        error = (result.stderr or b"").decode("utf-8", errors="replace").strip()
        summary = output[-800:] if output else ""
        if result.returncode != 0:
            return f"Příkaz doběhl s chybou (kód {result.returncode}): {error[-400:] or 'bez výstupu'}"
        return f"Příkaz spuštěn.{(' Výstup: ' + summary) if summary else ''}"
    except subprocess.TimeoutExpired:
        return "Příkaz překročil časový limit (60 s)."
    except Exception as e:
        return f"Chyba při spouštění příkazu: {e}"


def action_clipboard(text):
    try:
        if IS_WINDOWS:
            p = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
            p.communicate(input=text.encode("utf-16le"))
        elif sys.platform == "darwin":
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(input=text.encode("utf-8"))
        else:
            p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
            p.communicate(input=text.encode("utf-8"))
        return "Text zkopírován do schránky."
    except Exception as e:
        return f"Nepodařilo se zkopírovat do schránky: {e}"


ACTION_HANDLERS = {
    "open_app": lambda p: action_open_app(p.get("name", "")),
    "close_app": lambda p: action_close_app(p.get("name", "")),
    "open_web": lambda p: action_open_web(p.get("url", "")),
    "search": lambda p: action_search(p.get("query", "")),
    "video": lambda p: action_video(p.get("query", "")),
    "email": lambda p: action_email(p.get("to", ""), p.get("subject", ""), p.get("body", "")),
    "create_file": lambda p: action_create_file(p.get("path", ""), p.get("content", "")),
    "append_file": lambda p: action_append_file(p.get("path", ""), p.get("content", "")),
    "delete_file": lambda p: action_delete_file(p.get("path", "")),
    "run_command": lambda p: action_run_command(p.get("command", "")),
    "clipboard": lambda p: action_clipboard(p.get("text", "")),
}

ACTION_DESCRIPTIONS = {
    "open_app": lambda p: f'Otevřít aplikaci „{p.get("name", "")}“',
    "close_app": lambda p: f'Zavřít aplikaci „{p.get("name", "")}“',
    "open_web": lambda p: f'Otevřít web: {p.get("url", "")}',
    "search": lambda p: f'Vyhledat na internetu: {p.get("query", "")}',
    "video": lambda p: f'Najít video: {p.get("query", "")}',
    "email": lambda p: f'Napsat email pro {p.get("to", "")} (předmět: {p.get("subject", "")})',
    "create_file": lambda p: f'Vytvořit soubor: {p.get("path", "")}',
    "append_file": lambda p: f'Připsat text do souboru: {p.get("path", "")}',
    "delete_file": lambda p: f'Smazat soubor: {p.get("path", "")}',
    "run_command": lambda p: f'Spustit příkaz: {p.get("command", "")}',
    "clipboard": lambda p: 'Zkopírovat text do schránky',
}


def describe_action(action_type, params):
    fn = ACTION_DESCRIPTIONS.get(action_type)
    if fn:
        try:
            return fn(params)
        except Exception:
            pass
    return f"Akce: {action_type} ({params})"


# Format akce v odpovedi modelu: [ACTION:type|key=value|key=value]
ACTION_PATTERN = re.compile(r"\[ACTION:([a-z_]+)((?:\|[a-zA-Z_]+=[^\]\|]*)*)\]", re.I)


def extract_actions(text):
    """Najde ACTION tagy v textu, NEPROVÁDÍ je. Vrátí (čistý_text, [(typ, params), ...])."""
    actions = []

    def repl(m):
        action_type = m.group(1).lower()
        raw_params = m.group(2)
        params = {}
        for part in raw_params.split("|"):
            if not part:
                continue
            if "=" in part:
                k, v = part.split("=", 1)
                params[k.strip()] = v.strip()
        actions.append((action_type, params))
        return ""

    clean = ACTION_PATTERN.sub(repl, text).strip()
    return clean, actions


def run_single_action(action_type, params):
    handler = ACTION_HANDLERS.get(action_type)
    if not handler:
        return f"Neznámá akce: {action_type}"
    try:
        return handler(params)
    except Exception as e:
        return f"Chyba při akci {action_type}: {e}"


def confirm_action(description):
    """Zobrazí akci a nechá uživatele potvrdit šipkami (Ano / Ne) + Enter."""
    options = ["Ano", "Ne"]
    idx = 0
    rendered_lines = 0

    while True:
        lines = []
        lines.append(ORANGE_BOLD + "⚙ AI chce provést akci:" + RESET)
        lines.append("  " + description)
        for i, label in enumerate(options):
            if i == idx:
                color = GREEN if label == "Ano" else RED
                lines.append(f"  {color}{BOLD}> {label}{RESET}")
            else:
                lines.append(f"    {GRAY}{label}{RESET}")
        lines.append(DIM + "↑ ↓ výběr   Enter potvrdit" + RESET)

        if rendered_lines:
            sys.stdout.write(f"{ESC}[{rendered_lines}A")
            for _ in range(rendered_lines):
                sys.stdout.write(f"{ESC}[2K\n")
            sys.stdout.write(f"{ESC}[{rendered_lines}A")

        for line in lines:
            print(line)
        rendered_lines = len(lines)
        sys.stdout.flush()

        key = get_key()
        if key == "UP":
            idx = (idx - 1) % len(options)
        elif key == "DOWN":
            idx = (idx + 1) % len(options)
        elif key == "ENTER":
            return options[idx] == "Ano"
        elif key == "ESC":
            return False


SYSTEM_PROMPT = """Jsi Neutron AI, český terminálový asistent na Windows.

Vždy odpovídej výhradně spisovnou češtinou, gramaticky správně a VŽDY s plnou
diakritikou (háčky a čárky). Nikdy nepiš bez diakritiky a nepoužívej hovorové
zkomoleniny ani slang. Piš stručně, věcně a slušně.

Kdyz uzivatel chce neco udelat na pocitaci nebo na internetu, MUSIS do odpovedi
vlozit prislusny ACTION tag presne v tomto formatu (muzes jich pouzit i vic
za sebou, provedou se v poradi, v jakem je napises):

[ACTION:open_app|name=NAZEV_APLIKACE]
[ACTION:close_app|name=NAZEV_APLIKACE]
[ACTION:open_web|url=ADRESA]
[ACTION:search|query=DOTAZ]
[ACTION:video|query=DOTAZ]
[ACTION:email|to=EMAIL|subject=PREDMET|body=TEXT]
[ACTION:create_file|path=CESTA|content=OBSAH]
[ACTION:append_file|path=CESTA|content=OBSAH]
[ACTION:delete_file|path=CESTA]
[ACTION:run_command|command=PRIKAZ]
[ACTION:clipboard|text=TEXT]

Příklady:
- "otevři chrome" -> [ACTION:open_app|name=chrome]
- "zavři chrome" -> [ACTION:close_app|name=chrome]
- "otevři seznam.cz" -> [ACTION:open_web|url=seznam.cz]
- "najdi mi recept na guláš" -> [ACTION:search|query=recept na guláš]
- "najdi video o vesmíru" -> [ACTION:video|query=vesmír]
- "napiš email Petrovi na petr@email.cz, že přijdu později" ->
  [ACTION:email|to=petr@email.cz|subject=Zpráva|body=Ahoj, přijdu později.]
- "vytvoř soubor poznamky.txt s textem ahoj" ->
  [ACTION:create_file|path=poznamky.txt|content=ahoj]
- "spusť příkaz dir" -> [ACTION:run_command|command=dir]

Tag piš VŽDY, když má dojít k akci. Text kolem tagu piš spisovnou češtinou
s diakritikou. Hodnoty uvnitř tagu (name=, url=, query=, path=, command=...)
piš bez diakritiky, aby se nerozbil formát tagu. V hodnote content= muzes
pouzit \\n pro novy radek. U run_command bud opatrny a navrhuj jen bezpecne,
zamyslene prikazy - uzivatel kazdou akci jeste potvrzuje sam.
Pokud akce není potřeba, odpověz jen normálním textem bez tagu.
"""


# ----------------------------------------------------------------------------
# Online provider - volani API
# ----------------------------------------------------------------------------

def call_anthropic(api_key, model, history, user_msg):
    url = "https://api.anthropic.com/v1/messages"
    messages = history + [{"role": "user", "content": user_msg}]
    payload = {
        "model": model,
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": messages,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    return text


def call_openai(api_key, model, history, user_msg):
    url = "https://api.openai.com/v1/chat/completions"
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [
        {"role": "user", "content": user_msg}
    ]
    payload = {"model": model, "messages": messages, "max_tokens": 1024}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def call_gemini(api_key, model, history, user_msg):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    contents = []
    for h in history:
        role = "user" if h["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": h["content"]}]})
    contents.append({"role": "user", "parts": [{"text": user_msg}]})
    payload = {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["candidates"][0]["content"]["parts"][0]["text"]


CALL_FUNCTIONS = {
    "anthropic": call_anthropic,
    "openai": call_openai,
    "gemini": call_gemini,
}


# ----------------------------------------------------------------------------
# Lokalni model (llama-cpp-python)
# ----------------------------------------------------------------------------

class LocalModel:
    def __init__(self, path, settings):
        try:
            from llama_cpp import Llama
        except ImportError:
            print(RED + "Knihovna 'llama-cpp-python' neni nainstalovana." + RESET)
            print(DIM + "Nainstaluj pomoci: pip install llama-cpp-python" + RESET)
            sys.exit(1)
        print(ORANGE + f"Načítám model: {os.path.basename(path)} ..." + RESET)
        self.llm = Llama(
            model_path=path,
            n_ctx=settings.get("n_ctx", 4096),
            n_gpu_layers=settings.get("n_gpu_layers", 0),
            verbose=False,
        )

    def reply(self, history, user_msg):
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [
            {"role": "user", "content": user_msg}
        ]
        out = self.llm.create_chat_completion(messages=messages, max_tokens=1024)
        return out["choices"][0]["message"]["content"]


# ----------------------------------------------------------------------------
# Animace - spinner behem cekani na odpoved + typing efekt
# ----------------------------------------------------------------------------

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class Spinner:
    """Animovany 'premyslejici' spinner s dychajicimi oranzovymi odstiny."""

    def __init__(self, label="Neutron přemýšlí"):
        self.label = label
        self._stop = threading.Event()
        self._thread = None

    def _run(self):
        i = 0
        while not self._stop.is_set():
            frame = SPINNER_FRAMES[i % len(SPINNER_FRAMES)]
            code = ORANGE_SHADES[i % len(ORANGE_SHADES)]
            line = f"\r{shade(code)}{frame} {self.label}...{RESET}   "
            sys.stdout.write(line)
            sys.stdout.flush()
            time.sleep(0.08)
            i += 1

    def __enter__(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
        # smaz radek spinneru
        sys.stdout.write("\r" + " " * 60 + "\r")
        sys.stdout.flush()


def type_out(text, base_delay=0.012):
    """Vypise text postupne (typing efekt), s pauzou navic po interpunkci."""
    if not text:
        return
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        if ch in ".!?":
            time.sleep(base_delay * 14)
        elif ch in ",;:":
            time.sleep(base_delay * 7)
        elif ch == "\n":
            time.sleep(base_delay * 4)
        else:
            time.sleep(base_delay)
    print()


# ----------------------------------------------------------------------------
# Nastaveni - API klice a modelove sloty
# ----------------------------------------------------------------------------

def mask_key(key):
    if not key:
        return DIM + "(prázdné)" + RESET
    if len(key) <= 8:
        return GRAY + "•" * len(key) + RESET
    return GRAY + key[:4] + "•" * (len(key) - 8) + key[-4:] + RESET


def edit_api_keys(settings):
    while True:
        items = []
        for name in ("anthropic", "openai", "gemini"):
            key = get_api_key(settings, name)
            status = "nastaven" if key else "prázdný"
            items.append((f"{PROVIDER_LABELS[name]} – klíč {status}", name))
        items.append(("⬅ Zpět", "back"))

        choice = select_menu("API KLÍČE", items)
        if choice in (None, "back"):
            return

        clear()
        print(ORANGE_BOLD + f"{PROVIDER_LABELS[choice]} - API klíč" + RESET)
        current = get_api_key(settings, choice)
        print(DIM + f"Aktuální: {mask_key(current)}" + RESET)
        print(DIM + "Zadej nový klíč (Enter ponechá beze změny):" + RESET)
        new_key = read_line_hidden("> ").strip()
        if new_key:
            settings["providers"][choice]["api_key"] = new_key
            save_settings(settings)
            print(GREEN + "Uloženo." + RESET)
        time.sleep(0.8)


def edit_models(settings):
    while True:
        items = [(f"{PROVIDER_LABELS[name]}", name) for name in ("anthropic", "openai", "gemini")]
        items.append(("⬅ Zpět", "back"))
        provider = select_menu("MODELY - VYBER PROVIDERA", items)
        if provider in (None, "back"):
            return

        while True:
            models = settings["providers"][provider]["models"]
            items = [(f"Slot {i + 1}: {m or '(prázdný)'}", i) for i, m in enumerate(models)]
            items.append(("⬅ Zpět", "back"))
            slot = select_menu(f"{PROVIDER_LABELS[provider].upper()} - 3 SLOTY MODELŮ", items)
            if slot in (None, "back"):
                break

            clear()
            print(ORANGE_BOLD + f"{PROVIDER_LABELS[provider]} - slot {slot + 1}" + RESET)
            print(DIM + f"Aktuální: {models[slot] or '(prázdný)'}" + RESET)
            print(DIM + "Zadej název modelu (Enter ponechá beze změny):" + RESET)
            new_name = input("> ").strip()
            if new_name:
                settings["providers"][provider]["models"][slot] = new_name
                save_settings(settings)
                print(GREEN + "Uloženo." + RESET)
            time.sleep(0.8)


def settings_menu(settings):
    while True:
        items = [
            ("🔑 API klíče", "keys"),
            ("🧠 Modelové sloty (3 na providera)", "models"),
            ("⬅ Zpět do hlavního menu", "back"),
        ]
        choice = select_menu("NASTAVENÍ", items)
        if choice in (None, "back"):
            return
        elif choice == "keys":
            edit_api_keys(settings)
        elif choice == "models":
            edit_models(settings)


# ----------------------------------------------------------------------------
# Hlavni chat smycka
# ----------------------------------------------------------------------------

def run_chat(choice, settings):
    history = []
    local = None
    if choice.kind == "local":
        local = LocalModel(choice.path, settings)

    print_header()
    print((ORANGE + f"Model: {choice.name}" + RESET))
    print(DIM + "Napiš zprávu. Příkaz 'konec' ukončí program." + RESET)
    print()

    while True:
        try:
            user_msg = input(ORANGE_BOLD + "Ty> " + RESET).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_msg:
            continue
        if user_msg.lower() in ("konec", "exit", "quit"):
            break

        try:
            with Spinner("Neutron přemýšlí"):
                if choice.kind == "local":
                    raw = local.reply(history, user_msg)
                else:
                    fn = CALL_FUNCTIONS[choice.provider]
                    api_key = get_api_key(settings, choice.provider)
                    raw = fn(api_key, choice.model, history, user_msg)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(RED + "Limit požadavků na API byl vyčerpán (429). Zkus to za chvíli, nebo zkontroluj billing/free tier u daného API." + RESET)
            elif e.code in (401, 403):
                print(RED + f"API klíč není platný nebo nemá oprávnění ({e.code}). Zkontroluj settings.json / Nastavení." + RESET)
            else:
                print(RED + f"Chyba při komunikaci s modelem (HTTP {e.code})." + RESET)
            continue
        except Exception as e:
            print(RED + f"Chyba při komunikaci s modelem: {e}" + RESET)
            continue

        clean_text, actions = extract_actions(raw)

        sys.stdout.write(ORANGE_BOLD + "Neutron> " + RESET)
        sys.stdout.flush()
        type_out(clean_text if clean_text else "")
        print()

        for action_type, params in actions:
            desc = describe_action(action_type, params)
            confirmed = confirm_action(desc)
            if confirmed:
                result = run_single_action(action_type, params)
                print(GREEN + "  ✓ " + result + RESET)
            else:
                print(RED + "  ✗ Akce zrušena." + RESET)
            print()

        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": raw})


# ----------------------------------------------------------------------------
# Vstupni bod
# ----------------------------------------------------------------------------

def main():
    settings = load_settings()
    os.makedirs(MODELS_DIR, exist_ok=True)

    while True:
        choices = discover_models(settings)

        menu_items = []
        for c in choices:
            prefix = "💻 " if c.kind == "local" else "🌐 "
            menu_items.append((prefix + c.name, c))
        menu_items.append(("⚙ Nastavení (API klíče, modely)", "settings"))

        if not choices:
            print_header()
            print(RED + "Nebyl nalezen žádný model." + RESET)
            print(DIM + f"Vlož .gguf soubory do: {MODELS_DIR}" + RESET)
            print(DIM + "Nebo doplň API klíč v Nastavení." + RESET)
            print()

        selected = select_menu("VYBER MODEL", menu_items)
        if selected is None:
            return
        if selected == "settings":
            settings_menu(settings)
            continue

        run_chat(selected, settings)
        # po ukonceni chatu (prikaz "konec") se vratime do hlavniho menu
        settings = load_settings()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        sys.exit(0)