import ctypes
import math

from OpenGL.GL import *


def setup_night_lighting():
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

    # Moon mostly from -X a bit up so sideways light lamp stays more overhead
    glLightfv(GL_LIGHT0, GL_POSITION, (-0.92, 0.38, 0.08, 0.0))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.18, 0.20, 0.26, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.52, 0.58, 0.74, 1.0))
    glLightfv(GL_LIGHT0, GL_SPECULAR, (0.06, 0.07, 0.09, 1.0))
    glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.12, 0.135, 0.18, 1.0))


def setup_lamp_lights(
    lamp_light_ids,
    diffuse_strength=(10.5, 8.6, 5.2),
    attenuation_linear=0.022,
    attenuation_quad=0.0022,
    spot_cutoff_deg=26.0,
    spot_exponent=45.0,
):
    for lid in lamp_light_ids:
        glEnable(lid)
        glLightfv(lid, GL_AMBIENT, (0.012, 0.010, 0.006, 1.0))
        glLightfv(lid, GL_DIFFUSE, (*diffuse_strength, 1.0))
        glLightfv(lid, GL_SPECULAR, (0.22, 0.18, 0.12, 1.0))
        glLightf(lid, GL_CONSTANT_ATTENUATION, 1.0)
        glLightf(lid, GL_LINEAR_ATTENUATION, attenuation_linear)
        glLightf(lid, GL_QUADRATIC_ATTENUATION, attenuation_quad)
        glLightf(lid, GL_SPOT_CUTOFF, spot_cutoff_deg)
        glLightf(lid, GL_SPOT_EXPONENT, spot_exponent)
        glLightfv(lid, GL_SPOT_DIRECTION, (0.0, -1.0, 0.0))


def select_active_lamp_indices(cam_x, cam_z, lamp_positions, max_lights, required_indices=None):
    ranked = sorted(
        list(enumerate(lamp_positions)),
        key=lambda it: (it[1][0] - cam_x) * (it[1][0] - cam_x) + (it[1][1] - cam_z) * (it[1][1] - cam_z),
    )
    active_indices = [it[0] for it in ranked[:max_lights]]
    for ri in required_indices or []:
        if 0 <= ri < len(lamp_positions) and ri not in active_indices and len(active_indices) >= max_lights:
            active_indices[-1] = ri
    return active_indices


def apply_active_lights(lamp_light_ids, active_indices, lamp_positions, lamp_height):
    for idx, lid in enumerate(lamp_light_ids):
        if idx < len(active_indices):
            li = active_indices[idx]
            lx, lz = lamp_positions[li]
            glEnable(lid)
            glLightfv(lid, GL_POSITION, (lx, lamp_height, lz, 1.0))
            glLightfv(lid, GL_SPOT_DIRECTION, (0.0, -1.0, 0.0))
        else:
            glDisable(lid)


def enforce_night_lighting_state():
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)


def _normalize3(v):
    x, y, z = v
    n = math.sqrt(x * x + y * y + z * z)
    if n < 1e-20:
        return (0.0, 1.0, 0.0)
    return (x / n, y / n, z / n)


def planar_shadow_matrix(light4, plane4):
    # Old planar shadow matrix column major for glMultMatrixf main uses per vertex projection instead
    # Plane (a b c d) for ax+by+cz+d=0 light (x y z w) w=0 directional w=1 point
    lx, ly, lz, lw = light4
    px, py, pz, pd = plane4
    dot = px * lx + py * ly + pz * lz + pd * lw
    rows = []
    for r in range(4):
        row = []
        for c in range(4):
            diag = dot if r == c else 0.0
            row.append(diag - [lx, ly, lz, lw][r] * [px, py, pz, pd][c])
        rows.append(row)
    col_major = []
    for c in range(4):
        for r in range(4):
            col_major.append(rows[r][c])
    return (ctypes.c_float * 16)(*col_major)


def shadow_matrix_directional(light_dir_toward, plane_y):
    # Vector toward the light same idea as GL directional w=0
    dx, dy, dz = _normalize3(light_dir_toward)
    plane = (0.0, 1.0, 0.0, -float(plane_y))
    return planar_shadow_matrix((dx, dy, dz, 0.0), plane)


def shadow_matrix_point(light_pos, plane_y):
    # Point bulb at xyz
    lx, ly, lz = light_pos
    plane = (0.0, 1.0, 0.0, -float(plane_y))
    return planar_shadow_matrix((lx, ly, lz, 1.0), plane)
