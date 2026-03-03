import glfw
from OpenGL.GL import *
from OpenGL.GLU import *
from PIL import Image
import os
import math

# helper function for loading texture
def load_texture(path):
    if not os.path.exists(path):
        print(f"Error: {path} not found!")
        return 0
    
    img = Image.open(path)
    img = img.transpose(Image.FLIP_TOP_BOTTOM) # flip for OpenGL coordinates(in OpenGl, (0, 0) is at bottom-left and we want it at top-left)
    img_data = img.convert("RGB").tobytes()
    
    tex_id = glGenTextures(1) # id number to store the new texture
    glBindTexture(GL_TEXTURE_2D, tex_id) # binds future modifications to the newly created texture
    
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR) # texture minimizing function (used when the pixel being textured maps to an area > than one texture element)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR) # texture magnification function (used when the pixel being textured maps to an area <= than one texture element)

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT) # integer part of coordinate s is ignored => repeating pattern
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT) # same for coordinate t
    
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, img.width, img.height, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data) # sends raw pixels to GPU memory
    return tex_id

def draw_ground(texture_id):
    glColor3f(1.0, 1.0, 1.0) # reset colors
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
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

    glEnd()
    glDisable(GL_TEXTURE_2D)

def draw_relief(texture_id):
    glColor3f(1.0, 1.0, 1.0) 
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    
    step = 0.5 # grid resolution
    height_multiplier = 3 # height of the peaks
    
    # relief area is x from -5 to 5, and z from -10 to 0
    x_range = [i * step for i in range(int(-5/step), int(5/step))]
    z_range = [j * step for j in range(int(-10/step), int(0/step))]

    for x in x_range:
        glBegin(GL_TRIANGLE_STRIP)
        for z in z_range:
            # wave pattern is created by sin and cos
            y1 = math.sin(x * 0.5) * math.cos(z * 0.5) * height_multiplier
            y2 = math.sin((x + step) * 0.5) * math.cos(z * 0.5) * height_multiplier
            
            # texture coordinates; the division controls how many times the grass texture tiles
            u1, v1 = x / 5.0, z / 5.0
            u2, v2 = (x + step) / 5.0, z / 5.0

            glTexCoord2f(u1, v1); glVertex3f(x, y1 - 0.5, z)
            glTexCoord2f(u2, v2); glVertex3f(x + step, y2 - 0.5, z)
        glEnd()
    
    glDisable(GL_TEXTURE_2D)

def main():
    if not glfw.init():
        return

    window = glfw.create_window(1200, 800, "OpenGL Project : Task P1", None, None)
    if not window:
        glfw.terminate()
        return

    glfw.make_context_current(window)
    glEnable(GL_DEPTH_TEST) # the depth buffer stores z-values of fragments and discards them if they fail the depth testing

    grass_tex = load_texture("grass.jpg")
    sky_tex = load_texture("sky.jpg")
    
    while not glfw.window_should_close(window):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT) # we need to clear the buffers or they will retain values from last frame
        
        glMatrixMode(GL_PROJECTION) # applies matrix operations to the projection matrix stack
        glLoadIdentity() # replaces current marix with identity matrix
        gluPerspective(45, (1200/800), 0.1, 100.0)
        
        glMatrixMode(GL_MODELVIEW) # applies matrix operations to the modelview matrix stack
        glLoadIdentity()
        glTranslatef(0, -2, -15) # moves the frame up by 2 units, and back by 15
        glRotatef(5, 1, 0, 0) # rotates on x axis so we can see the ground better

        draw_ground(grass_tex)
        draw_relief(grass_tex)
        draw_skybox(sky_tex)

        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()

if __name__ == "__main__":
    main()