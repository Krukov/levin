from . import components
from .core.app import Application as _Application

__all__ = ["app"]

app = _Application(
    components=[
        components.PatchRequest(),
        components.h2.Push(),
        components.LoggerComponent(),
        components.ErrorHandle(),
        components.limit.TimeLimit(),
        components.HttpRouter(),
        components.RunProcess(),
        components.ProfileHandler(),
        components.SyncToAsync(),
        components.JsonFormat(),
        components.TextFormat(),
        components.TemplateFormat(),

        components.InjectFromScope(),
        components.SkipRequest(),
        components.Cli(),
    ]
)
