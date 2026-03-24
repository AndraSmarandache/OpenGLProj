"""Procedural relief and optional heightmap mesh"""

import math
from OpenGL.GL import *
from textures import sample_heightmap

def terrain_height(x, z):
    """Non-negative procedural height from Gaussians and sine layers in canonical xz"""
    hill1 = 2.2 * math.exp(-((x - 1.5) ** 2 + (z + 5) ** 2) / 8.0)
    hill2 = 1.8 * math.exp(-((x + 2) ** 2 + (z + 2) ** 2) / 6.0)
    hill3 = 1.2 * math.exp(-((x - 2.5) ** 2 + (z + 7) ** 2) / 10.0)
    noise1 = 0.5 * math.sin(x * 0.4) * math.cos(z * 0.4)
    noise2 = 0.3 * math.sin(x * 0.9 + 1.3) * math.cos(z * 0.85 + 0.7)
    noise3 = 0.2 * math.sin(2.1 * x + 2) * math.cos(1.6 * z + 1)
    return max(0.0, hill1 + hill2 + hill3 + noise1 + noise2 + noise3 + 0.6)

def _relief_normal(x, z, step, h_func):
    """Unit normal from central differences on h_func(x, z)"""
    dx, dz = step * 0.5, step * 0.5
    hx0 = h_func(x - dx, z)
    hx1 = h_func(x + dx, z)
    hz0 = h_func(x, z - dz)
    hz1 = h_func(x, z + dz)
    tx = (hx1 - hx0) / (2 * dx)
    tz = (hz1 - hz0) / (2 * dz)
    nx, ny, nz = -tx, 1.0, -tz
    L = math.sqrt(nx * nx + ny * ny + nz * nz)
    if L > 1e-6:
        nx, ny, nz = nx / L, ny / L, nz / L
    return (nx, ny, nz)

def draw_relief(texture_id, x_min=-5.0, x_max=5.0, z_min=-10.0, z_max=0.0, inner_ellipse_rx=None, inner_ellipse_rz=None, edge_fade=10.0, tint=(1.0, 1.0, 1.0)):
    # Smoothstep height fade using edge_fade at patch boundary
    def height_mapped(x, z):
        x_can = -5.0 + (x - x_min) / (x_max - x_min) * 10.0
        z_can = -10.0 + (z - z_min) / (z_max - z_min) * 10.0
        h = terrain_height(x_can, z_can)
        if inner_ellipse_rx is not None and inner_ellipse_rz is not None:
            if (x / inner_ellipse_rx) ** 2 + (z / inner_ellipse_rz) ** 2 > 1:
                h = 0.0
        # Smoothstep at patch edges to blend into flat ground
        dist_x = min(x - x_min, x_max - x)
        dist_z = min(z - z_min, z_max - z)
        t_x = min(1.0, dist_x / edge_fade) if edge_fade > 0 else 1.0
        t_z = min(1.0, dist_z / edge_fade) if edge_fade > 0 else 1.0
        t_x = t_x * t_x * (3.0 - 2.0 * t_x)
        t_z = t_z * t_z * (3.0 - 2.0 * t_z)
        return h * t_x * t_z
    glColor3f(*tint)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    n_x, n_z = 36, 40
    step_x = (x_max - x_min) / n_x
    step_z = (z_max - z_min) / n_z

    for i in range(n_x):
        x = x_min + i * step_x
        x2 = x_min + (i + 1) * step_x
        glBegin(GL_TRIANGLE_STRIP)

        for j in range(n_z + 1):
            z = z_min + j * step_z
            y1 = -1.0 + height_mapped(x, z)
            y2 = -1.0 + height_mapped(x2, z)
            n1 = _relief_normal(x, z, step_x, height_mapped)
            n2 = _relief_normal(x2, z, step_x, height_mapped)
            uv_repeats = 16.0
            u1 = (x - x_min) / (x_max - x_min) * uv_repeats
            u2 = (x2 - x_min) / (x_max - x_min) * uv_repeats
            v = (z - z_min) / (z_max - z_min) * uv_repeats
            glNormal3f(*n1)
            glTexCoord2f(u1, v)
            glVertex3f(x, y1, z)
            glNormal3f(*n2)
            glTexCoord2f(u2, v)
            glVertex3f(x2, y2, z)
        glEnd()

    glDisable(GL_TEXTURE_2D)

def draw_relief_heightmap(hm_data, texture_id, height_scale=3.0, x_min=-5.0, x_max=5.0, z_min=-10.0, z_max=0.0, outer_ellipse_rx=None, outer_ellipse_rz=None):
    """Heightmap relief using the same strip layout as draw_relief"""
    hm_width, hm_height, hm_pixels = hm_data
    n_x, n_z = 36, 40
    step_x = (x_max - x_min) / n_x
    step_z = (z_max - z_min) / n_z

    def height_at(x, z):
        if outer_ellipse_rx is not None and outer_ellipse_rz is not None:
            if (x / outer_ellipse_rx) ** 2 + (z / outer_ellipse_rz) ** 2 <= 1:
                return 0.0
        u = (x - x_min) / (x_max - x_min)
        v = (z - z_min) / (z_max - z_min)
        return height_scale * sample_heightmap(hm_width, hm_height, hm_pixels, u, v)

    glColor3f(1.0, 1.0, 1.0)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    for i in range(n_x):
        x = x_min + i * step_x
        x2 = x_min + (i + 1) * step_x
        glBegin(GL_TRIANGLE_STRIP)
        
        for j in range(n_z + 1):
            z = z_min + j * step_z
            
            y1 = -1.0 + height_at(x, z)
            y2 = -1.0 + height_at(x2, z)
            
            n1 = _relief_normal(x, z, step_x, height_at)
            n2 = _relief_normal(x2, z, step_x, height_at)
            
            uv_repeats = 16.0
            u1 = (x - x_min) / (x_max - x_min) * uv_repeats
            u2 = (x2 - x_min) / (x_max - x_min) * uv_repeats
            v = (z - z_min) / (z_max - z_min) * uv_repeats
            
            glNormal3f(*n1); glTexCoord2f(u1, v); glVertex3f(x, y1, z)
            glNormal3f(*n2); glTexCoord2f(u2, v); glVertex3f(x2, y2, z)
        glEnd()
    glDisable(GL_TEXTURE_2D)
