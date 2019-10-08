import inspect
import sys
import types
from importlib.machinery import ModuleSpec


class AppFinder:
    def __init__(self, name):
        self._name = name

    def find_spec(self, fullname, path=None, target=None):
        """
        This functions is what gets executed by the loader.
        """
        name_parts = fullname.split(".")
        if name_parts[0] != self._name or len(name_parts) > 3:
            return None
        if len(name_parts) == 1:
            return ModuleSpec(fullname, self)
        else:
            return ModuleSpec(fullname, self)

    def create_module(self, spec):
        """
        Module creator. Returning None causes Python to use the default module creator.
        """
        return None

    def exec_module(self, module):
        """
        Module executor.
        """
        module.__path__ = []
        return module


def component_to_module(component):
    module = types.ModuleType(component.name, "Pseudo module for component")
    module.__file__ = inspect.getfile(component.__class__)
    for attr, value in inspect.getmembers(component):
        if not attr.startswith("_") and attr != "name":
            setattr(module, attr, value)
    return module


def init_app_component_imports(app, name):
    sys.meta_path.append(AppFinder(name))
