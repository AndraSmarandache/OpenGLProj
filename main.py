"""Night outdoor scene with modular camera, lighting, and benches"""

import math
import os

import glfw
from OpenGL.GL import *
from OpenGL.GLU import *

from bench_system import compute_bench_positions, load_bench_scene
from camera_controller import CameraConfig, CameraState, apply_camera_view, update_camera_from_input
from lamp_effects import draw_lamp_beam_cone, draw_lamp_glow_orb, find_material_anchor_local
from lighting_system import apply_active_lights, enforce_night_lighting_state, select_active_lamp_indices, setup_lamp_lights, setup_night_lighting
from model_obj import draw_scene_mesh, load_glb_scene_mesh, load_scene_mesh, normalize_scene_mesh
from moving_objects import (
    CarState,
    apply_car_headlights,
    draw_car,
    draw_random_walker,
    init_random_walkers,
    setup_car_headlights,
    update_car_state,
    update_random_walkers,
)
from pedestrian_system import PedestrianConfig, PedestrianState, draw_pedestrian, update_pedestrian_from_input
from scene import draw_circuit, draw_ground, draw_skybox
from static_objects import TREE_SITES, draw_static_trees
from terrain import draw_relief
from textures import load_texture, load_texture_from_pil

_ASSET_ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(_ASSET_ROOT, "assets")

GROUND_TINT = (0.36, 0.40, 0.46)
ROAD_TINT = (0.40, 0.42, 0.49)
TREE_MESH_TINT = (0.26, 0.30, 0.38)
LAMP_POST_TINT = (0.50, 0.53, 0.60)

TREE_MESH_HEIGHT = 6.5
LAMP_POST_HEIGHT = 8.2
PEDESTRIAN_HEIGHT = 2.05
ENABLE_PEDESTRIAN_GLB = False

LAMP_LIGHTS_MAX = 4
LAMP_LIGHT_HEIGHT = 6.6
LAMP_LIGHT_DIFFUSE_STRENGTH = (10.5, 8.6, 5.2)
LAMP_LIGHT_ATTENUATION_LINEAR = 0.022
LAMP_LIGHT_ATTENUATION_QUAD = 0.0022
LAMP_GLOW_Y_BIAS = 0.04
# Wider real spotlight so the lit patch reaches the bench beside the pole
LAMP_SPOT_CUTOFF_DEG = 38.0
LAMP_SPOT_EXPONENT = 38.0
# Soft rim on lamp shadow falloff in degrees
LAMP_SHADOW_CONE_SOFT_DEG = 6.0
# Skinny cone mesh only old style was 13 deg half angle from a 26 deg name
LAMP_BEAM_VISUAL_HALF_DEG = 13.0
LAMP_BEAM_END_Y = -0.985
LAMP_BEAM_ALPHA_APEX = 0.22

ENABLE_BENCH = True
BENCH_HEIGHT = 2.4
BENCH_TINT = (0.62, 0.47, 0.30)
BENCH_GROUND_Y = -1.0
BENCH_ASSET_DIR = "bench"
BENCH_UNDER_ALL_LAMPS = False
# Which poles have benches -> shorter list when you have fewer poles
BENCH_LAMP_INDICES = [0, 3]
BENCH_FALLBACK_POS = (0.0, 38.5)
BENCH_YAW_OFFSET_DEG = 20
BENCH_OFFSET_FROM_LAMP = 1.4
MAX_TREE_INSTANCES = 6
ENABLE_RELIEF = False

# Same road height as scene.py draw_circuit
ROAD_SURFACE_Y = -0.985
# Keep in sync with GL_LIGHT0 moon from the left shadow slides toward +X not under the pole like lamp
MOON_LIGHT_DIR = (-0.92, 0.38, 0.08)
# Moon shadow a bit softer than lamp on purpose
SHADOW_ALPHA_MOON = 0.44
# Black so alpha blend actually reads as shadow brown tint looked washed out
SHADOW_ALPHA_LAMP = 0.72
LAMP_SHADOW_RGB = (0.0, 0.0, 0.0)
LAMP_COLLISION_RADIUS = 0.9
BENCH_COLLISION_RADIUS = 1.75
TREE_COLLISION_RADIUS = 1.05
COLLISION_MARGIN = 0.2
PEDESTRIAN_TINT = (1.0, 1.0, 1.0)
NPC_COUNT = 2
CAR_COLLISION_RADIUS = 1.25


def _shadow_plane_y_at(xz, road_rx_inner=34.0, road_rz_inner=30.0, road_width=4.0):
    # Grass or road under the bench plus tiny nudge so z-fighting behaves
    px, pz = xz
    rx_o = road_rx_inner + road_width
    rz_o = road_rz_inner + road_width
    ei = (px / road_rx_inner) ** 2 + (pz / road_rz_inner) ** 2
    eo = (px / rx_o) ** 2 + (pz / rz_o) ** 2
    on_road = ei >= 1.0 and eo <= 1.0
    base_y = ROAD_SURFACE_Y if on_road else BENCH_GROUND_Y
    return base_y + 0.002


def _lamp_spot_visibility_factor(lx, lamp_y, lz, px, py, pz, cutoff_deg, soft_deg=0.0):
    # How much this point sits in the lamp cone 1 inside 0 out soft_deg blurs the edge
    vx = px - lx
    vy = py - lamp_y
    vz = pz - lz
    ln = math.sqrt(vx * vx + vy * vy + vz * vz)
    if ln < 1e-8:
        return 1.0
    cos_ang = max(-1.0, min(1.0, (-vy) / ln))
    if soft_deg <= 1e-6:
        cos_cut = math.cos(math.radians(float(cutoff_deg)))
        return 1.0 if cos_ang >= cos_cut else 0.0
    c_in = math.cos(math.radians(float(max(0.0, cutoff_deg - soft_deg))))
    c_out = math.cos(math.radians(float(cutoff_deg + soft_deg)))
    if cos_ang >= c_in:
        return 1.0
    if cos_ang <= c_out:
        return 0.0
    return (cos_ang - c_out) / (c_in - c_out + 1e-8)


def _project_mesh_to_plane_point(mesh, tx, ty, tz, light_pos, plane_y):
    # Lamp as point each vertex projects along the ray through the bulb down to plane_y
    lx, ly, lz = light_pos
    out = []
    for vx, vy, vz in mesh.vertices:
        wx = vx + tx
        wy = vy + ty
        wz = vz + tz
        denom = wy - ly
        if abs(denom) < 1e-6:
            t = 0.0
        else:
            t = (plane_y - ly) / denom
        sx = lx + t * (wx - lx)
        sz = lz + t * (wz - lz)
        out.append((sx, plane_y, sz))
    return out


def _project_mesh_to_plane_directional(mesh, tx, ty, tz, light_dir, plane_y):
    # Moon as parallel rays same direction for every vertex
    dx, dy, dz = light_dir
    ln = math.sqrt(dx * dx + dy * dy + dz * dz)
    if ln < 1e-8:
        dx, dy, dz = 0.0, 1.0, 0.0
    else:
        dx, dy, dz = dx / ln, dy / ln, dz / ln
    out = []
    for vx, vy, vz in mesh.vertices:
        wx = vx + tx
        wy = vy + ty
        wz = vz + tz
        # Rays travel from the moon so use minus the stored moon direction
        if abs(dy) < 1e-6:
            t = 0.0
        else:
            t = (plane_y - wy) / (-dy)
        sx = wx + t * (-dx)
        sz = wz + t * (-dz)
        out.append((sx, plane_y, sz))
    return out


def _draw_projected_shadow(mesh, projected_vertices, rgba):
    # Flat tint on the ground no lights no texture just alpha blend
    if mesh is None or not projected_vertices:
        return
    glDisable(GL_LIGHTING)
    glDisable(GL_TEXTURE_2D)
    glShadeModel(GL_FLAT)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    raw_depth_func = glGetIntegerv(GL_DEPTH_FUNC)
    try:
        prev_depth_func = int(raw_depth_func[0])
    except (TypeError, IndexError, ValueError):
        prev_depth_func = int(raw_depth_func)
    glDepthFunc(GL_LEQUAL)
    glDepthMask(GL_FALSE)
    glColor4f(rgba[0], rgba[1], rgba[2], rgba[3])
    glBegin(GL_TRIANGLES)
    for _mname, tris in mesh.groups.items():
        for tri in tris:
            for vi, _vti, _vni in tri:
                sx, sy, sz = projected_vertices[vi]
                glVertex3f(sx, sy, sz)
    glEnd()
    glDisable(GL_BLEND)
    glDepthMask(GL_TRUE)
    glDepthFunc(prev_depth_func)
    glEnable(GL_LIGHTING)
    glShadeModel(GL_SMOOTH)
    glColor3f(1.0, 1.0, 1.0)


def _draw_projected_lamp_shadow(mesh, projected_vertices, rgb, base_alpha, lamp_pos_3d, cutoff_deg, soft_deg):
    # Same bench footprint alpha per vertex so cone edge does not chop the whole thing off
    if mesh is None or not projected_vertices or base_alpha <= 1e-6:
        return
    lx, ly, lz = lamp_pos_3d
    r, g, b = rgb[0], rgb[1], rgb[2]
    glDisable(GL_LIGHTING)
    glDisable(GL_TEXTURE_2D)
    glShadeModel(GL_SMOOTH)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    raw_depth_func = glGetIntegerv(GL_DEPTH_FUNC)
    try:
        prev_depth_func = int(raw_depth_func[0])
    except (TypeError, IndexError, ValueError):
        prev_depth_func = int(raw_depth_func)
    glDepthFunc(GL_LEQUAL)
    glDepthMask(GL_FALSE)
    glBegin(GL_TRIANGLES)
    for _mname, tris in mesh.groups.items():
        for tri in tris:
            for vi, _vti, _vni in tri:
                sx, sy, sz = projected_vertices[vi]
                vis = _lamp_spot_visibility_factor(lx, ly, lz, sx, sy, sz, cutoff_deg, soft_deg=soft_deg)
                glColor4f(r, g, b, float(base_alpha) * vis)
                glVertex3f(sx, sy, sz)
    glEnd()
    glDisable(GL_BLEND)
    glDepthMask(GL_TRUE)
    glDepthFunc(prev_depth_func)
    glEnable(GL_LIGHTING)
    glShadeModel(GL_SMOOTH)
    glColor3f(1.0, 1.0, 1.0)


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
    glClearColor(0.022, 0.028, 0.05, 1.0)
    setup_night_lighting()

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

    lamp_scene = None
    lamp_mat_tex = {}
    lamp_glow_anchor_local = None
    lamp_obj = os.path.join(ASSETS_DIR, "d2fn4gudnri8-rv_Lamp_post4", "rv_lamp_post_4.obj")
    if os.path.isfile(lamp_obj):
        raw_lamp = load_scene_mesh(lamp_obj)
        if raw_lamp is not None:
            lamp_scene = normalize_scene_mesh(raw_lamp, target_height=LAMP_POST_HEIGHT)
            lamp_glow_anchor_local = find_material_anchor_local(lamp_scene, "Lamppost_glow1SG")
            for mname, tex_path in raw_lamp.material_diffuse.items():
                if tex_path and os.path.isfile(tex_path):
                    tid = load_texture(tex_path)
                    if tid:
                        lamp_mat_tex[mname] = int(tid)

    pedestrian_scene = None
    pedestrian_mat_tex = {}
    if ENABLE_PEDESTRIAN_GLB:
        pedestrian_glb = os.path.join(
            ASSETS_DIR,
            "character",
            "55-rp_nathan_animated_003_walking_fbx",
            "rp_nathan_animated_003_walking.glb",
        )
        if os.path.isfile(pedestrian_glb):
            ped_glb_mesh, ped_glb_pils = load_glb_scene_mesh(pedestrian_glb)
            if ped_glb_mesh is not None:
                pedestrian_scene = normalize_scene_mesh(ped_glb_mesh, target_height=PEDESTRIAN_HEIGHT)
                for mname, pil_img in ped_glb_pils.items():
                    tid = load_texture_from_pil(pil_img)
                    if tid:
                        pedestrian_mat_tex[mname] = int(tid)

    bench_scene, bench_mat_tex = (None, {})
    if ENABLE_BENCH:
        bench_scene, bench_mat_tex = load_bench_scene(
            ASSETS_DIR,
            bench_asset_dir=BENCH_ASSET_DIR,
            bench_height=BENCH_HEIGHT,
        )

    # Two posts
    lamp_positions = [
        (0.0, 38.5),
        (31.0, 0.0),
    ]
    lamp_light_ids = [GL_LIGHT1, GL_LIGHT2, GL_LIGHT3, GL_LIGHT4]

    bench_positions = compute_bench_positions(
        lamp_positions,
        bench_under_all_lamps=BENCH_UNDER_ALL_LAMPS,
        bench_lamp_indices=BENCH_LAMP_INDICES,
        fallback_pos=BENCH_FALLBACK_POS,
        offset_from_lamp=BENCH_OFFSET_FROM_LAMP,
    )

    setup_lamp_lights(
        lamp_light_ids,
        diffuse_strength=LAMP_LIGHT_DIFFUSE_STRENGTH,
        attenuation_linear=LAMP_LIGHT_ATTENUATION_LINEAR,
        attenuation_quad=LAMP_LIGHT_ATTENUATION_QUAD,
        spot_cutoff_deg=LAMP_SPOT_CUTOFF_DEG,
        spot_exponent=LAMP_SPOT_EXPONENT,
    )
    car_headlight_ids = (GL_LIGHT5, GL_LIGHT6)
    setup_car_headlights(car_headlight_ids)

    sky_exr = os.path.join(ASSETS_DIR, "sky.exr")
    sky_jpg = os.path.join(ASSETS_DIR, "sky.jpg")
    sky_tex = 0
    if os.path.exists(sky_exr):
        sky_tex = load_texture(sky_exr)
    if not sky_tex:
        sky_tex = load_texture(sky_jpg)

    tree_instances = [
        {
            "x": tx,
            "z": tz,
            "kind": "mesh" if pine_scene is not None else "proc",
            "mesh_scale": 0.95 + 0.04 * ((idx % 4) - 1),
            "proc_scale": 0.92 + 0.03 * (idx % 3),
            "tint_dim": 0.9,
        }
        for idx, (tx, tz) in enumerate(TREE_SITES)
    ]
    tree_instances = tree_instances[:MAX_TREE_INSTANCES]

    bench_draw_data = []
    if ENABLE_BENCH and bench_scene is not None:
        for bpx, bpz in bench_positions:
            closest_lamp = min(
                lamp_positions,
                key=lambda p: (p[0] - bpx) ** 2 + (p[1] - bpz) ** 2,
            )
            lamp_pos_3d = (closest_lamp[0], LAMP_LIGHT_HEIGHT, closest_lamp[1])
            bench_yaw = math.degrees(math.atan2(-bpx, -bpz)) + BENCH_YAW_OFFSET_DEG

            # Rotate vertices one time instead of every frame
            ry = math.radians(bench_yaw)
            cs = math.cos(ry)
            sn = math.sin(ry)
            rot_vertices = []
            for vx, vy, vz in bench_scene.vertices:
                rx = vx * cs + vz * sn
                rz = -vx * sn + vz * cs
                rot_vertices.append((rx, vy, rz))

            class _TmpMesh:
                pass

            tmp_mesh = _TmpMesh()
            tmp_mesh.vertices = rot_vertices
            tmp_mesh.groups = bench_scene.groups

            plane_y = _shadow_plane_y_at((bpx, bpz))
            lamp_shadow = _project_mesh_to_plane_point(
                tmp_mesh, bpx, BENCH_GROUND_Y, bpz, lamp_pos_3d, plane_y
            )
            moon_shadow = _project_mesh_to_plane_directional(
                tmp_mesh, bpx, BENCH_GROUND_Y, bpz, MOON_LIGHT_DIR, plane_y
            )
            bench_draw_data.append(
                {
                    "x": bpx,
                    "z": bpz,
                    "yaw": bench_yaw,
                    "tmp_mesh": tmp_mesh,
                    "lamp_shadow": lamp_shadow,
                    "moon_shadow": moon_shadow,
                    "lamp_pos_3d": lamp_pos_3d,
                }
            )

    cam_cfg = CameraConfig()
    cam_state = CameraState()
    ped_cfg = PedestrianConfig()
    ped_state = PedestrianState()

    blocked_circles = []
    for lx, lz in lamp_positions:
        blocked_circles.append((lx, lz, LAMP_COLLISION_RADIUS + ped_cfg.radius + COLLISION_MARGIN))
    for bpx, bpz in bench_positions:
        blocked_circles.append((bpx, bpz, BENCH_COLLISION_RADIUS + ped_cfg.radius + COLLISION_MARGIN))
    for tree in tree_instances:
        tx = float(tree["x"])
        tz = float(tree["z"])
        blocked_circles.append((tx, tz, TREE_COLLISION_RADIUS + ped_cfg.radius + COLLISION_MARGIN))

    npc_waypoints = []
    for bpx, bpz in bench_positions:
        npc_waypoints.append((bpx + 3.6, bpz))
        npc_waypoints.append((bpx - 3.6, bpz))
        npc_waypoints.append((bpx, bpz + 3.6))
        npc_waypoints.append((bpx, bpz - 3.6))
    for lx, lz in lamp_positions:
        npc_waypoints.append((lx + 2.8, lz))
        npc_waypoints.append((lx - 2.8, lz))
    npc_waypoints.extend([(24.0, 28.0), (-24.0, 28.0), (24.0, -28.0), (-24.0, -28.0)])
    npc_blocked = list(blocked_circles)
    random_walkers = init_random_walkers(NPC_COUNT, npc_waypoints)
    car_state = CarState()
    car_hit_cooldown = 0.0
    player_hit_flash = 0.0

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
        apply_camera_view(cam_state, scene_y_offset=-2.0)

        active_indices = select_active_lamp_indices(
            cam_state.x,
            cam_state.z,
            lamp_positions,
            LAMP_LIGHTS_MAX,
            required_indices=BENCH_LAMP_INDICES if (ENABLE_BENCH and bench_scene is not None) else [],
        )
        apply_active_lights(lamp_light_ids, active_indices, lamp_positions, LAMP_LIGHT_HEIGHT)

        update_camera_from_input(window, dt, cam_state, cam_cfg)
        update_pedestrian_from_input(window, dt, ped_state, ped_cfg, blocked_circles)
        update_random_walkers(random_walkers, dt, npc_waypoints, npc_blocked)
        update_car_state(car_state, dt, rx=36.2, rz=32.2)
        if car_hit_cooldown > 0.0:
            car_hit_cooldown = max(0.0, car_hit_cooldown - dt)
        if player_hit_flash > 0.0:
            player_hit_flash = max(0.0, player_hit_flash - dt)

        dx_pc = ped_state.x - car_state.x
        dz_pc = ped_state.z - car_state.z
        hit_r = ped_cfg.radius + CAR_COLLISION_RADIUS
        if car_hit_cooldown <= 0.0 and (dx_pc * dx_pc + dz_pc * dz_pc) <= (hit_r * hit_r):
            push_len = math.sqrt(max(1e-8, dx_pc * dx_pc + dz_pc * dz_pc))
            push_x = dx_pc / push_len
            push_z = dz_pc / push_len
            ped_state.x += push_x * 1.15
            ped_state.z += push_z * 1.15
            ped_state.yaw_deg = math.degrees(math.atan2(push_x, push_z))
            car_hit_cooldown = 0.9
            player_hit_flash = 0.28

        glDepthMask(GL_FALSE)
        draw_skybox(sky_tex)
        glDepthMask(GL_TRUE)
        enforce_night_lighting_state()
        apply_car_headlights(car_headlight_ids[0], car_headlight_ids[1], car_state)

        draw_ground(grass_tex, tint=GROUND_TINT)
        if ENABLE_RELIEF:
            draw_relief(grass_tex, -22.0, 22.0, -22.0, 22.0, tint=GROUND_TINT)
        draw_circuit(road_tex, rx_inner=34.0, rz_inner=30.0, road_width=4.0, tint=ROAD_TINT)
        draw_static_trees(
            ground_y=-1.0,
            tree_instances=tree_instances,
            scene_mesh=pine_scene,
            material_to_texid=pine_mat_tex if pine_scene else None,
            obj_tint=TREE_MESH_TINT,
        )
        draw_car(car_state, ground_y=BENCH_GROUND_Y)

        if ENABLE_BENCH and bench_scene is not None:
            for bench_item in bench_draw_data:
                bpx = bench_item["x"]
                bpz = bench_item["z"]
                bench_yaw = bench_item["yaw"]
                tmp_mesh = bench_item["tmp_mesh"]
                lamp_shadow = bench_item["lamp_shadow"]
                moon_shadow = bench_item["moon_shadow"]
                lamp_pos_3d = bench_item["lamp_pos_3d"]

                _draw_projected_lamp_shadow(
                    tmp_mesh,
                    lamp_shadow,
                    LAMP_SHADOW_RGB,
                    SHADOW_ALPHA_LAMP,
                    lamp_pos_3d,
                    LAMP_SPOT_CUTOFF_DEG,
                    LAMP_SHADOW_CONE_SOFT_DEG,
                )
                _draw_projected_shadow(tmp_mesh, moon_shadow, (0.0, 0.0, 0.0, SHADOW_ALPHA_MOON))

                draw_scene_mesh(
                    bench_scene,
                    bench_mat_tex,
                    bpx,
                    BENCH_GROUND_Y,
                    bpz,
                    tint=BENCH_TINT,
                    uniform_scale=1.0,
                    rotate_y_deg=bench_yaw,
                )

        if lamp_scene is not None:
            for lx, lz in lamp_positions:
                draw_scene_mesh(
                    lamp_scene,
                    lamp_mat_tex,
                    lx,
                    -1.0,
                    lz,
                    tint=LAMP_POST_TINT,
                    uniform_scale=1.0,
                )
                if lamp_glow_anchor_local is not None:
                    ax, ay, az = lamp_glow_anchor_local
                    lamp_glow_x = lx + ax
                    lamp_glow_y = -1.0 + ay + LAMP_GLOW_Y_BIAS
                    lamp_glow_z = lz + az
                    draw_lamp_beam_cone(
                        lamp_glow_x,
                        lamp_glow_y,
                        lamp_glow_z,
                        LAMP_BEAM_END_Y,
                        visual_half_angle_deg=LAMP_BEAM_VISUAL_HALF_DEG,
                        alpha_apex=LAMP_BEAM_ALPHA_APEX,
                    )
                    draw_lamp_glow_orb(lamp_glow_x, lamp_glow_y, lamp_glow_z, radius=0.22)
                else:
                    draw_lamp_beam_cone(
                        lx,
                        LAMP_LIGHT_HEIGHT,
                        lz,
                        LAMP_BEAM_END_Y,
                        visual_half_angle_deg=LAMP_BEAM_VISUAL_HALF_DEG,
                        alpha_apex=LAMP_BEAM_ALPHA_APEX,
                    )
                    draw_lamp_glow_orb(lx, LAMP_LIGHT_HEIGHT, lz)

        draw_pedestrian(
            ped_state,
            ground_y=BENCH_GROUND_Y,
            scene_mesh=pedestrian_scene,
            material_to_texid=pedestrian_mat_tex,
            tint=PEDESTRIAN_TINT,
        )
        if player_hit_flash > 0.0:
            glDisable(GL_LIGHTING)
            glDisable(GL_TEXTURE_2D)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glColor4f(1.0, 0.2, 0.2, 0.35)
            glPushMatrix()
            glTranslatef(ped_state.x, BENCH_GROUND_Y + 0.02, ped_state.z)
            q = gluNewQuadric()
            try:
                glRotatef(-90.0, 1.0, 0.0, 0.0)
                gluDisk(q, 0.0, 0.95, 20, 1)
            finally:
                gluDeleteQuadric(q)
            glPopMatrix()
            glDisable(GL_BLEND)
            glEnable(GL_LIGHTING)
            glColor3f(1.0, 1.0, 1.0)
        for w in random_walkers:
            draw_random_walker(w, now, ground_y=BENCH_GROUND_Y)

        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()


if __name__ == "__main__":
    main()
