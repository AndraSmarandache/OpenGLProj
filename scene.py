import math
from OpenGL.GL import *

# circular ground: no visible corners; mesh is a disk so the edge fades into fog at the horizon (industry standard)
# radius chosen to sit inside the skybox sphere; texture tiles using world x,z for natural repetition
def draw_ground(texture_id, radius=48.0, segments=64, tint=(1.0, 1.0, 1.0)):
    glColor3f(*tint)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glNormal3f(0, 1, 0)
    # tile scale: more repeats = less stretched (e.g. 1/5 gives ~10 repeats over radius so grass/fronds look natural)
    uv_scale = 1.0 / 5.0
    glBegin(GL_TRIANGLE_FAN)
    glTexCoord2f(0.5, 0.5)  # center of first texel for a smooth look at origin
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

# sphere skybox: one texture wrapped around the inside of a sphere so there are no seams when you rotate
# texture is equirectangular (360 degrees panorama); u = horizontal angle (theta), v = vertical (phi from top)
# lighting is disabled so the sky is always full brightness (otherwise the top of the sphere looks like a black cap)
def draw_skybox(texture_id):
    glDisable(GL_LIGHTING)
    glColor3f(1.0, 1.0, 1.0)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glFrontFace(GL_CW)  # we are inside the sphere so we want to see the inner face (winding is CW from inside)
    radius = 50.0
    n_lat, n_lon = 24, 48  # latitude and longitude segments for the sphere mesh
    for j in range(n_lat):
        phi0 = math.pi * (j / n_lat)       # polar angle from top (0) to bottom (pi)
        phi1 = math.pi * ((j + 1) / n_lat)
        glBegin(GL_QUAD_STRIP)
        for i in range(n_lon + 1):
            theta = 2 * math.pi * i / n_lon  # azimuth angle around the sphere (0 to 2*pi)
            for phi in (phi0, phi1):
                x = radius * math.sin(phi) * math.cos(theta)
                y = radius * math.cos(phi)
                z = radius * math.sin(phi) * math.sin(theta)
                u = theta / (2 * math.pi)    # u runs 0..1 around the horizon for equirectangular
                v = 1.0 - phi / math.pi     # v runs 0 (top) to 1 (bottom)
                glTexCoord2f(u, v)
                glVertex3f(x, y, z)
        glEnd()
    glFrontFace(GL_CCW)  # restore default winding for the rest of the scene
    glDisable(GL_TEXTURE_2D)
    glEnable(GL_LIGHTING)
