import math
import random
from dataclasses import dataclass

from OpenGL.GL import *
from OpenGL.GLU import *


@dataclass
class CarState:
    phase: float = 0.0
    speed: float = 0.36
    x: float = 0.0
    z: float = 0.0
    yaw_deg: float = 0.0


@dataclass
class RandomWalker:
    x: float
    z: float
    yaw_deg: float
    speed: float
    target_x: float
    target_z: float
    body_tint: tuple
    leg_tint: tuple
    scale: float


def _length2(x, z):
    return x * x + z * z


def _point_hits_any_circle(px, pz, circles):
    for cx, cz, radius in circles:
        if _length2(px - cx, pz - cz) <= radius * radius:
            return True
    return False


def _segment_hits_circle(x0, z0, x1, z1, cx, cz, radius):
    dx = x1 - x0
    dz = z1 - z0
    seg_len2 = dx * dx + dz * dz
    if seg_len2 <= 1e-8:
        return _length2(x0 - cx, z0 - cz) <= radius * radius
    t = ((cx - x0) * dx + (cz - z0) * dz) / seg_len2
    t = max(0.0, min(1.0, t))
    hx = x0 + t * dx
    hz = z0 + t * dz
    return _length2(hx - cx, hz - cz) <= radius * radius


def _segment_hits_any_circle(x0, z0, x1, z1, circles):
    for cx, cz, radius in circles:
        if _segment_hits_circle(x0, z0, x1, z1, cx, cz, radius):
            return True
    return False


def init_random_walkers(count, waypoints, seed=7):
    rng = random.Random(seed)
    out = []
    if not waypoints:
        return out
    for _ in range(max(1, int(count))):
        sx, sz = waypoints[rng.randrange(len(waypoints))]
        tx, tz = waypoints[rng.randrange(len(waypoints))]
        out.append(
            RandomWalker(
                x=float(sx),
                z=float(sz),
                yaw_deg=0.0,
                speed=rng.uniform(1.35, 1.9),
                target_x=float(tx),
                target_z=float(tz),
                body_tint=(rng.uniform(0.15, 0.35), rng.uniform(0.18, 0.42), rng.uniform(0.25, 0.58)),
                leg_tint=(rng.uniform(0.06, 0.14), rng.uniform(0.06, 0.14), rng.uniform(0.08, 0.18)),
                scale=rng.uniform(0.92, 1.08),
            )
        )
    return out


def update_random_walkers(walkers, dt, waypoints, blocked_circles):
    if not walkers or not waypoints:
        return
    for w in walkers:
        dx = w.target_x - w.x
        dz = w.target_z - w.z
        dist2 = dx * dx + dz * dz
        if dist2 <= 0.45 * 0.45:
            w.target_x, w.target_z = random.choice(waypoints)
            dx = w.target_x - w.x
            dz = w.target_z - w.z
            dist2 = dx * dx + dz * dz
        if dist2 <= 1e-10:
            continue
        dist = math.sqrt(dist2)
        dir_x = dx / dist
        dir_z = dz / dist
        w.yaw_deg = math.degrees(math.atan2(dir_x, dir_z))
        step_count = max(1, int(math.ceil((w.speed * dt) / 0.14)))
        step_len = (w.speed * dt) / float(step_count)
        for _ in range(step_count):
            nx = w.x + dir_x * step_len
            nz = w.z + dir_z * step_len
            if not _segment_hits_any_circle(w.x, w.z, nx, nz, blocked_circles):
                w.x = nx
                w.z = nz
                continue
            side_x = -dir_z
            side_z = dir_x
            alt_x = w.x + side_x * step_len
            alt_z = w.z + side_z * step_len
            if not _segment_hits_any_circle(w.x, w.z, alt_x, alt_z, blocked_circles):
                w.x = alt_x
                w.z = alt_z
            break


def update_car_state(car, dt, rx=37.6, rz=33.6):
    car.phase = (car.phase + car.speed * dt) % (2.0 * math.pi)
    t = car.phase
    car.x = rx * math.cos(t)
    car.z = rz * math.sin(t)
    tx = -rx * math.sin(t)
    tz = rz * math.cos(t)
    car.yaw_deg = math.degrees(math.atan2(tx, tz))


def setup_car_headlights(light_ids):
    for lid in light_ids:
        glEnable(lid)
        glLightfv(lid, GL_AMBIENT, (0.0, 0.0, 0.0, 1.0))
        glLightfv(lid, GL_DIFFUSE, (0.75, 0.72, 0.62, 1.0))
        glLightfv(lid, GL_SPECULAR, (0.12, 0.11, 0.08, 1.0))
        glLightf(lid, GL_CONSTANT_ATTENUATION, 1.0)
        glLightf(lid, GL_LINEAR_ATTENUATION, 0.08)
        glLightf(lid, GL_QUADRATIC_ATTENUATION, 0.02)
        glLightf(lid, GL_SPOT_CUTOFF, 24.0)
        glLightf(lid, GL_SPOT_EXPONENT, 24.0)


def apply_car_headlights(light_left, light_right, car):
    yaw = math.radians(car.yaw_deg)
    fwd_x = math.sin(yaw)
    fwd_z = math.cos(yaw)
    right_x = math.cos(yaw)
    right_z = -math.sin(yaw)
    base_y = -0.58
    off_side = 0.42
    off_front = 0.9
    lx = car.x + right_x * (-off_side) + fwd_x * off_front
    lz = car.z + right_z * (-off_side) + fwd_z * off_front
    rx = car.x + right_x * off_side + fwd_x * off_front
    rz = car.z + right_z * off_side + fwd_z * off_front
    glEnable(light_left)
    glLightfv(light_left, GL_POSITION, (lx, base_y, lz, 1.0))
    glLightfv(light_left, GL_SPOT_DIRECTION, (fwd_x, -0.08, fwd_z))
    glEnable(light_right)
    glLightfv(light_right, GL_POSITION, (rx, base_y, rz, 1.0))
    glLightfv(light_right, GL_SPOT_DIRECTION, (fwd_x, -0.08, fwd_z))


def draw_car(car, ground_y=-1.0):
    glPushMatrix()
    glTranslatef(car.x, ground_y, car.z)
    glRotatef(car.yaw_deg, 0.0, 1.0, 0.0)
    glDisable(GL_TEXTURE_2D)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.16, 0.16, 0.16, 1.0))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 24.0)
    glColor3f(0.20, 0.24, 0.36)
    glPushMatrix()
    glTranslatef(0.0, 0.38, 0.0)
    glScalef(1.8, 0.42, 0.84)
    _draw_unit_box()
    glPopMatrix()
    glColor3f(0.09, 0.10, 0.14)
    glPushMatrix()
    glTranslatef(0.06, 0.62, 0.0)
    glScalef(1.0, 0.34, 0.72)
    _draw_unit_box()
    glPopMatrix()
    glColor3f(0.9, 0.88, 0.74)
    for sx in (-0.42, 0.42):
        glPushMatrix()
        glTranslatef(0.82, 0.35, sx)
        glScalef(0.08, 0.08, 0.08)
        _draw_unit_box()
        glPopMatrix()
    glColor3f(0.08, 0.08, 0.10)
    for wx, wz in ((0.55, 0.46), (0.55, -0.46), (-0.58, 0.46), (-0.58, -0.46)):
        glPushMatrix()
        glTranslatef(wx, 0.17, wz)
        q = gluNewQuadric()
        try:
            glRotatef(90.0, 0.0, 1.0, 0.0)
            gluCylinder(q, 0.17, 0.17, 0.12, 12, 1)
        finally:
            gluDeleteQuadric(q)
        glPopMatrix()
    glColor3f(1.0, 1.0, 1.0)
    glPopMatrix()


def draw_random_walker(walker, time_s, ground_y=-1.0):
    bob = 0.035 * math.sin(time_s * 7.2 + walker.x * 0.37 + walker.z * 0.41)
    leg_swing = 24.0 * math.sin(time_s * 7.2 + walker.x * 0.37)
    glPushMatrix()
    glTranslatef(walker.x, ground_y, walker.z)
    glRotatef(walker.yaw_deg, 0.0, 1.0, 0.0)
    glScalef(walker.scale, walker.scale, walker.scale)
    glDisable(GL_TEXTURE_2D)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.03, 0.03, 0.03, 1.0))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 5.0)
    glColor3f(*walker.body_tint)
    glPushMatrix()
    glTranslatef(0.0, 1.18 + bob, 0.0)
    glScalef(0.36, 0.62, 0.24)
    _draw_unit_box()
    glPopMatrix()
    glColor3f(0.74, 0.64, 0.54)
    glPushMatrix()
    glTranslatef(0.0, 1.86 + bob, 0.0)
    q = gluNewQuadric()
    try:
        gluSphere(q, 0.2, 14, 12)
    finally:
        gluDeleteQuadric(q)
    glPopMatrix()
    glColor3f(*walker.leg_tint)
    for leg_x, sign in ((-0.12, 1.0), (0.12, -1.0)):
        glPushMatrix()
        glTranslatef(leg_x, 0.54, 0.0)
        glRotatef(leg_swing * sign, 1.0, 0.0, 0.0)
        glRotatef(-90.0, 1.0, 0.0, 0.0)
        q = gluNewQuadric()
        try:
            gluCylinder(q, 0.07, 0.07, 0.66, 10, 1)
        finally:
            gluDeleteQuadric(q)
        glPopMatrix()
    glColor3f(0.1, 0.1, 0.12)
    glPushMatrix()
    glTranslatef(0.0, 2.08 + bob, 0.0)
    glScalef(0.24, 0.08, 0.24)
    _draw_unit_box()
    glPopMatrix()
    glColor3f(1.0, 1.0, 1.0)
    glPopMatrix()


def _draw_unit_box():
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
