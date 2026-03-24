"""Procedural trees and instanced placement"""

import math
import random
from OpenGL.GL import *
from OpenGL.GLU import *

from model_obj import draw_scene_mesh

_quadric = None


def _get_quadric():
    global _quadric
    if _quadric is None:
        _quadric = gluNewQuadric()
        gluQuadricNormals(_quadric, GLU_SMOOTH)
    return _quadric


def _point_in_outer_tree_margin(
    x,
    z,
    rx_inner=34.0,
    rz_inner=30.0,
    road_width=4.0,
    ground_radius=47.2,
    past_road_pad=0.035,
    inside_disk_margin=1.15,
):
    """True if xz is outside the road oval and inside the ground margin"""
    rx_o = rx_inner + road_width
    rz_o = rz_inner + road_width
    eo = (x / rx_o) ** 2 + (z / rz_o) ** 2
    if eo <= 1.0 + past_road_pad:
        return False
    r2 = x * x + z * z
    rm = max(2.0, ground_radius - inside_disk_margin)
    if r2 > rm * rm:
        return False
    return True


def build_natural_tree_instances(
    *,
    has_asset_mesh,
    n_range=(18, 30),
    ground_radius=47.2,
    base_min_spacing=2.5,
    seed=None,
):
    """Build random tree instances on the outer ring (mesh vs procedural cones)"""
    if seed is not None:
        random.seed(seed)
    target_n = random.randint(n_range[0], n_range[1])
    placed = []
    out = []

    w_mesh = 0.52 if has_asset_mesh else 0.0
    w_proc = 1.0 - w_mesh
    if w_proc < 0.2:
        w_proc = 0.2
        s = w_mesh + w_proc
        w_mesh /= s
        w_proc /= s

    max_attempts = target_n * 450
    for _ in range(max_attempts):
        if len(out) >= target_n:
            break
        x = random.uniform(-ground_radius, ground_radius)
        z = random.uniform(-ground_radius, ground_radius)
        if not _point_in_outer_tree_margin(x, z, ground_radius=ground_radius):
            continue

        spacing = base_min_spacing + random.uniform(0.0, 2.1)
        clash = False
        for px, pz in placed:
            if (x - px) ** 2 + (z - pz) ** 2 < spacing * spacing:
                clash = True
                break
        if clash:
            continue

        placed.append((x, z))
        roll = random.random()
        kind = "mesh" if (roll < w_mesh and has_asset_mesh) else "proc"

        mesh_scale = random.uniform(0.72, 1.22) if kind == "mesh" else 1.0
        proc_scale = random.uniform(0.72, 1.18) if kind == "proc" else 1.0

        tint_dim = random.uniform(0.82, 0.98)

        out.append(
            {
                "x": x,
                "z": z,
                "kind": kind,
                "mesh_scale": mesh_scale,
                "proc_scale": proc_scale,
                "tint_dim": tint_dim,
            }
        )

    if not out and target_n > 0:
        for tx, tz in TREE_SITES[: min(8, len(TREE_SITES))]:
            out.append(
                {
                    "x": tx,
                    "z": tz,
                    "kind": "mesh" if has_asset_mesh else "proc",
                    "mesh_scale": 1.0,
                    "proc_scale": 0.95,
                    "tint_dim": 0.9,
                }
            )
    return out


# Fallback positions when random placement fails
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


def draw_pine_tree(x, ground_y, z, scale=1.0, dim=1.0):
    """Procedural pine trunk and stacked cones with dimmed colors for night"""
    q = _get_quadric()
    d = max(0.35, min(1.5, float(dim)))
    trunk_r0, trunk_r1, trunk_h = 0.22 * scale, 0.16 * scale, 2.0 * scale
    glPushMatrix()
    glTranslatef(x, ground_y, z)

    glRotatef(-90.0, 1.0, 0.0, 0.0)
    glColor3f(0.14 * d, 0.10 * d, 0.08 * d)
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
        glColor3f(0.04 * d, g * d, 0.055 * d)
        gluCylinder(q, rad, 0.0, h, 10, 1)
        glTranslatef(0.0, 0.0, h * 0.55)

    glPopMatrix()
    glColor3f(1.0, 1.0, 1.0)


def draw_static_trees(
    ground_y=-1.0,
    tree_instances=None,
    scene_mesh=None,
    material_to_texid=None,
    obj_tint=(0.55, 0.55, 0.62),
):
    """Draw trees from instance dictionaries"""
    if not tree_instances:
        tree_instances = [
            {
                "x": tx,
                "z": tz,
                "kind": "mesh" if scene_mesh is not None else "proc",
                "mesh_scale": 1.0,
                "proc_scale": 0.9 + 0.05 * k,
                "tint_dim": 0.9,
            }
            for k, (tx, tz) in enumerate(TREE_SITES)
        ]

    for inst in tree_instances:
        td = float(inst.get("tint_dim", 0.92))
        tint_m = (obj_tint[0] * td, obj_tint[1] * td, obj_tint[2] * td)
        tx = inst["x"]
        tz = inst["z"]
        kind = inst["kind"]

        if kind == "mesh" and scene_mesh is not None:
            mt = material_to_texid if material_to_texid is not None else {}
            draw_scene_mesh(
                scene_mesh,
                mt,
                tx,
                ground_y,
                tz,
                tint=tint_m,
                uniform_scale=inst.get("mesh_scale", 1.0),
            )
        else:
            draw_pine_tree(
                tx,
                ground_y,
                tz,
                scale=inst.get("proc_scale", 1.0),
                dim=td,
            )
