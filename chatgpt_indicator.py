#!/usr/bin/env python3
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")

from gi.repository import AppIndicator3, GLib, Gtk  # noqa: E402


APP_ID = "gptokens-indicator"
APP_TITLE = "GPTokens"
CONFIG_DIR = Path(
    os.environ.get("GPTOKENS_CONFIG_DIR", str(Path.home() / ".config" / "gptokens"))
)
STATE_FILE = CONFIG_DIR / "usage_state.json"
REFRESH_INTERVAL_SECONDS = int(os.environ.get("GPTOKENS_REFRESH_SECONDS", "30"))
WARNING_THRESHOLD = int(os.environ.get("GPTOKENS_WARNING_THRESHOLD", "40"))
CRITICAL_THRESHOLD = int(os.environ.get("GPTOKENS_CRITICAL_THRESHOLD", "20"))


@dataclass
class WindowSummary:
    label: str
    remaining_percent: int
    remaining_count: int
    quota: int
    used: int
    hours: int
    reset_at: str


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def now_hhmm() -> str:
    return datetime.now().strftime("%H:%M")


def format_hhmm_from_iso(iso_value: str | None) -> str:
    if not iso_value:
        return "inconnu"
    try:
        return datetime.fromisoformat(iso_value).strftime("%H:%M")
    except ValueError:
        return "inconnu"


def format_reset_at(iso_value: str | None) -> str:
    return format_hhmm_from_iso(iso_value)


def compute_window_summary(model: dict) -> WindowSummary:
    quota = int(model.get("quota", 0))
    used = int(model.get("used", 0))
    remaining_count = max(0, quota - used) if quota > 0 else max(0, int(model.get("max", 0)) - used)
    denom = quota if quota > 0 else int(model.get("max", 0) or 1)
    remaining_percent = max(0, min(100, int(round((remaining_count / max(1, denom)) * 100))))
    return WindowSummary(
        label=model.get("id", "modele"),
        remaining_percent=remaining_percent,
        remaining_count=remaining_count,
        quota=quota,
        used=used,
        hours=int(model.get("hours", 0)),
        reset_at=format_reset_at(model.get("reset_at")),
    )


def format_window_line(prefix: str, summary: WindowSummary) -> str:
    quota_text = summary.quota if summary.quota > 0 else "?"
    return (
        f"{prefix}: {summary.remaining_percent}% ({summary.remaining_count}/{quota_text})"
        f" | reset {summary.reset_at}"
    )


def choose_windows(models: list[dict]) -> tuple[WindowSummary | None, WindowSummary | None]:
    if not models:
        return None, None

    sorted_models = sorted(models, key=lambda item: int(item.get("hours", 0) or 0))
    primary = compute_window_summary(sorted_models[0])
    secondary = compute_window_summary(sorted_models[-1])
    return primary, secondary


def load_state() -> dict | None:
    try:
        if not STATE_FILE.exists():
            return None
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


class GPTokensIndicator:
    def __init__(self) -> None:
        ensure_config_dir()

        self.indicator = AppIndicator3.Indicator.new(
            APP_ID,
            "network-workgroup",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        self.menu = Gtk.Menu()

        self.title_item = Gtk.MenuItem(label=APP_TITLE)
        self.title_item.set_sensitive(False)
        self.menu.append(self.title_item)

        self.summary_item = Gtk.MenuItem(label="En attente de donnees...")
        self.summary_item.set_sensitive(False)
        self.menu.append(self.summary_item)

        self.primary_item = Gtk.MenuItem(label="")
        self.primary_item.set_sensitive(False)
        self.menu.append(self.primary_item)

        self.secondary_item = Gtk.MenuItem(label="")
        self.secondary_item.set_sensitive(False)
        self.menu.append(self.secondary_item)

        self.plan_item = Gtk.MenuItem(label="")
        self.plan_item.set_sensitive(False)
        self.menu.append(self.plan_item)

        self.last_check_item = Gtk.MenuItem(label="")
        self.last_check_item.set_sensitive(False)
        self.menu.append(self.last_check_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        refresh_item = Gtk.MenuItem(label="Rafraichir")
        refresh_item.connect("activate", self.manual_refresh)
        self.menu.append(refresh_item)

        quit_item = Gtk.MenuItem(label="Quitter")
        quit_item.connect("activate", self.quit)
        self.menu.append(quit_item)

        self.menu.show_all()
        self.indicator.set_menu(self.menu)

        self.refresh()
        GLib.timeout_add_seconds(REFRESH_INTERVAL_SECONDS, self.refresh)

    def manual_refresh(self, _widget) -> None:
        self.refresh()

    def set_visual_state(self, remaining_percent: int | None) -> None:
        if remaining_percent is None:
            level = "error"
        elif remaining_percent <= CRITICAL_THRESHOLD:
            level = "critical"
        elif remaining_percent <= WARNING_THRESHOLD:
            level = "warning"
        else:
            level = "ok"

        icon_map = {
            "ok": "emblem-default",
            "warning": "dialog-warning",
            "critical": "dialog-error",
            "error": "network-error",
        }
        icon_name = icon_map[level]
        self.indicator.set_icon_full(icon_name, level)
        self.indicator.set_attention_icon_full(icon_name, level)

    def set_indicator_text(self, remaining_percent: int | None) -> None:
        if remaining_percent is None:
            text = "--%"
        elif remaining_percent <= CRITICAL_THRESHOLD:
            text = f"!{remaining_percent}%"
        elif remaining_percent <= WARNING_THRESHOLD:
            text = f"{remaining_percent}%"
        else:
            text = f"{remaining_percent}%"
        self.indicator.set_label(text, APP_ID)

    def refresh(self) -> bool:
        state = load_state()
        if not state:
            self.set_visual_state(None)
            self.set_indicator_text(None)
            self.summary_item.set_label("Aucune donnee recue")
            self.primary_item.set_label("1ere etape: envoyer un message depuis ChatGPT dans Brave")
            self.secondary_item.set_label("2e etape: cliquer sur Sync Linux Indicator")
            self.plan_item.set_label(f"Fichier attendu: {STATE_FILE}")
            self.last_check_item.set_label(f"Dernier check: {now_hhmm()}")
            return True

        models = state.get("models", [])
        primary, secondary = choose_windows(models)
        if primary is None:
            self.set_visual_state(None)
            self.set_indicator_text(None)
            self.summary_item.set_label("Etat present, mais sans modele suivi")
            self.primary_item.set_label(f"Source: {state.get('source', 'inconnue')}")
            self.secondary_item.set_label("")
            self.plan_item.set_label("")
            self.last_check_item.set_label(
                f"Dernier check: {format_hhmm_from_iso(state.get('updated_at'))}"
            )
            return True

        self.set_visual_state(primary.remaining_percent)
        self.set_indicator_text(primary.remaining_percent)
        self.summary_item.set_label(
            f"Restant: {primary.remaining_percent}% sur la fenetre courte"
        )
        self.primary_item.set_label(format_window_line("Fenetre courte", primary))
        self.secondary_item.set_label(format_window_line("Fenetre longue", secondary))
        self.plan_item.set_label(
            f"Plan: {state.get('plan', 'inconnu')} | Source: {state.get('source', 'extension')}"
        )
        self.last_check_item.set_label(
            f"Dernier check: {format_hhmm_from_iso(state.get('updated_at'))}"
        )
        return True

    def quit(self, _widget) -> None:
        Gtk.main_quit()


def main() -> int:
    ensure_config_dir()
    GPTokensIndicator()
    Gtk.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
