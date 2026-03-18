import glfw
import os
import math
from OpenGL.GL import *
from OpenGL.GLU import *
from textures import load_texture
from scene import draw_ground, draw_skybox
from terrain import draw_relief

ASSETS_DIR = "assets"

# camera state (position and rotation) so we can move around the scene
cam_x, cam_z = 0.0, -15.0
cam_angle_y = 0.0
cam_angle_x = 5.0
move_speed = 0.25
turn_speed = 2.5

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

    grass_tex = load_texture(os.path.join(ASSETS_DIR, "grass.jpg"))
    sky_exr = os.path.join(ASSETS_DIR, "sky.exr")
    sky_tex = load_texture(sky_exr) if os.path.exists(sky_exr) else load_texture(os.path.join(ASSETS_DIR, "sky.jpg"))

    global cam_x, cam_z, cam_angle_y
    while not glfw.window_should_close(window):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT) # we need to clear the buffers or they will retain values from last frame
        
        # lens setting
        glMatrixMode(GL_PROJECTION) # applies matrix operations to the projection matrix stack
        glLoadIdentity() # replaces current marix with identity matrix
        gluPerspective(45, (1200/800), 0.1, 100.0)
        
        # camera position and rotation (W/S move, A/D turn; frame moves the scene opposite to camera)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslatef(0, -2, 0)
        glRotatef(cam_angle_x, 1, 0, 0)
        glRotatef(cam_angle_y, 0, 1, 0)
        glTranslatef(-cam_x, 0, -cam_z)
        key_w = glfw.get_key(window, glfw.KEY_W)
        key_s = glfw.get_key(window, glfw.KEY_S)
        key_a = glfw.get_key(window, glfw.KEY_A)
        key_d = glfw.get_key(window, glfw.KEY_D)
        # use both PRESS and REPEAT so holding a key keeps moving/turning every frame
        if key_w == glfw.PRESS or key_w == glfw.REPEAT:
            cam_x += math.sin(math.radians(cam_angle_y)) * move_speed
            cam_z += math.cos(math.radians(cam_angle_y)) * move_speed
        if key_s == glfw.PRESS or key_s == glfw.REPEAT:
            cam_x -= math.sin(math.radians(cam_angle_y)) * move_speed
            cam_z -= math.cos(math.radians(cam_angle_y)) * move_speed
        if key_a == glfw.PRESS or key_a == glfw.REPEAT:
            cam_angle_y += turn_speed
        if key_d == glfw.PRESS or key_d == glfw.REPEAT:
            cam_angle_y -= turn_speed

        glDepthMask(GL_FALSE) # draw skybox first without writing depth (avoids z-fight at horizon)
        draw_skybox(sky_tex) # draw the skybox first so it stays 'behind'
        glDepthMask(GL_TRUE) # enable depth buffer for writing so that object can correctly overlap

        draw_ground(grass_tex)
        draw_relief(grass_tex, -7.0, 7.0, -5.0, 5.0)

        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()

if __name__ == "__main__":
    main()
