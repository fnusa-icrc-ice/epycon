import os
from platform import system
from datetime import datetime
# from yaml.constructor import SafeConstructor

from epycon.core._typing import (
    List,
)

from re import (
    sub,
    match,
)
from json import (
    dumps,
    loads,
)

# ----------------------- HELPER FUNCTIONS ------------------------------

def default_log_path():
    """Returns a platform-specific default log file path."""
    log_name = "epycon.log"
    
    this_system = system()
    
    if this_system == "Windows":
        log_path = os.path.join(os.environ["APPDATA"], "Local", "epycon")
    
    elif this_system == "Linux" or this_system == "Darwin":
        log_path = os.path.join("/var/log/", "epycon")
    
    else:
        # Fallback to a generic location for other systems
        log_path = ""

    try:
        os.makedirs(log_path, exist_ok=True)
    except OSError as e:        
        print(f"Error creating log directory: {e}. Generic location will be used instead.")
        log_path = ""
    
    return os.path.join(log_path, f"{log_name}")


def deep_override(cfg_dict: dict, keys: list, value):
    """ Override value in nested dictionary fields.

    Args:
        cfg_dict (dict): source nested dictionary
        keys (list): list of keys sorted from the top to bottom level
        value (_type_): value to be stored

    Raises:
        KeyError: _description_

    Returns:
        _type_: _description_
    """
    current_dict = cfg_dict
    
    for key in keys[:-1]:  # Iterate through all keys except the last one
        current_dict = current_dict[key]  # Directly access nested dicts
    if keys[-1] in current_dict:
        current_dict[keys[-1]] = value
    else:
        raise KeyError(f"Invalid key `{keys[-1]}`")
    
    return cfg_dict


def difftimestamp(timestamps: List[float]):
    assert len(timestamps) == 2
    return abs((datetime.fromtimestamp(timestamps[0]) - datetime.fromtimestamp(timestamps[1])).total_seconds())


def safe_string(name:str, safe_char: str = '-'):
    """_summary_

    Args:
        name (str): _description_

    Returns:
        _type_: _description_
    """    
    replace_chars = r"[,;\/:\\]"
    
    return sub(replace_chars, safe_char, name)

def pretty_json(custom_dict):
    """Saves dictionary into pretty json omitting empty space within time series data.

    Args:
        custom_dict (_type_): _description_

    Raises:
        ValueError: _description_

    Returns:
        _type_: _description_
    """
    s = dumps(custom_dict, indent=4, separators=(',', ':'))
    s = sub(r"\s+(?=[+-]?[0-9^()])", '', s)
    s = sub(r"(?<=[0-9])+\s+(?=[\]])", '', s)

    # check json string validity
    try:
        loads(s)
    except ValueError:
        raise ValueError
    else:
        return s



