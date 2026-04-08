import math
from dataclasses import dataclass

import glfw
from OpenGL.GL import glRotatef, glTranslatef


@dataclass
class CameraConfig:
    move_units_per_sec: float = 16.0
    turn_deg_per_sec: float = 160.0
    pitch_deg_per_sec: float = 130.0
    sprint_mult: float = 2.4
    input_response_accel: float = 20.0
    input_response_brake: float = 30.0
    min_pitch_deg: float = -85.0
    max_pitch_deg: float = 85.0
    move_radius_limit: float = 44.0


@dataclass
class CameraState:
    x: float = 0.0
    z: float = -15.0
    yaw_deg: float = 0.0
    pitch_deg: float = 5.0
    forward_vel: float = 0.0
    yaw_vel: float = 0.0
    pitch_vel: float = 0.0


def _axis_pressed(window, key_pos, key_neg):
    pos = 1.0 if glfw.get_key(window, key_pos) == glfw.PRESS else 0.0
    neg = 1.0 if glfw.get_key(window, key_neg) == glfw.PRESS else 0.0
    return pos - neg


def _smooth_vel(current, target, dt, accel_response, brake_response):
    same_direction = (current * target) > 0.0
    accelerating = abs(target) > abs(current) and same_direction
    response = accel_response if accelerating else brake_response
    blend = 1.0 - math.exp(-response * dt)
    return current + (target - current) * blend


def update_camera_from_input(window, dt, state: CameraState, cfg: CameraConfig):
    key_shift_l = glfw.get_key(window, glfw.KEY_LEFT_SHIFT)
    key_shift_r = glfw.get_key(window, glfw.KEY_RIGHT_SHIFT)
    sprint = (key_shift_l == glfw.PRESS) or (key_shift_r == glfw.PRESS)
    move_speed = cfg.move_units_per_sec * (cfg.sprint_mult if sprint else 1.0)

    forward_axis = _axis_pressed(window, glfw.KEY_W, glfw.KEY_S)
    yaw_axis = _axis_pressed(window, glfw.KEY_A, glfw.KEY_D)
    pitch_axis = _axis_pressed(window, glfw.KEY_E, glfw.KEY_Q)

    target_forward_vel = forward_axis * move_speed
    target_yaw_vel = yaw_axis * cfg.turn_deg_per_sec
    target_pitch_vel = pitch_axis * cfg.pitch_deg_per_sec

    state.forward_vel = _smooth_vel(state.forward_vel, target_forward_vel, dt, cfg.input_response_accel, cfg.input_response_brake)
    state.yaw_vel = _smooth_vel(state.yaw_vel, target_yaw_vel, dt, cfg.input_response_accel, cfg.input_response_brake)
    state.pitch_vel = _smooth_vel(state.pitch_vel, target_pitch_vel, dt, cfg.input_response_accel, cfg.input_response_brake)

    state.x += math.sin(math.radians(state.yaw_deg)) * state.forward_vel * dt
    state.z += math.cos(math.radians(state.yaw_deg)) * state.forward_vel * dt
    state.yaw_deg += state.yaw_vel * dt
    state.pitch_deg += state.pitch_vel * dt
    state.pitch_deg = max(cfg.min_pitch_deg, min(cfg.max_pitch_deg, state.pitch_deg))

    dist = math.sqrt(state.x * state.x + state.z * state.z)
    if dist > cfg.move_radius_limit:
        f = cfg.move_radius_limit / dist
        state.x *= f
        state.z *= f


def apply_camera_view(state: CameraState, scene_y_offset=-2.0):
    glTranslatef(0.0, scene_y_offset, 0.0)
    glRotatef(state.pitch_deg, 1.0, 0.0, 0.0)
    glRotatef(state.yaw_deg, 0.0, 1.0, 0.0)
    glTranslatef(-state.x, 0.0, -state.z)
