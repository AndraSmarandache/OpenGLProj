import math
import os

from model_obj import load_scene_mesh, normalize_scene_mesh, draw_scene_mesh


def load_bench_scene(assets_dir, bench_asset_dir="bench", bench_height=2.4):
    bench_scene = None
    bench_mat_tex = {}
    bench_dir = os.path.join(assets_dir, bench_asset_dir)
    bench_obj = os.path.join(bench_dir, "bench.obj")
    if os.path.isfile(bench_obj):
        raw_bench = load_scene_mesh(bench_obj)
        if raw_bench is not None:
            bench_scene = normalize_scene_mesh(raw_bench, target_height=bench_height)
    return bench_scene, bench_mat_tex


def compute_bench_positions(
    lamp_positions,
    bench_under_all_lamps=False,
    bench_lamp_indices=None,
    fallback_pos=(0.0, 38.5),
    offset_from_lamp=1.4,
):
    if bench_under_all_lamps:
        base_positions = list(lamp_positions)
    else:
        indices = bench_lamp_indices or []
        base_positions = [lamp_positions[i] for i in indices if 0 <= i < len(lamp_positions)]
        if not base_positions:
            base_positions = [fallback_pos]

    bench_positions = []
    for lx, lz in base_positions:
        to_center_x = -lx
        to_center_z = -lz
        to_center_len = math.hypot(to_center_x, to_center_z)
        if to_center_len > 1e-6:
            dx = (to_center_x / to_center_len) * offset_from_lamp
            dz = (to_center_z / to_center_len) * offset_from_lamp
        else:
            dx, dz = 0.0, 0.0
        bench_positions.append((lx + dx, lz + dz))
    return bench_positions


def draw_benches(bench_scene, bench_mat_tex, bench_positions, bench_ground_y, bench_tint, bench_yaw_offset_deg):
    if bench_scene is None:
        return
    for bpx, bpz in bench_positions:
        bench_yaw = math.degrees(math.atan2(-bpx, -bpz)) + bench_yaw_offset_deg
        draw_scene_mesh(
            bench_scene,
            bench_mat_tex,
            bpx,
            bench_ground_y,
            bpz,
            tint=bench_tint,
            uniform_scale=1.0,
            rotate_y_deg=bench_yaw,
        )
