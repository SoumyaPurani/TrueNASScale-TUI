from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Label

from ..config import ScaleConfig, save_config


class SettingsScreen(Screen):
    DEFAULT_CSS = """
    SettingsScreen {
        align: center middle;
    }
    SettingsScreen #form {
        width: 60;
        height: auto;
        padding: 2 4;
        border: thick $primary;
        background: $surface;
    }
    SettingsScreen Label {
        height: 1;
        margin-bottom: 0;
    }
    SettingsScreen Input {
        margin-bottom: 1;
    }
    SettingsScreen #title-label {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    SettingsScreen #btn-row {
        layout: horizontal;
        height: auto;
        margin-top: 1;
    }
    SettingsScreen #btn-row Button {
        margin-right: 2;
    }
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("q", "app.quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        from ..app import ScaleApp

        app: ScaleApp = self.app  # type: ignore[assignment]
        cfg = app._config

        yield Header()
        with Center():
            with Vertical(id="form"):
                yield Label("Settings", id="title-label")
                yield Label("TrueNAS Host / IP")
                yield Input(
                    value=cfg.server_host,
                    placeholder="192.168.1.100 or truenas.local",
                    id="server-host",
                )
                yield Label("Username")
                yield Input(
                    value=cfg.username,
                    placeholder="admin",
                    id="username",
                )
                yield Label("API Key")
                yield Input(
                    value=cfg.api_key,
                    placeholder="1-abc...",
                    id="api-key",
                    password=True,
                )
                yield Checkbox(
                    value=cfg.verify_ssl,
                    label="Verify SSL",
                    id="verify-ssl",
                )
                with Vertical(id="btn-row"):
                    yield Button("Save", variant="primary", id="save-btn")
                    yield Button(
                        "Save & Reconnect", variant="success", id="reconnect-btn"
                    )
                    yield Button("Cancel", variant="default", id="cancel-btn")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        from ..app import ScaleApp

        btn_id = event.button.id
        if btn_id == "cancel-btn":
            self.app.pop_screen()
            return

        if btn_id in ("save-btn", "reconnect-btn"):
            app: ScaleApp = self.app  # type: ignore[assignment]
            host = self.query_one("#server-host", Input).value.strip()
            username = self.query_one("#username", Input).value.strip()
            api_key = self.query_one("#api-key", Input).value.strip()
            verify_ssl = self.query_one("#verify-ssl", Checkbox).value

            if not host or not api_key:
                self.notify("Host and API Key are required", severity="error")
                return

            cfg = ScaleConfig(
                server_host=host,
                username=username or "admin",
                api_key=api_key,
                verify_ssl=verify_ssl,
            )
            save_config(cfg)
            app._config = cfg
            self.notify("Settings saved")

            if btn_id == "reconnect-btn":
                self.app.pop_screen()
                app.action_logout()
