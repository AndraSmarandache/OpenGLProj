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
    
def draw_skybox(texture_id):
    glColor3f(1.0, 1.0, 1.0)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glBegin(GL_QUADS)

    # image is used one time (does not repeat like grass did) 
    # front wall
    glTexCoord2f(0, 0); glVertex3f(-25, -1, -25)
    glTexCoord2f(1, 0); glVertex3f( 25, -1, -25)
    glTexCoord2f(1, 1); glVertex3f( 25, 20, -25)
    glTexCoord2f(0, 1); glVertex3f(-25, 20, -25)

    # left wall
    glTexCoord2f(0, 0); glVertex3f(-25, -1,  25)
    glTexCoord2f(1, 0); glVertex3f(-25, -1, -25)
    glTexCoord2f(1, 1); glVertex3f(-25, 20, -25)
    glTexCoord2f(0, 1); glVertex3f(-25, 20,  25)
    
    # right wall
    glTexCoord2f(0, 0); glVertex3f( 25, -1, -25)
    glTexCoord2f(1, 0); glVertex3f( 25, -1,  25)
    glTexCoord2f(1, 1); glVertex3f( 25, 20,  25)
    glTexCoord2f(0, 1); glVertex3f( 25, 20, -25)

    # back wall
    glTexCoord2f(0, 0); glVertex3f( 25, -1,  25)
    glTexCoord2f(1, 0); glVertex3f(-25, -1,  25)
    glTexCoord2f(1, 1); glVertex3f(-25, 20,  25)
    glTexCoord2f(0, 1); glVertex3f( 25, 20,  25)

    # top (ceiling)
    glTexCoord2f(0, 0); glVertex3f(-25, 20, -25)
    glTexCoord2f(1, 0); glVertex3f( 25, 20, -25)
    glTexCoord2f(1, 1); glVertex3f( 25, 20,  25)
    glTexCoord2f(0, 1); glVertex3f(-25, 20,  25)

    glEnd()
    glDisable(GL_TEXTURE_2D)
