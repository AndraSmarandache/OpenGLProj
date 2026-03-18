import glfw
from OpenGL.GL import *
from OpenGL.GLU import *
from textures import load_texture, load_heightmap
from scene import draw_ground, draw_skybox
from terrain import draw_relief, draw_relief_heightmap

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
    # try to load heightmap so we can show both reliefs when present
    hm = load_heightmap("heightmap.jpg")

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
        # when heightmap is present, show both – procedural left patch, heightmap right patch
        if hm is not None:
            draw_relief(grass_tex, -10.0, -1.0, -10.0, 0.0)
            draw_relief_heightmap(hm, grass_tex, 2.5, 2.0, 10.0, -10.0, 0.0)
        else:
            draw_relief(grass_tex)

        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()

if __name__ == "__main__":
    main()
