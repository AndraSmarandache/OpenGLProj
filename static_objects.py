# Static scenery: procedural pine trees (no external meshes — reads well as night silhouettes).
# Industry options elsewhere: textured billboards (PNG + alpha), instanced low-poly GLTF, or speedtree-style assets.

import math
from OpenGL.GL import *
from OpenGL.GLU import *

_quadric = None


def _get_quadric():
    global _quadric
    if _quadric is None:
        _quadric = gluNewQuadric()
        gluQuadricNormals(_quadric, GLU_SMOOTH)
    return _quadric


# (x, z) on flat grass, between the road ring and ground edge — "middle of nowhere"
TREE_SITES = [
    (43.0, 0.0),
    (41.5, 10.0),
    (38.0, -18.0),
    (-42.0, 6.0),
    (-40.0, -14.0),
    (-36.0, -22.0),
    (8.0, 43.5),
    (-12.0, -42.0),
    (22.0, 39.0),
    (-28.0, 37.0),
    (35.0, -32.0),
    (-44.0, -5.0),
]


def draw_pine_tree(x, ground_y, z, scale=1.0):
    """Trunk + stacked cones (gluCylinder top=0) — night colours, lit by scene lights."""
    q = _get_quadric()
    trunk_r0, trunk_r1, trunk_h = 0.22 * scale, 0.16 * scale, 2.0 * scale
    glPushMatrix()
    glTranslatef(x, ground_y, z)

    glRotatef(-90.0, 1.0, 0.0, 0.0)
    glColor3f(0.14, 0.10, 0.08)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.0, 0.0, 0.0, 1.0))
    gluCylinder(q, trunk_r0, trunk_r1, trunk_h, 10, 1)

    glTranslatef(0.0, 0.0, trunk_h * 0.92)
    layers = [
        (1.15 * scale, 1.7 * scale),
        (0.92 * scale, 1.45 * scale),
        (0.68 * scale, 1.15 * scale),
    ]
    for idx, (rad, h) in enumerate(layers):
        g = 0.08 + idx * 0.012
        glColor3f(0.04, g, 0.055)
        gluCylinder(q, rad, 0.0, h, 10, 1)
        glTranslatef(0.0, 0.0, h * 0.55)

    glPopMatrix()
    glColor3f(1.0, 1.0, 1.0)


def draw_static_trees(ground_y=-1.0):
    for i, (tx, tz) in enumerate(TREE_SITES):
        s = 0.85 + 0.12 * (i % 4)
        draw_pine_tree(tx, ground_y, tz, scale=s)
