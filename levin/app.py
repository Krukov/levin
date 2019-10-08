from . import components
from .core.app import Application as _Application
from .core.finder import init_app_component_imports

__all__ = ["app"]

app = _Application(
    components=[
        components.LoggerComponent(),
        components.handle_error(),
        components.TimeLimit(),
        components.HttpRouter(),
        components.RunProcess(),
        components.SyncToAsync(),
        components.Profile(),
        components.JsonFormat(),
        components.TextFormat(),
        components.TemplateFormat(),
    ]
)

init_app_component_imports(app, "app")
