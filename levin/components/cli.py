import argparse
import inspect
import sys
from typing import Awaitable, Callable, Dict, Iterable, List, Optional, Union

from levin.core.component import Component

_PROPERTY = "_command"


def command(method):
    setattr(method, _PROPERTY, True)
    return method


class Cli(Component):
    name = "cli"

    def init(self, app):
        self.app = app  # pylint: disable=attribute-defined-outside-init

    @staticmethod
    def _get_commands(component: Component):
        for _, method in inspect.getmembers(component, predicate=inspect.ismethod):
            if getattr(method, _PROPERTY, None):
                yield method

    def _get_command(self, component: Component, command_name: str) -> Optional[Union[Callable, Awaitable]]:
        for command_ in self._get_commands(component):
            if command_.__name__ == command_name:
                return command_
        return None

    def _get_command_options(self, command_func: Callable) -> Iterable[Dict]:
        for param in inspect.signature(command_func).parameters.values():
            if param.annotation is param.empty:
                continue
            if inspect.isclass(param.annotation):
                yield from self._get_for_type(param.annotation, param)
            elif hasattr(param.annotation, "__args__"):
                yield from self._get_for_type(param.annotation.__args__[0], param)

    @staticmethod
    def _get_for_type(_type, param):
        if issubclass(_type, bool):
            yield {"dest": f"--{param.name}", "default": param.default, "required": False, "action": "store_true"}

        elif param.default is not param.empty:
            yield {
                "option_strings": f"{param.name}",
                "dest": param.name,
                "default": param.default,
                "type": _type,
                "nargs": "?",
            }
        else:
            yield {"option_strings": f"{param.name}", "dest": param.name, "type": _type}

    def _cli_root(self):
        parser = argparse.ArgumentParser(description="Manage app", prog=__name__)
        subparsers = parser.add_subparsers(title="Components", metavar=" ", required=True)
        for component in self.app.components:
            if list(self._get_commands(component)):
                subparsers.add_parser(component.name, help=component.__class__.__doc__)

        parser.print_help()

    def _cli_component(self, argv: List[str]):
        component = self.app.get_component(argv[0])
        if not component:
            exit(2)

        parser = self._get_parser_for_component(component, prog=argv[0])
        if len(argv) == 1:
            parser.print_help()
        else:
            args = vars(parser.parse_args(argv[1:]))
            result = self._get_command(component, argv[1])(**args)
            if result:
                print(result)

    def _get_parser_for_component(self, component, prog):
        parser = argparse.ArgumentParser(
            description=f"Manage component {prog}", prog=prog, formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        subparsers = parser.add_subparsers(title="Commands", metavar=" ", required=True)
        for command_ in self._get_commands(component):
            self._add_command_argument(command_, subparsers)
        return parser

    def _add_command_argument(self, command_, subparsers):
        command_parser = subparsers.add_parser(
            command_.__name__, help=command_.__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        for arg in self._get_command_options(command_):
            if "dest" in arg:
                dest = arg.pop("dest")
                command_parser.add_argument(dest, **arg)
            else:
                command_parser.add_argument(**arg)

    def __call__(self, argv: Iterable[str] = tuple(sys.argv[1:])):
        commands = len([_ for _ in argv if not _.startswith("-")])

        if commands == 0:
            self._cli_root()
        else:
            self._cli_component(argv)

    @command
    def run(self, port: int = 8000, host: str = "0.0.0.0", ssl_cert: str = "cert.crt", ssl_key: str = "cert.key"):
        """Run server for current app"""
        self.app.run(host, port, ssl=(ssl_cert, ssl_key))

    @command
    def components(self, values: bool = False, component: Optional[str] = None):
        """Print info for installed components"""
        components = ""
        for _component in self.app.components:
            if component and _component.name != component:
                continue
            components += f"\n{_component.name}: "
            if values or component:
                components += "\n" + "\n ".join(
                    [f"\t{param} = {getattr(_component, param)}" for param in _component.get_configure_params()]
                )
            else:
                components += "\t" + ", ".join(_component.get_configure_params())
        return components
