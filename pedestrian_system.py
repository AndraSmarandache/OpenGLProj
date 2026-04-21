import math
from dataclasses import dataclass

import glfw
from OpenGL.GL import *
from OpenGL.GLU import *


@dataclass
class PedestrianConfig:
    move_units_per_sec: float = 6.0
    sprint_mult: float = 1.7
    radius: float = 0.7
    move_radius_limit: float = 45.5


@dataclass
class PedestrianState:
    x: float = 3.0
    z: float = 8.0
    yaw_deg: float = 180.0


def _axis_pressed(window, key_pos, key_neg):
    pos = 1.0 if glfw.get_key(window, key_pos) == glfw.PRESS else 0.0
    neg = 1.0 if glfw.get_key(window, key_neg) == glfw.PRESS else 0.0
    return pos - neg


def _length2(x, z):
    return x * x + z * z


def point_hits_circle(px, pz, cx, cz, radius):
    return _length2(px - cx, pz - cz) < radius * radius


def point_hits_any_circle(px, pz, circles):
    for cx, cz, radius in circles:
        if point_hits_circle(px, pz, cx, cz, radius):
            return True
    return False


def _segment_hits_circle(x0, z0, x1, z1, cx, cz, radius):
    dx = x1 - x0
    dz = z1 - z0
    seg_len2 = dx * dx + dz * dz
    if seg_len2 <= 1e-8:
        return point_hits_circle(x0, z0, cx, cz, radius)
    t = ((cx - x0) * dx + (cz - z0) * dz) / seg_len2
    t = max(0.0, min(1.0, t))
    hx = x0 + t * dx
    hz = z0 + t * dz
    return point_hits_circle(hx, hz, cx, cz, radius)


def segment_hits_any_circle(x0, z0, x1, z1, circles):
    for cx, cz, radius in circles:
        if _segment_hits_circle(x0, z0, x1, z1, cx, cz, radius):
            return True
    return False


def update_pedestrian_from_input(window, dt, state: PedestrianState, cfg: PedestrianConfig, blocked_circles):
    key_shift_l = glfw.get_key(window, glfw.KEY_LEFT_SHIFT)
    key_shift_r = glfw.get_key(window, glfw.KEY_RIGHT_SHIFT)
    sprint = (key_shift_l == glfw.PRESS) or (key_shift_r == glfw.PRESS)
    move_speed = cfg.move_units_per_sec * (cfg.sprint_mult if sprint else 1.0)

    move_axis = _axis_pressed(window, glfw.KEY_UP, glfw.KEY_DOWN)
    turn_axis = _axis_pressed(window, glfw.KEY_RIGHT, glfw.KEY_LEFT)

    if abs(turn_axis) > 1e-6:
        state.yaw_deg += turn_axis * 150.0 * dt

    if abs(move_axis) <= 1e-6:
        return

    step_count = max(1, int(math.ceil(move_speed * dt / 0.18)))
    step_dt = dt / float(step_count)
    for _ in range(step_count):
        nx = state.x + math.sin(math.radians(state.yaw_deg)) * move_axis * move_speed * step_dt
        nz = state.z + math.cos(math.radians(state.yaw_deg)) * move_axis * move_speed * step_dt

        if _length2(nx, nz) > cfg.move_radius_limit * cfg.move_radius_limit:
            break

        if segment_hits_any_circle(state.x, state.z, nx, nz, blocked_circles):
            break

        state.x = nx
        state.z = nz


def draw_pedestrian(state: PedestrianState, ground_y=-1.0):
    glPushMatrix()
    glTranslatef(state.x, ground_y, state.z)
    glRotatef(state.yaw_deg, 0.0, 1.0, 0.0)

    glDisable(GL_TEXTURE_2D)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.05, 0.05, 0.05, 1.0))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 6.0)

    q = gluNewQuadric()
    try:
        glColor3f(0.14, 0.16, 0.22)
        glPushMatrix()
        glTranslatef(0.0, 1.2, 0.0)
        glScalef(0.42, 0.7, 0.28)
        glut_solid_unit_cube()
        glPopMatrix()

        glColor3f(0.80, 0.70, 0.58)
        glPushMatrix()
        glTranslatef(0.0, 2.0, 0.0)
        gluSphere(q, 0.24, 14, 12)
        glPopMatrix()

        glColor3f(0.10, 0.10, 0.12)
        for leg_x in (-0.14, 0.14):
            glPushMatrix()
            glTranslatef(leg_x, 0.45, 0.0)
            glRotatef(-90.0, 1.0, 0.0, 0.0)
            gluCylinder(q, 0.08, 0.08, 0.65, 10, 1)
            glPopMatrix()
    finally:
        gluDeleteQuadric(q)
        glColor3f(1.0, 1.0, 1.0)
        glPopMatrix()


def glut_solid_unit_cube():
    glBegin(GL_QUADS)
    glNormal3f(0.0, 0.0, 1.0)
    glVertex3f(-0.5, -0.5, 0.5)
    glVertex3f(0.5, -0.5, 0.5)
    glVertex3f(0.5, 0.5, 0.5)
    glVertex3f(-0.5, 0.5, 0.5)

    glNormal3f(0.0, 0.0, -1.0)
    glVertex3f(0.5, -0.5, -0.5)
    glVertex3f(-0.5, -0.5, -0.5)
    glVertex3f(-0.5, 0.5, -0.5)
    glVertex3f(0.5, 0.5, -0.5)

    glNormal3f(1.0, 0.0, 0.0)
    glVertex3f(0.5, -0.5, 0.5)
    glVertex3f(0.5, -0.5, -0.5)
    glVertex3f(0.5, 0.5, -0.5)
    glVertex3f(0.5, 0.5, 0.5)

    glNormal3f(-1.0, 0.0, 0.0)
    glVertex3f(-0.5, -0.5, -0.5)
    glVertex3f(-0.5, -0.5, 0.5)
    glVertex3f(-0.5, 0.5, 0.5)
    glVertex3f(-0.5, 0.5, -0.5)

    glNormal3f(0.0, 1.0, 0.0)
    glVertex3f(-0.5, 0.5, 0.5)
    glVertex3f(0.5, 0.5, 0.5)
    glVertex3f(0.5, 0.5, -0.5)
    glVertex3f(-0.5, 0.5, -0.5)

    glNormal3f(0.0, -1.0, 0.0)
    glVertex3f(-0.5, -0.5, -0.5)
    glVertex3f(0.5, -0.5, -0.5)
    glVertex3f(0.5, -0.5, 0.5)
    glVertex3f(-0.5, -0.5, 0.5)
    glEnd()
