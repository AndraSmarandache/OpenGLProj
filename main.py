"""Night outdoor scene with GLFW, fixed pipeline, Pine.glb trees, and procedural fill"""

import glfw
import os
import math
from OpenGL.GL import *
from OpenGL.GLU import *
from textures import load_texture, load_texture_from_pil
from model_obj import normalize_scene_mesh, load_glb_scene_mesh
from scene import draw_ground, draw_skybox, draw_circuit
from terrain import draw_relief
from static_objects import draw_static_trees, build_natural_tree_instances

_ASSET_ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(_ASSET_ROOT, "assets")

# Diffuse tints aligned with night sky and terrain
GROUND_TINT = (0.62, 0.62, 0.68)
ROAD_TINT = (0.68, 0.68, 0.72)
TREE_MESH_TINT = (0.37, 0.39, 0.46)
# Mesh height after normalization (world units)
TREE_MESH_HEIGHT = 6.5

cam_x, cam_z = 0.0, -15.0
cam_angle_y = 0.0
cam_angle_x = 5.0
# Camera speed in world units and degrees per second (delta time)
CAM_MOVE_UNITS_PER_SEC = 16.0
CAM_TURN_DEG_PER_SEC = 150.0
CAM_PITCH_DEG_PER_SEC = 120.0


def main():
    if not glfw.init():
        return

    window = glfw.create_window(1200, 800, "OpenGL Project : Task P1", None, None)
    if not window:
        glfw.terminate()
        return

    glfw.make_context_current(window)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_NORMALIZE)

    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

    # Directional moon fill with low ambient for night
    glLightfv(GL_LIGHT0, GL_POSITION, (0.4, 1.0, 0.6, 0.0))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.08, 0.09, 0.12, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.28, 0.30, 0.38, 1.0))

    grass_tex = load_texture(os.path.join(ASSETS_DIR, "grass.jpg"))
    road_tex = load_texture(os.path.join(ASSETS_DIR, "road.jpg"))

    pine_scene = None
    pine_mat_tex = {}
    pine_glb = os.path.join(ASSETS_DIR, "Pine.glb")
    if os.path.isfile(pine_glb):
        glb_mesh, glb_pils = load_glb_scene_mesh(pine_glb)
        if glb_mesh is not None:
            pine_scene = normalize_scene_mesh(glb_mesh, target_height=TREE_MESH_HEIGHT)
            for mname, pil_img in glb_pils.items():
                tid = load_texture_from_pil(pil_img)
                if tid:
                    pine_mat_tex[mname] = int(tid)

    sky_exr = os.path.join(ASSETS_DIR, "sky.exr")
    sky_tex = load_texture(sky_exr) if os.path.exists(sky_exr) else load_texture(os.path.join(ASSETS_DIR, "sky.jpg"))

    tree_instances = build_natural_tree_instances(
        has_asset_mesh=pine_scene is not None,
        n_range=(18, 30),
    )

    global cam_x, cam_z, cam_angle_y, cam_angle_x
    last_t = glfw.get_time()
    while not glfw.window_should_close(window):
        now = glfw.get_time()
        dt = min(now - last_t, 0.1)
        last_t = now
        if dt <= 0.0:
            dt = 1.0 / 60.0

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, (1200 / 800), 0.1, 100.0)

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
        m = CAM_MOVE_UNITS_PER_SEC * dt
        tr = CAM_TURN_DEG_PER_SEC * dt
        pr = CAM_PITCH_DEG_PER_SEC * dt
        if key_w == glfw.PRESS or key_w == glfw.REPEAT:
            cam_x += math.sin(math.radians(cam_angle_y)) * m
            cam_z += math.cos(math.radians(cam_angle_y)) * m
        if key_s == glfw.PRESS or key_s == glfw.REPEAT:
            cam_x -= math.sin(math.radians(cam_angle_y)) * m
            cam_z -= math.cos(math.radians(cam_angle_y)) * m
        if key_a == glfw.PRESS or key_a == glfw.REPEAT:
            cam_angle_y += tr
        if key_d == glfw.PRESS or key_d == glfw.REPEAT:
            cam_angle_y -= tr
        if key_q == glfw.PRESS or key_q == glfw.REPEAT:
            cam_angle_x -= pr
        if key_e == glfw.PRESS or key_e == glfw.REPEAT:
            cam_angle_x += pr
        cam_angle_x = max(-85.0, min(85.0, cam_angle_x))

        ground_radius = 48.0
        cam_limit = ground_radius - 4.0
        dist = math.sqrt(cam_x * cam_x + cam_z * cam_z)
        if dist > cam_limit:
            f = cam_limit / dist
            cam_x *= f
            cam_z *= f

        glDepthMask(GL_FALSE)
        draw_skybox(sky_tex)
        glDepthMask(GL_TRUE)

        draw_ground(grass_tex, tint=GROUND_TINT)
        draw_relief(grass_tex, -22.0, 22.0, -22.0, 22.0, tint=GROUND_TINT)
        draw_circuit(road_tex, rx_inner=34.0, rz_inner=30.0, road_width=4.0, tint=ROAD_TINT)
        draw_static_trees(
            ground_y=-1.0,
            tree_instances=tree_instances,
            scene_mesh=pine_scene,
            material_to_texid=pine_mat_tex if pine_scene else None,
            obj_tint=TREE_MESH_TINT,
        )

        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()


if __name__ == "__main__":
    main()
