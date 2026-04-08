import math
from OpenGL.GL import *
from OpenGL.GLU import *

_lamp_glow_quadric = None


def draw_lamp_glow_orb(x, y, z, radius=0.23):
    global _lamp_glow_quadric
    if _lamp_glow_quadric is None:
        _lamp_glow_quadric = gluNewQuadric()
        gluQuadricNormals(_lamp_glow_quadric, GLU_SMOOTH)

    glPushMatrix()
    glTranslatef(x, y, z)
    glDisable(GL_LIGHTING)
    glDisable(GL_TEXTURE_2D)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)

    halo_r = float(radius) * 2.1
    glColor4f(1.0, 0.86, 0.55, 0.22)
    glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (1.0, 0.78, 0.34, 1.0))
    gluSphere(_lamp_glow_quadric, halo_r, 18, 14)

    glColor4f(1.0, 0.86, 0.55, 0.95)
    gluSphere(_lamp_glow_quadric, float(radius), 14, 10)

    glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.0, 0.0, 0.0, 1.0))
    glDisable(GL_BLEND)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glColor3f(1.0, 1.0, 1.0)
    glPopMatrix()


def draw_lamp_beam_cone(x, y_apex, z, y_end, visual_half_angle_deg=13.0, alpha_apex=0.22, radius_at_end=None):
    # Fake narrow beam half angle in degrees not the same as GL spot or shadow cone
    theta = math.radians(float(visual_half_angle_deg))
    height = abs(y_apex - y_end)
    if radius_at_end is None:
        radius_at_end = max(0.2, height * math.tan(theta)) * 1.18

    segs = 28
    glPushMatrix()
    glTranslatef(x, y_apex, z)
    glDisable(GL_LIGHTING)
    glDisable(GL_TEXTURE_2D)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)

    color = (1.0, 0.86, 0.55)
    y_base = y_end - y_apex
    glBegin(GL_TRIANGLES)
    for i in range(segs):
        a0 = (2.0 * math.pi * i) / segs
        a1 = (2.0 * math.pi * (i + 1)) / segs
        x0 = radius_at_end * math.cos(a0)
        z0 = radius_at_end * math.sin(a0)
        x1 = radius_at_end * math.cos(a1)
        z1 = radius_at_end * math.sin(a1)

        glColor4f(color[0], color[1], color[2], 0.0)
        glVertex3f(x0, y_base, z0)
        glColor4f(color[0], color[1], color[2], float(alpha_apex))
        glVertex3f(0.0, 0.0, 0.0)
        glColor4f(color[0], color[1], color[2], 0.0)
        glVertex3f(x1, y_base, z1)
    glEnd()

    glDisable(GL_BLEND)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glPopMatrix()


def find_material_anchor_local(mesh, material_name):
    if mesh is None:
        return None
    tris = mesh.groups.get(material_name)
    if not tris:
        return None
    pts = []
    for tri in tris:
        for vi, _vti, _vni in tri:
            if vi is not None and 0 <= vi < len(mesh.vertices):
                pts.append(mesh.vertices[vi])
    if not pts:
        return None
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    cz = sum(p[2] for p in pts) / len(pts)
    return (cx, cy, cz)
