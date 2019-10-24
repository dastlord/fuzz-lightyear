import inspect
from functools import lru_cache
from functools import wraps
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple


@lru_cache(maxsize=1)
def get_setup_fixtures() -> List:
    """
    This is a global list that contains the functions that should be executed
    before fuzz-lightyear begins executing tests.

    :rtype: list(function)
    """
    return []


@lru_cache(maxsize=1)
def get_user_defined_mapping() -> Dict:
    """
    This is essentially a global variable, within a function scope, because
    this returns a reference to the cached dictionary.

    :rtype: dict(str => function)
    """
    return {}


@lru_cache(maxsize=1)
def get_included_tags() -> Set[str]:
    """This is a global set containing tags which should
    be fuzzed. Each element is a string for the tag which
    should be included.
    """
    return set()


@lru_cache(maxsize=1)
def get_excluded_operations() -> Dict[str, Optional[str]]:
    """
    This is a global dictionary containing fuzzing-excluded operations.
    Operation id's are keys. Tags are values, if the user provided them.
    If you don't care about the operation's tag, you can get just the
    excluded operations with `get_excluded_operations().keys()`.

    :rtype: dict(str => str)
    """
    return {}


@lru_cache(maxsize=1)
def get_non_vulnerable_operations() -> Dict[str, Optional[str]]:
    """
    This is a global dictionary containing non-vulnerable operations.
    Operation ids are keys. Tags are values, if the user provided them.
    If you don't care about the operation's tag, you can get just the
    excluded operations with `get_excluded_operations().keys()`.

    :rtype: dict(str => str)
    """
    return {}


def clear_cache() -> None:
    """ Clear the cached values for fixture functions """
    for value in get_user_defined_mapping().values():
        value._fuzz_cache = None


def inject_user_defined_variables(func: Callable) -> Callable:
    """
    This decorator allows the use of user defined variables in functions.
    e.g.
        >>> @fuzz_lightyear.register_factory('name')
        ... def name():
        ...     return 'freddy'
        >>>
        >>> @inject_user_defined_variables
        ... def foobar(name):
        ...     print(name)     # freddy
    """
    mapping = get_user_defined_mapping()

    @wraps(func)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if getattr(func, '_fuzz_cache', None) is not None:
            return func._fuzz_cache  # type: ignore

        expected_args = _get_injectable_variables(func)
        type_annotations = inspect.getfullargspec(func).annotations

        for index, arg_name in enumerate(expected_args):
            if index < len(args):
                # This handles the case of explicitly supplied
                # positional arguments, so that we don't pass func
                # two values for the same argument.
                continue

            if arg_name not in mapping:
                raise TypeError

            value = mapping[arg_name]()
            if (
                arg_name in type_annotations
                and not isinstance(type_annotations[arg_name], type(List))
            ):
                # If type annotations are used, use that to cast
                # values for input.
                value = type_annotations[arg_name](value)

            kwargs[arg_name] = value

        func._fuzz_cache = func(*args, **kwargs)  # type: ignore
        return func._fuzz_cache  # type: ignore

    return wrapped


def _get_injectable_variables(func: Callable) -> Tuple[str, ...]:
    """
    The easiest way to understand this is to see it as an example:

        >>> def func(a, b=1, *args, c, d=2, **kwargs):
        ...     e = 5
        >>>
        >>> print(func.__code__.co_varnames)
        ('a', 'b', 'c', 'd', 'args', 'kwargs', 'e')
        >>> print(func.__code__.co_argcount)    # `a` and `b`
        2
        >>> print(func.__code__.co_kwonlyargcount)  # `c` and `d`
        2
    """
    variable_names = func.__code__.co_varnames
    arg_count = func.__code__.co_argcount + func.__code__.co_kwonlyargcount

    return variable_names[:arg_count]
