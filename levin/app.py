from . import components
from .core.app import Application as _Application

__all__ = ["app"]

app = _Application(
    components=[
        components.LoggerComponent(),
        components.handle_error(),
        components.TimeLimit(),
        components.HttpRouter(),
        components.ProfileHandler(),
        components.RunProcess(),
        components.SyncToAsync(),
        components.JsonFormat(),
        components.TextFormat(),
        components.TemplateFormat(),
    ]
)

app.add(components.Cli(app))
