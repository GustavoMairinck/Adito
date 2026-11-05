import os
import logging

try:
    from rich.console import Console
    from rich.markup import escape
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
except ImportError:  # pragma: no cover - keeps local checks working before image rebuild.
    Console = None
    escape = None
    Panel = None
    Table = None
    Text = None


_FORCE_TERMINAL = os.getenv("RICH_FORCE_TERMINAL", "1") != "0"


if Console:
    console = Console(
        force_terminal=_FORCE_TERMINAL,
        color_system="truecolor",
        highlight=False,
        soft_wrap=True,
    )
else:
    console = None


STYLES = {
    "auth": "magenta",
    "chat": "cyan",
    "graph": "blue",
    "mcp": "purple",
    "bi": "green",
    "rewrite": "yellow",
    "db": "bright_blue",
    "admin": "bright_green",
    "dashboard": "bright_cyan",
    "error": "red",
}

LEVEL_STYLES = {
    logging.DEBUG: "dim",
    logging.INFO: "cyan",
    logging.WARNING: "yellow",
    logging.ERROR: "bold red",
    logging.CRITICAL: "bold white on red",
}


def _style(scope: str, fallback: str = "cyan") -> str:
    return STYLES.get(scope.lower(), fallback)


def _escape(message: str) -> str:
    if escape:
        return escape(str(message))
    return str(message)


def _print_line(scope: str, message: str, style: str):
    line = f"[{scope}] {message}"
    if console:
        console.print(_escape(line), style=style)
    else:
        print(line)


def log_section(title: str, scope: str = "chat"):
    style = _style(scope)
    if console:
        console.rule(f"[bold {style}]{title}[/bold {style}]")
    else:
        print(f"========== {title} ==========")


def log_info(scope: str, message: str):
    _print_line(scope, message, _style(scope))


def log_success(scope: str, message: str):
    _print_line(scope, message, "green")


def log_warning(scope: str, message: str):
    _print_line(scope, message, "yellow")


def log_error(scope: str, message: str):
    _print_line(scope, message, "bold red")


def log_kv(scope: str, title: str, data: dict):
    style = _style(scope)
    if not console or not Table:
        print(f"[{scope}] {title}: {data}")
        return

    table = Table(title=title, title_style=f"bold {style}", show_header=False, box=None)
    table.add_column("Campo", style="bold")
    table.add_column("Valor")
    for key, value in data.items():
        table.add_row(str(key), str(value))
    console.print(table)


def log_table(scope: str, title: str, columns: list[str], rows: list[list[object]]):
    style = _style(scope)
    if not console or not Table:
        print(f"[{scope}] {title}:")
        for row in rows:
            print(" | ".join(str(value) for value in row))
        return

    table = Table(
        title=title,
        title_style=f"bold {style}",
        header_style=f"bold {style}",
        border_style=style,
        expand=False,
        show_lines=False,
        padding=(0, 1),
    )
    for column in columns:
        table.add_column(column, overflow="fold")
    for row in rows:
        table.add_row(*[str(value) for value in row])
    console.print(table)


def log_panel(scope: str, title: str, body: str):
    style = _style(scope)
    if console and Panel:
        console.print(Panel(body, title=title, border_style=style))
    else:
        print(f"[{scope}] {title}\n{body}")


def log_node_start(node: str, message: str = ""):
    suffix = f" | {message}" if message else ""
    log_info("bi", f"▶ início {node}{suffix}")


def log_node_end(node: str, message: str = ""):
    suffix = f" | {message}" if message else ""
    log_success("bi", f"✓ fim {node}{suffix}")


class BackendRichHandler(logging.Handler):
    """Handler compatível com LOGGING do Django, com fallback sem Rich."""

    def __init__(self, *args, level=logging.NOTSET, **kwargs):
        super().__init__(level=level)
        self.formatter = logging.Formatter("%(levelname)-8s %(message)s")

    def emit(self, record):
        message = self.format(record)
        if "GET /health" in message:
            return
        if console and Text:
            style = LEVEL_STYLES.get(record.levelno, "white")
            console.print(Text(message, style=style))
            if record.exc_info:
                console.print_exception(show_locals=False)
            return
        print(message)

    def setFormatter(self, fmt):
        self.formatter = fmt
