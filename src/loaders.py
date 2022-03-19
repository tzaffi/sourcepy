import importlib.machinery
import importlib.util
import inspect
import sys

from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any, Iterator, List, Optional, get_origin

from casters import isprimitive, iscollection



def load_path(module_path: Path) -> ModuleType:
    module_name = module_path.stem.replace('-', '_')
    spec = importlib.util.spec_from_loader(
        module_name,
        importlib.machinery.SourceFileLoader(module_name, str(module_path))
    )
    # spec_from_loader could be None only if loader was not supplied
    module = importlib.util.module_from_spec(spec) # type: ignore[arg-type]
    # results from above implied Optional[ModuleSpec]
    spec.loader.exec_module(module) # type: ignore [union-attr]
    sys.modules[module_name] = module
    return module


def get_definitions(obj: Any, parents: Optional[List] = None) -> Iterator[dict]:
    if parents is None:
        parents = []
    members = dict(inspect.getmembers(obj))
    if '__all__' in members:
        members = {k:v for k,v in members.items() if k in members['__all__']}
    else:
        members = {k:v for k,v in members.items() if not k.startswith('_')}
    for name, value in members.items():
        if is_unsourceable(value):
            continue
        if isprimitive(value) or iscollection(value):
            yield {'type': 'variable', 'name': name, 'value': value, 'parents': parents}
        elif callable(value):
            yield {'type': 'function', 'name': name, 'value': value, 'parents': parents}
        else:
            yield from get_definitions(value, parents + [name])


def get_callable(parent: ModuleType, method_str: str) -> Callable:
    attr_list = method_str.split('.')
    current = parent
    for attr in attr_list:
        current = getattr(current, attr)
    if not callable(current):
        raise ValueError(f'{method_str} does not point to a valid callable')
    return current

def is_unsourceable(obj: Any) -> bool:
    return any([
        isinstance(obj, (type, ModuleType)),
        isinstance(get_origin(obj), type),
    ])
