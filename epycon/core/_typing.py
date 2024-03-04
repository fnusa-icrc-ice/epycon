import sys 

# For Python 3.5 and below, use the 'typing' module for type hinting
if sys.version_info >= (3, 6):
    from typing import (
        Union as Union,
        List as List,
        Dict as Dict,
        Sequence as Sequence,
        Tuple as Tuple,
        Any as Any,
        Callable,
        Iterator,
        Optional,
    )

    from os import (
        PathLike as PathLike,
    )
    
    from numpy import (        
        ndarray as NumpyArray
    )

    from numpy.typing import (
        ArrayLike as ArrayLike,        
    )

else:
    # For other versions of Python, raise an error
    raise RuntimeError("Unsupported Python version")
