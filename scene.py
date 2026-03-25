"""Textured ground disk, oval road, and equirectangular sky"""

import math
from OpenGL.GL import *


def draw_ground(texture_id, radius=48.0, segments=64, tint=(1.0, 1.0, 1.0)):
    glColor3f(*tint)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glNormal3f(0, 1, 0)
    uv_scale = 1.0 / 5.0  # grass UV scale in world units
    glBegin(GL_TRIANGLE_FAN)
    glTexCoord2f(0.5, 0.5)
    glVertex3f(0, -1, 0)
    for i in range(segments + 1):
        t = 2 * math.pi * i / segments
        x = radius * math.cos(t)
        z = radius * math.sin(t)
        u = x * uv_scale
        v = z * uv_scale
        glTexCoord2f(u, v)
        glVertex3f(x, -1, z)
    glEnd()
    glDisable(GL_TEXTURE_2D)

def draw_circuit(texture_id, rx_inner, rz_inner, road_width, y=-0.985, segments=64, u_repeats=6.0, tint=(1.0, 1.0, 1.0)):
    """Textured flat ring between inner and outer ellipses"""
    rx_outer = rx_inner + road_width
    rz_outer = rz_inner + road_width
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.32, 0.32, 0.35, 1.0))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 22.0)
    if texture_id:
        glColor3f(*tint)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture_id)
    else:
        glColor3f(0.18, 0.18, 0.22)
    glNormal3f(0, 1, 0)
    glBegin(GL_QUADS)
    for i in range(segments):
        t0 = 2 * math.pi * i / segments
        t1 = 2 * math.pi * (i + 1) / segments
        x0i, z0i = rx_inner * math.cos(t0), rz_inner * math.sin(t0)
        x1i, z1i = rx_inner * math.cos(t1), rz_inner * math.sin(t1)
        x0o, z0o = rx_outer * math.cos(t0), rz_outer * math.sin(t0)
        x1o, z1o = rx_outer * math.cos(t1), rz_outer * math.sin(t1)
        u0 = (i / segments) * u_repeats
        u1 = ((i + 1) / segments) * u_repeats
        glTexCoord2f(u0, 0); glVertex3f(x0i, y, z0i)
        glTexCoord2f(u1, 0); glVertex3f(x1i, y, z1i)
        glTexCoord2f(u1, 1); glVertex3f(x1o, y, z1o)
        glTexCoord2f(u0, 1); glVertex3f(x0o, y, z0o)
    glEnd()
    if texture_id:
        glDisable(GL_TEXTURE_2D)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.0, 0.0, 0.0, 1.0))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 0.0)
    glColor3f(1.0, 1.0, 1.0)

def draw_skybox(texture_id):
    """Equirectangular sky on an inner sphere with lighting disabled"""
    glDisable(GL_LIGHTING)
    glColor3f(1.0, 1.0, 1.0)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glFrontFace(GL_CW)
    radius = 50.0
    n_lat, n_lon = 24, 48
    for j in range(n_lat):
        phi0 = math.pi * (j / n_lat)
        phi1 = math.pi * ((j + 1) / n_lat)
        glBegin(GL_QUAD_STRIP)
        for i in range(n_lon + 1):
            theta = 2 * math.pi * i / n_lon
            for phi in (phi0, phi1):
                x = radius * math.sin(phi) * math.cos(theta)
                y = radius * math.cos(phi)
                z = radius * math.sin(phi) * math.sin(theta)
                u = theta / (2 * math.pi)
                v = 1.0 - phi / math.pi
                glTexCoord2f(u, v)
                glVertex3f(x, y, z)
        glEnd()
    glFrontFace(GL_CCW)
    glDisable(GL_TEXTURE_2D)
    glEnable(GL_LIGHTING)
