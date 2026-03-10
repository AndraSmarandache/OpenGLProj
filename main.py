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
    
def terrain_height(x, z): 
    """
    Creates terrain by Gaussian Hills and layeres noise. The Gaussian Hills
    are created using Bell's Curve: A * e^(-(distance^2/spread))
    We also use procedural noise for bumpy, natural textures, with pattern:
    amplitude * sin(x * frequency) * cos(x * frequency)
    Notice we also use offsets to 'scramble' the waves so they look more natural
    """
    hill1 = 2.2 * math.exp(-((x - 1.5) ** 2 + (z + 5) ** 2) / 8.0) # hill centered at x = 1.5, z = -5, peak height of 2.2, spread of 8
    hill2 = 1.8 * math.exp(-((x + 2) ** 2 + (z + 2) ** 2) / 6.0)
    hill3 = 1.2 * math.exp(-((x - 2.5) ** 2 + (z + 7) ** 2) / 10.0)
    
    noise1 = 0.5 * math.sin(x * 0.4) * math.cos(z * 0.4) # base noise - general unevenness
    noise2 = 0.3 * math.sin(x * 0.9 + 1.3) * math.cos(z * 0.85 + 0.7) # medium noise - small mounds and dips
    noise3 = 0.2 * math.sin(2.1 * x + 2) * math.cos(1.6 * z + 1) # high noise - rougher texture
    
    return max(0.0, hill1 + hill2 + hill3 + noise1 + noise2 + noise3 + 0.6) # adds hills and noise woth an offset to 'lift' the terrain; if sum is negative it keeps the ground flat (returns 0)

def _relief_normal(x, z, step, h_func):
    """
    Calculates the surface normal at point (x,z) from finite differences (neighbors) so lighting looks correct on the relief
    OpenGL uses (nx ny, nz) values to calculate shadows; if normal points towards the light source, the texture looks brighter, and vice-versa
    """
    dx, dz = step * 0.5, step * 0.5 # tiny offsets with which to sample the neighboring heights
   
    hx0 = h_func(x - dx, z) # left neighbor
    hx1 = h_func(x + dx, z) # right neighbor
    hz0 = h_func(x, z - dz) # front neighbor
    hz1 = h_func(x, z + dz) # back neighbor
   
    tx = (hx1 - hx0) / (2 * dx) # slope (gardient) for x-axis
    tz = (hz1 - hz0) / (2 * dz) # gradient for z-axis
   
    nx, ny, nz = -tx, 1.0, -tz # normal vector - the normal needs to tilt to the opposite of the slope to stay perpendicular
    L = math.sqrt(nx * nx + ny * ny + nz * nz) # Pythagorean theorem to calculate the current normal arrow length
    if L > 1e-6: # safety check - avoid division by 0
        nx, ny, nz = nx/L, ny/L, nz/L # make arrow of length 1 (brightness is calculated by the dot product of the normal vector and light vector - they have be of length 1 so the result is just cos(angle))
    return (nx, ny, nz)

def draw_relief(texture_id):
    glColor3f(1.0, 1.0, 1.0)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    n_x, n_z = 36, 40 # how many squares (divisions) to make up the relief
    x_min, x_max, z_min, z_max = -5.0, 5.0, -10.0, 0.0 # surface space for the relief
    # steps necessary to cover the relief surface
    step_x = (x_max - x_min) / n_x # width
    step_z = (z_max - z_min) / n_z # length

    for i in range(n_x): # for every width division (columns)
        x = x_min + i * step_x # x coordinate of left edge of the div
        x2 = x_min + (i + 1) * step_x # x coordinate of right edge of the div
        glBegin(GL_TRIANGLE_STRIP) # start a strip of triangles to connect x and x2
        
        for j in range(n_z + 1): # for every length division (rows)
            z = z_min + j * step_z # current z coordinate
            
            # height: find the y for both edges of the strip; subtract 1 to align base of hill to ground level
            y1 = -1.0 + terrain_height( x, z)
            y2 = -1.0 + terrain_height(x2, z)
            
            # lighting: calculate normal vector for correct shading
            n1 = _relief_normal(x, z, step_x, terrain_height)
            n2 = _relief_normal(x2, z, step_x, terrain_height)
            
            # texture: convert to UV coordinates (0 to 1 scale), and multiply by 2 to repeat the texture so it doesn't look stretched
            u1 = (x - x_min) / (x_max - x_min) * 2
            u2 = (x2 - x_min) / (x_max - x_min) * 2
            v = (z - z_min) / (z_max - z_min) * 2
            
            # drawing: send the normals, coords and 3D position to the GPU
            # this crates a 'zig-zag' pattern that fills the triag strip:  GL_TRIANGLE_STRIP connects the last 2 points so the new ones, creating 2 triangles
            """
            [l0] ---- [r0]
            | \\  trig2 |
            |    \\     |
            | trig1 \\  |
            [l1] ---- [r1]
            """
            glNormal3f(*n1); glTexCoord2f(u1, v); glVertex3f(x, y1, z) # left point
            glNormal3f(*n2); glTexCoord2f(u2, v); glVertex3f(x2, y2, z) # right point
        glEnd() # finish the current column strip
    glDisable(GL_TEXTURE_2D) # turn off texturing to not accidentally affect other objects 

def main():
    if not glfw.init(): # initialize GLFW library
        return

    # creates 1200 x 800 px window
    window = glfw.create_window(1200, 800, "OpenGL Project : Task P1", None, None)
    if not window:
        glfw.terminate()
        return

    glfw.make_context_current(window) # all future commands are gonna affect the created window
    glEnable(GL_DEPTH_TEST) # the depth buffer stores z-values of fragments and discards them if they fail the depth testing
    glEnable(GL_NORMALIZE) # automatically fixes normals (makes them of length 1)

    # turn on the light engine
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0) # our primary 'Sun'
    glEnable(GL_COLOR_MATERIAL) # briging that tells OpenGl to use colors from our textures
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    
    glLightfv(GL_LIGHT0, GL_POSITION, (1.0, 1.2, 0.8, 0.0)) # directional light from top-left (sun-like)
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.25, 0.25, 0.28, 1.0)) # ambient (the 'shadow' light): prevents unlit areas from being pitch black
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.85, 0.85, 0.82, 1.0)) # diffuse (the 'sunlight' color): 0.85 is a slightly warm white

    grass_tex = load_texture("grass.jpg")
    sky_tex = load_texture("sky.jpg")

    while not glfw.window_should_close(window):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT) # we need to clear the buffers or they will retain values from last frame
        
        # lens setting
        glMatrixMode(GL_PROJECTION) # applies matrix operations to the projection matrix stack
        glLoadIdentity() # replaces current marix with identity matrix
        gluPerspective(45, (1200/800), 0.1, 100.0)
        
        # camera position setting
        glMatrixMode(GL_MODELVIEW) # applies matrix operations to the modelview matrix stack
        glLoadIdentity()
        glTranslatef(0, -2, -15) # moves the frame up by 2 units, and back by 15
        glRotatef(5, 1, 0, 0) # rotates on x axis so we can see the ground better

        glDepthMask(GL_FALSE) # draw skybox first without writing depth (avoids z-fight at horizon)
        draw_skybox(sky_tex) # draw the skybox first so it stays 'behind'
        glDepthMask(GL_TRUE) # enable depth buffer for writing so that object can correctly overlap

        draw_ground(grass_tex)
        draw_relief(grass_tex)

        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()

if __name__ == "__main__":
    main()