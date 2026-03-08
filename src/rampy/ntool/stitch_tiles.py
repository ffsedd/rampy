#!/usr/bin/env python3
'''
python3 script
mail: ffsedd@gmail.com
'''

import logging
import numpy as np


def tiles_centered(tiles, axis=0):
    """Join tiles centered."""
    print("tiles_centered")
    if axis==0:
        tiles = [t.T for t in tiles]
        stitched = tiles_horizontally(tiles)
        stitched = stitched.T
    else:
        stitched = tiles_horizontally(tiles)

    return stitched

def tiles_horizontally(tiles):
    """Join tiles side by side centered vertically."""
    logging.debug(f"tiles_horizontally {tiles}")
    newhei =  max([a.shape[0] for a in tiles])
    print("newhei", newhei)
    tiles = [center_tile_vertically(t,newhei) for t in tiles]
    stitched = np.concatenate(tiles, axis=1)
    return stitched


def center_tile_vertically(t, newhei):
    """Add zeros at top and bottom so that tile is centered and of exact height."""

    h, w = t.shape
    if h != newhei:
#        print(h, newhei)
        new = np.zeros((newhei,w))
        h1 = (newhei-h)//2
        h2 = h1 + h
#        print(h1,h, h2)
        new[h1:h2] = t
    else:
        new = t
    return new



if __name__ == "__main__":
    logger = logging.getLogger()
    logging.basicConfig(
        level=20,
        format='!%(levelno)s [%(module)10s%(lineno)4d]    %(message)s'
        )
    t = np.array(
            [[1,1,12,5,2],
            [1,1,12,5,2],
            [1,1,12,5,2],
            [1,1,12,5,2]],
                 )

    u = np.array(
            [[1,1,12,5,2],
            [1,1,12,5,2],
            [1,1,12,5,2],
            [1,1,12,5,2],
            [1,1,12,5,2],
            [1,1,12,5,2]],
                 )

    z = tiles_centered((t,u), axis=1)
    print(z)