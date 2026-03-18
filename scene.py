import math
from OpenGL.GL import *

def draw_ground(texture_id):
    glColor3f(1.0, 1.0, 1.0) # reset colors
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glNormal3f(0, 1, 0) # normal faces up for lighting
    glBegin(GL_QUADS)
    # Mapping: (0,0) is bottom-left of image, (5,5) repeats it 5 times
    glTexCoord2f(0, 5); glVertex3f(-25, -1, -25)
    glTexCoord2f(5, 5); glVertex3f( 25, -1, -25)
    glTexCoord2f(5, 0); glVertex3f( 25, -1,  25)
    glTexCoord2f(0, 0); glVertex3f(-25, -1,  25)
    glEnd()
    glDisable(GL_TEXTURE_2D)

# sphere skybox: one texture wrapped around the inside of a sphere so there are no seams when you rotate
# texture is equirectangular (360° panorama); u = horizontal angle (theta), v = vertical (phi from top)
def draw_skybox(texture_id):
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
