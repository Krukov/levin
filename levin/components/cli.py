import argparse
import inspect
import sys
from typing import *

from levin.core.component import Component

_PROPERTY = "_command"


def command(method):
    setattr(method, _PROPERTY, True)
    return method


class Cli(Component):
    name = "cli"

    def __init__(self, app):
        self.app = app

    @staticmethod
    def _get_commands(component: Component):
        for name, method in inspect.getmembers(component, predicate=inspect.ismethod):
            if getattr(method, _PROPERTY, None):
                yield method

    def _get_command(self, component: Component, command: str) -> Optional[Union[Callable, Awaitable]]:
        for command_ in self._get_commands(component):
            if command_.__name__ == command:
                return command_

    def _get_command_options(self, command: Callable) -> Iterable[Dict]:
        for param in inspect.signature(command).parameters.values():
            if param.annotation is param.empty:
                continue
            if issubclass(param.annotation, bool):
                yield {"dest": f"--{param.name}", "default": param.default, "required": False, "action": "store_true"}

            elif param.default is not param.empty:
                yield {
                    "option_strings": f"{param.name}",
                    "dest": param.name,
                    "default": param.default,
                    "type": param.annotation,
                    "nargs": "?",
                }
            else:
                yield {"option_strings": f"{param.name}", "dest": param.name, "type": param.annotation}

    def _cli_root(self, argv: List[str]):
        parser = argparse.ArgumentParser(description="Manage app", prog=__name__)
        subparsers = parser.add_subparsers(title="Components", metavar=" ", required=True)
        for component in self.app.components:
            if list(self._get_commands(component)):
                subparsers.add_parser(component.name, help=component.__class__.__doc__)

        parser.print_help()

    def _cli_component(self, argv: List[str]):
        component = self.app.get_component(argv[0])
        if not component:
            exec("E")
        parser = argparse.ArgumentParser(
            description=f"Manage component {argv[0]}",
            prog=argv[0],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        subparsers = parser.add_subparsers(title="Commands", metavar=" ", required=True)
        for command in self._get_commands(component):
            command_parser = subparsers.add_parser(
                command.__name__, help=command.__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
            )
            for arg in self._get_command_options(command):
                if "dest" in arg:
                    dest = arg.pop("dest")
                    command_parser.add_argument(dest, **arg)
                else:
                    command_parser.add_argument(**arg)
        if len(argv) == 1:
            parser.print_help()
        else:
            args = vars(parser.parse_args(argv[1:]))
            print(self._get_command(component, argv[1])(**args))

    def __call__(self, argv: List[str] = sys.argv[1:]):
        commands = len([_ for _ in argv if not _.startswith("-")])

        if commands == 0:
            self._cli_root(argv)
        else:
            self._cli_component(argv)
