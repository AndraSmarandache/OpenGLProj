import glfw
import os
import math
from OpenGL.GL import *
from OpenGL.GLU import *
from textures import load_texture
from scene import draw_ground, draw_skybox, draw_circuit
from terrain import draw_relief

ASSETS_DIR = "assets"

# tint so ground and road matches night sky
GROUND_TINT = (0.62, 0.62, 0.68)
ROAD_TINT = (0.68, 0.68, 0.72)

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
    
    glLightfv(GL_LIGHT0, GL_POSITION, (0.4, 1.0, 0.6, 0.0))  # directional: soft moon-style from above-front
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.08, 0.09, 0.12, 1.0))  # darker night fill light
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.28, 0.30, 0.38, 1.0))  # dimmer moon-like key so terrain reads as night

    grass_tex = load_texture(os.path.join(ASSETS_DIR, "grass.jpg"))
    road_tex = load_texture(os.path.join(ASSETS_DIR, "road.jpg"))
    sky_exr = os.path.join(ASSETS_DIR, "sky.exr")
    sky_tex = load_texture(sky_exr) if os.path.exists(sky_exr) else load_texture(os.path.join(ASSETS_DIR, "sky.jpg"))

    global cam_x, cam_z, cam_angle_y, cam_angle_x
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
        key_q = glfw.get_key(window, glfw.KEY_Q)
        key_e = glfw.get_key(window, glfw.KEY_E)
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
        if key_q == glfw.PRESS or key_q == glfw.REPEAT:
            cam_angle_x -= turn_speed  # look up
        if key_e == glfw.PRESS or key_e == glfw.REPEAT:
            cam_angle_x += turn_speed  # look down
        cam_angle_x = max(-85.0, min(85.0, cam_angle_x))  # clamp so we don't flip over
        # keep camera inside the ground circle so we never see past the disk (weird view)
        ground_radius = 48.0
        cam_limit = ground_radius - 4.0
        dist = math.sqrt(cam_x * cam_x + cam_z * cam_z)
        if dist > cam_limit:
            f = cam_limit / dist
            cam_x *= f
            cam_z *= f

        glDepthMask(GL_FALSE) # draw skybox first without writing depth (avoids z-fight at horizon)
        draw_skybox(sky_tex) # draw the skybox first so it stays 'behind'
        glDepthMask(GL_TRUE) # enable depth buffer for writing so that object can correctly overlap

        draw_ground(grass_tex, tint=GROUND_TINT)
        # relief covers most of the disk so the mini world is hills to the horizon, not a flat circle
        draw_relief(grass_tex, -22.0, 22.0, -22.0, 22.0, tint=GROUND_TINT)
        # flat oval trail on grass only (inner ellipse outside relief square)
        draw_circuit(road_tex, rx_inner=34.0, rz_inner=30.0, road_width=4.0, tint=ROAD_TINT)

        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()

if __name__ == "__main__":
    main()
