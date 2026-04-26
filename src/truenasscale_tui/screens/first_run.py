from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Label


class FirstRunScreen(Screen):
    DEFAULT_CSS = """
    FirstRunScreen {
        align: center middle;
    }
    FirstRunScreen #form {
        width: 60;
        height: auto;
        padding: 2 4;
        border: thick $primary;
        background: $surface;
    }
    FirstRunScreen Label {
        height: 1;
        margin-bottom: 0;
    }
    FirstRunScreen Input {
        margin-bottom: 1;
    }
    FirstRunScreen #title-label {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    FirstRunScreen #connect-btn {
        margin-top: 1;
    }
    """

    BINDINGS = [("q", "app.quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Center():
            with Vertical(id="form"):
                yield Label("TrueNASScale-TUI — First Run Setup", id="title-label")
                yield Label("TrueNAS Host / IP")
                yield Input(
                    placeholder="192.168.1.100 or truenas.local",
                    id="server-host",
                )
                yield Label("Username")
                yield Input(
                    placeholder="admin",
                    id="username",
                    value="admin",
                )
                yield Label("API Key")
                yield Input(
                    placeholder="1-abc...",
                    id="api-key",
                    password=True,
                )
                yield Checkbox(value=True, label="Verify SSL", id="verify-ssl")
                yield Button("Connect", variant="primary", id="connect-btn")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "connect-btn":
            self._save_and_continue()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "api-key":
            self._save_and_continue()

    def _save_and_continue(self) -> None:
        from ..app import ScaleApp
        from ..config import ScaleConfig, save_config

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

        app: ScaleApp = self.app  # type: ignore[assignment]
        app._config = cfg
        app.pop_screen()
        app.push_screen("dashboard")
        app.connect_and_subscribe()
