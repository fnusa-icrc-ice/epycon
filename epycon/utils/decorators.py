from typing import (
    Union,    
    get_origin as _get_origin,
    get_args as _get_args,
    _SpecialForm,
)

def checktypes(func):
    """ Type checking wrapper.

    Args:
        func (_type_): _description_
    """
    def validate(*args, **kwargs):
        parameters_mapping = dict(zip(func.__code__.co_varnames, args))
        parameters_mapping.update(kwargs)
        for key, value in func.__annotations__.items():
            if key == 'return':
                # skip return type check
                continue

            if isinstance(_get_origin(value), _SpecialForm):
                # if typing.Union or typing.ClassVar
                type_hint = _get_args(value)
            else:
                if value is None:
                    type_hint = type(value)
                else:
                    type_hint = value

            if not isinstance(parameters_mapping[key], type_hint):
                raise TypeError(
                    f'Expected type `{type_hint}` for input argument `{key}`',
                    f' got type `{type(value)}` instead'
                )

        return func(*args, **kwargs)
    return validate
