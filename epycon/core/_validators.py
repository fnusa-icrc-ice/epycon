import os

from epycon.core._typing import (
    Union, List, Any, Tuple, PathLike, ArrayLike, 
)

def _validate_int(
    name: str,
    value: Union[int, float],
    min_value: int = 0,
    mxn_value: Union[int, None] = None,
    ) -> Union[int, None]:
    """Checks whether the parameter is either
    an int or float that can be cast to an integer
    without loss of accuracy. Raises a ValueError otherwise.

    Args:
        value (Union[int, float]): _description_
        min_value (Union[int, None], optional): _description_. Defaults to None.
        mxn_value (Union[int, None], optional): _description_. Defaults to None.

    Raises:
        ValueError: _description_        
    Returns:
        Union[int, None]: _description_
    """    

    if value is None:
        return value

    messsage = f"Parameter `{name}` expected to be an {min_value} <= integer <= {mxn_value}"
    if isinstance(value, float):
        if int(value) != value:
            raise ValueError(messsage)
        value = int(value)

    if not isinstance(value, int):
        raise ValueError(messsage)

    if mxn_value is not None:
        assert mxn_value >= min_value
        if value > mxn_value:
            raise ValueError(messsage)

    if value < min_value:    
        raise ValueError(messsage)

    return int(value)


def _validate_str(
    name: str,
    value: str,
    valid_set: set,
    ) -> Union[str, None]:
    """Checks whether the parameter belongs to a set of valid parameters. Raises a ValueError otherwise.

    Args:
        value (str): _description_
        valid_set (set): Set of valid values.        

    Raises:
        ValueError: _description_        
    Returns:
        Union[int, None]: _description_
    """    

    if value is None:
        return value

    messsage = f"Parameter `{name}` containing `{value}` expected to be from {valid_set}"    
    if not isinstance(value, str):
        raise ValueError(messsage)

    if value not in valid_set:
        raise ValueError(messsage)

    return value


def _validate_version(
    version: Union[str, None],
    ) -> None:

    valid_x32, valid_x64 = {'4.1'}, {'4.2', '4.3'} 

    if version is None:
        return 'x64'
    
    if version in valid_x32:
        return 'x32'    
    elif version in valid_x64:
        return 'x64'
    else:
        raise ValueError(f'Invalid parameter `version`. Expected {52} ')


def _validate_reference(positive_ref, negative_ref):
    """ Validates electrical reference indices. If ref == 140 the lead is inactive with no recorded signal.

    Args:
        positive_ref (_type_): _description_
        negative_ref (_type_): _description_

    Raises:
        ValueError: _description_
        ValueError: _description_
    """
    if any(value == 140 for value in (negative_ref, positive_ref)):
        raise ValueError
    
    if all(value is None for value in (negative_ref, positive_ref)):
        raise ValueError        


def _validate_mount(mount: tuple, max: int):
    """ Validates custom mount schema for computing bipolar leads.

    Args:
        mount (tuple): 

    Raises:
        ValueError: _description_
        ValueError: _description_
    """
    if len(tuple) > 2:
        raise ValueError(f"Too many electrical sources for lead computation. Expected 2, got {len(tuple)}")
    
    for item in tuple:
        if not isinstance(item, int):
            raise TypeError(f"Electrical sources for lead computation requires type `int` not {type(item)}")
        
        if item > max:
            raise IndexError(f"Index {item} of the electrical source out of bounds. Max. {max}")


def _validate_tuple(
    name: str,
    arr: Union[List, Tuple],
    size: int,
    dtype: Any = str,    
    ) -> Union[List, Tuple]:
    """_summary_

    Args:
        name (str): _description_
        arr (Union[list, tuple]): _description_
        size (int): _description_
        dtype (Any, optional): _description_. Defaults to str.

    Raises:
        ValueError: _description_
        TypeError: _description_

    Returns:
        Union[list, tuple]: _description_
    """
    if arr is None:
        return arr

    messsage = f"Parameter `{name}` expected to have length of {size} and type {dtype}"
    if len(arr) != size:
        raise ValueError(messsage)

    if not all(isinstance(item, dtype) for item in arr):
        raise TypeError(messsage)
    

def _validate_path(
        f_path: Union[str, bytes, PathLike],
        name: str = "file or directory",
    ) -> Union[int, None]:

    """ Checks if the path exists and the user has read/write access.

    Args:
        path: The path to validate (string).

    Raises:
        ValueError: If the path does not exist, is not readable, or not writable.
    """
    message = f"Path to {name} does not exist or user does not have read/write permisson: {f_path}"
    
    if not os.path.exists(f_path):
        raise ValueError(message)

    # Check if it's a file
    if os.path.isfile(f_path):
        # Open and close for read access if it's a file
        try:
            with open(f_path, "r"):
                pass
        except OSError as e:
            raise ValueError(message)
    else:
        # Check if it's a directory and user has access (can list contents)
        try:
            os.listdir(f_path)
        except PermissionError as e:
            raise ValueError(message)
        
    return f_path