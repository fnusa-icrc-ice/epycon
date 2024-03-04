from typing import Union
from struct import unpack

def readbin(
    file_path, 
    start_byte: Union[int, None] = None,
    bytes_to_read: Union[int, None] = None,    
    ):
    """_summary_

    Args:
        file_path (_type_): _description_
        start_byte (Union[int, None], optional): _description_. Defaults to None.
        bytes_to_read (Union[int, None], optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """
    with open(file_path, "rb") as file:
        if start_byte:
            file.seek(start_byte, 0)
        barray = file.read(bytes_to_read)    
        
    return barray


def readchunk(f_object, chunk_size):    
    """_summary_

    Args:
        f_object (_type_): _description_
        chunk_size (_type_): _description_

    Yields:
        _type_: _description_
    """
    while True:
        chunk = f_object.read(chunk_size)
        if not chunk:
            break
        else:
            yield chunk


def parsebin(
    barray: bytearray,
    fchar: str,
    ):

    unpacked_barray = unpack(fchar, barray)

    if len(unpacked_barray) != 1:
        return unpacked_barray
    else:
        return unpacked_barray[0]