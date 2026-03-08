#!/usr/bin/env python3
'''
'''

import numpy as np

def min_max_from_dtype(dtype):
    """
    Get the minimum and maximum representable values from a NumPy data type.
    
    Parameters:
    - dtype: NumPy data type
    
    Returns:
    - min_val: minimum representable value
    - max_val: maximum representable value
    """
    if np.issubdtype(dtype, np.integer):
        info = np.iinfo(dtype)
    elif np.issubdtype(dtype, np.floating):
        info = np.finfo(dtype)
    else:
        raise ValueError("Unsupported dtype")

    return info.min, info.max


def main():
    
    # Example usage:
    dtype = np.uint16
    min_val, max_val = min_max_from_dtype(dtype)
    print("Minimum representable value for dtype {}: {}".format(dtype, min_val))
    print("Maximum representable value for dtype {}: {}".format(dtype, max_val))
        
        
        
        
    
    
        
if __name__ == "__main__":
    main()




