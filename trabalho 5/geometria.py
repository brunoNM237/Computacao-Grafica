import sys
from pathlib import Path

import glfw
import glm
import moderngl
import numpy as np


def criar_cubo(uv_escala=8.0):
    """Cubo unitario: 6 faces x 4 vertices (24 vertices, 12 triangulos CCW)."""
    s = uv_escala
    faces = [
        (( 0,  0,  1), [(-0.5, -0.5,  0.5), ( 0.5, -0.5,  0.5), ( 0.5,  0.5,  0.5), (-0.5,  0.5,  0.5)]),
        (( 0,  0, -1), [( 0.5, -0.5, -0.5), (-0.5, -0.5, -0.5), (-0.5,  0.5, -0.5), ( 0.5,  0.5, -0.5)]),
        (( 1,  0,  0), [( 0.5, -0.5,  0.5), ( 0.5, -0.5, -0.5), ( 0.5,  0.5, -0.5), ( 0.5,  0.5,  0.5)]),
        ((-1,  0,  0), [(-0.5, -0.5, -0.5), (-0.5, -0.5,  0.5), (-0.5,  0.5,  0.5), (-0.5,  0.5, -0.5)]),
        (( 0,  1,  0), [(-0.5,  0.5,  0.5), ( 0.5,  0.5,  0.5), ( 0.5,  0.5, -0.5), (-0.5,  0.5, -0.5)]),
        (( 0, -1,  0), [(-0.5, -0.5, -0.5), ( 0.5, -0.5, -0.5), ( 0.5, -0.5,  0.5), (-0.5, -0.5,  0.5)]),
    ]
    uvs = [(0, 0), (s, 0), (s, s), (0, s)]

    verts, inds = [], []
    for f, (n, cantos) in enumerate(faces):
        b = f * 4
        for p, uv in zip(cantos, uvs):
            verts.append((*p, *n, *uv))
        inds.extend([b, b + 1, b + 2, b, b + 2, b + 3])

    return np.array(verts, dtype='f4'), np.array(inds, dtype='u4')