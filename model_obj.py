"""Wavefront OBJ/MTL and glTF mesh loading with immediate-mode drawing"""

import os
from collections import OrderedDict
from OpenGL.GL import *


class SceneMesh:
    __slots__ = ("vertices", "texcoords", "normals", "groups", "material_diffuse", "material_kd", "material_blend")

    def __init__(self, vertices, texcoords, normals, groups, material_diffuse, material_kd=None, material_blend=None):
        self.vertices = vertices
        self.texcoords = texcoords
        self.normals = normals
        self.groups = groups
        self.material_diffuse = material_diffuse
        self.material_kd = material_kd if material_kd is not None else {}
        self.material_blend = material_blend


def load_mtl(mtl_path):
    """Material diffuse maps and Kd colors by material name"""
    if not mtl_path or not os.path.isfile(mtl_path):
        return {}, {}
    mats = OrderedDict()
    kd_by_mat = OrderedDict()
    current = None
    mtl_dir = os.path.dirname(os.path.abspath(mtl_path))
    with open(mtl_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if not parts:
                continue
            key = parts[0].lower()
            if key == "newmtl":
                current = " ".join(parts[1:]).strip()
                if current:
                    mats[current] = None
                    kd_by_mat[current] = None
            elif key == "kd" and current is not None and current in mats and len(parts) >= 4:
                try:
                    kd_by_mat[current] = (float(parts[1]), float(parts[2]), float(parts[3]))
                except ValueError:
                    pass
            elif key == "map_kd" and current is not None and current in mats:
                path_token = parts[-1].strip('"').replace("\\", os.sep)
                if path_token:
                    full = path_token if os.path.isabs(path_token) else os.path.normpath(os.path.join(mtl_dir, path_token))
                    mats[current] = full
    return mats, kd_by_mat


def _parse_face_vert(chunk, nv, nt, nn):
    parts = chunk.split("/")

    def parse_idx(s, n):
        if not s:
            return None
        i = int(s)
        if i < 0:
            return n + i
        return i - 1

    vi = parse_idx(parts[0], nv)
    vti = parse_idx(parts[1], nt) if len(parts) > 1 and parts[1] else None
    vni = parse_idx(parts[2], nn) if len(parts) > 2 and parts[2] else None
    return [vi, vti, vni]


def load_scene_mesh(obj_path):
    obj_path = os.path.abspath(obj_path)
    obj_dir = os.path.dirname(obj_path)

    vertices = []
    texcoords = []
    normals = []
    groups = OrderedDict()
    material_diffuse = OrderedDict()
    material_kd = OrderedDict()

    mtl_maps = OrderedDict()
    mtl_kd = OrderedDict()
    mtl_loaded = False
    current_mtl = "__default__"
    groups[current_mtl] = []

    with open(obj_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            tag = parts[0]
            if tag == "mtllib" and len(parts) >= 2:
                mtl_name = " ".join(parts[1:]).strip('"')
                mtl_path = os.path.normpath(os.path.join(obj_dir, mtl_name))
                mtl_maps, mtl_kd = load_mtl(mtl_path)
                mtl_loaded = True
                material_diffuse.clear()
                material_diffuse.update(mtl_maps)
                material_kd.clear()
                material_kd.update(mtl_kd)
            elif tag == "usemtl" and len(parts) >= 2:
                current_mtl = " ".join(parts[1:]).strip()
                if current_mtl not in groups:
                    groups[current_mtl] = []
            elif tag == "v" and len(parts) >= 4:
                vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif tag == "vt" and len(parts) >= 3:
                texcoords.append([float(parts[1]), float(parts[2])])
            elif tag == "vn" and len(parts) >= 4:
                normals.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif tag == "f":
                nv_c = len(vertices)
                nt_c = len(texcoords)
                nn_c = len(normals)
                verts = [_parse_face_vert(p, nv_c, nt_c, nn_c) for p in parts[1:]]
                if len(verts) < 3:
                    continue
                for k in range(1, len(verts) - 1):
                    groups[current_mtl].append([verts[0], verts[k], verts[k + 1]])

    nv = len(vertices)
    nt = len(texcoords)
    nn = len(normals)
    fixed_groups = OrderedDict()
    for mname, tris in groups.items():
        out = []
        for tri in tris:
            new_tri = []
            bad = False
            for vi, vti, vni in tri:
                if vi is None or vi < 0 or vi >= nv:
                    bad = True
                    break
                if vti is not None and (vti < 0 or vti >= nt):
                    vti = None
                if vni is not None and (vni < 0 or vni >= nn):
                    vni = None
                new_tri.append([vi, vti, vni])
            if not bad:
                out.append(new_tri)
        if out:
            fixed_groups[mname] = out

    nonempty = [g for g in fixed_groups.values() if g]
    if not nonempty:
        return None

    return SceneMesh(vertices, texcoords, normals, fixed_groups, material_diffuse, material_kd)


def normalize_scene_mesh(mesh, target_height=7.0):
    vs = mesh.vertices
    min_y = min(v[1] for v in vs)
    max_y = max(v[1] for v in vs)
    h = max_y - min_y
    s = target_height / h if h > 1e-6 else 1.0
    cx = sum(v[0] for v in vs) / len(vs)
    cz = sum(v[2] for v in vs) / len(vs)
    new_v = []
    for x, y, z in vs:
        new_v.append([(x - cx) * s, (y - min_y) * s, (z - cz) * s])
    return SceneMesh(
        new_v,
        mesh.texcoords,
        mesh.normals,
        mesh.groups,
        mesh.material_diffuse,
        getattr(mesh, "material_kd", None),
        getattr(mesh, "material_blend", None),
    )


def load_glb_scene_mesh(glb_path):
    """Load glTF binary to SceneMesh and PIL baseColor images (requires trimesh)"""
    import numpy as np

    try:
        import trimesh
    except ImportError:
        import sys

        print(
            "glTF (GLB) loading requires trimesh: python -m pip install trimesh",
            file=sys.stderr,
        )
        return None, {}

    glb_path = os.path.abspath(glb_path)
    if not os.path.isfile(glb_path):
        return None, {}

    try:
        scene = trimesh.load(glb_path, force="scene")
    except Exception:
        return None, {}

    from PIL import Image

    vertices = []
    texcoords = []
    normals = []
    groups = OrderedDict()
    material_diffuse = OrderedDict()
    material_kd = OrderedDict()
    material_blend = OrderedDict()
    pil_by_material = OrderedDict()

    def _white():
        return Image.new("RGB", (1, 1), (220, 220, 220))

    for name, geom in scene.geometry.items():
        mesh = geom
        if not hasattr(mesh, "faces") or mesh.faces is None or len(mesh.faces) == 0:
            continue
        vs = np.asarray(mesh.vertices, dtype=np.float64)
        fc = np.asarray(mesh.faces, dtype=np.int64)
        if vs.size == 0:
            continue

        if mesh.vertex_normals is None or len(mesh.vertex_normals) != len(vs):
            mesh.fix_normals()
        ns = np.asarray(mesh.vertex_normals, dtype=np.float64)

        uvs = None
        vis = mesh.visual
        if hasattr(vis, "uv") and vis.uv is not None:
            uvs = np.asarray(vis.uv, dtype=np.float64)
        if uvs is None or len(uvs) != len(vs):
            uvs = np.zeros((len(vs), 2), dtype=np.float64)

        mname = str(name).replace(" ", "_") or "mesh"
        mname = f"glb_{mname}"
        while mname in groups:
            mname = mname + "_"

        v_base = len(vertices)
        vertices.extend(vs.tolist())
        texcoords.extend(uvs.tolist())
        normals.extend(ns.tolist())

        tris = []
        for a, b, c in fc:
            ai, bi, ci = int(a), int(b), int(c)
            tris.append(
                [
                    [v_base + ai, v_base + ai, v_base + ai],
                    [v_base + bi, v_base + bi, v_base + bi],
                    [v_base + ci, v_base + ci, v_base + ci],
                ]
            )
        groups[mname] = tris
        material_diffuse[mname] = "__glb__"
        material_kd[mname] = None

        pil_img = _white()
        blend = False
        if hasattr(vis, "material") and vis.material is not None:
            m = vis.material
            if getattr(m, "baseColorTexture", None) is not None:
                tex = m.baseColorTexture
                pil_img = tex.copy() if hasattr(tex, "copy") else tex
                if pil_img.mode == "RGBA":
                    blend = True
        material_blend[mname] = blend
        pil_by_material[mname] = pil_img

    if not groups:
        return None, {}

    return (
        SceneMesh(vertices, texcoords, normals, groups, material_diffuse, material_kd, material_blend),
        dict(pil_by_material),
    )


def _material_needs_blend(tex_path):
    if not tex_path:
        return False
    low = tex_path.lower()
    return "twig" in low or "needle" in low or "leaf" in low


def _material_is_glow(material_name):
    low = (material_name or "").lower()
    return "glow" in low or "emissive" in low or "light" in low


def _tex_id_value(tid):
    if tid is None:
        return 0
    try:
        return int(tid)
    except (TypeError, ValueError):
        return 0


def draw_scene_mesh(
    mesh,
    material_to_texid,
    translate_x,
    translate_y,
    translate_z,
    tint=(1.0, 1.0, 1.0),
    uniform_scale=1.0,
    rotate_y_deg=0.0,
):
    if mesh is None:
        return
    if material_to_texid is None:
        material_to_texid = {}
    glPushMatrix()
    glTranslatef(translate_x, translate_y, translate_z)
    ry = float(rotate_y_deg)
    if abs(ry) > 1e-6:
        glRotatef(ry, 0.0, 1.0, 0.0)
    s = float(uniform_scale)
    if abs(s - 1.0) > 1e-6:
        glScalef(s, s, s)
    default_n = (0.0, 1.0, 0.0)
    vs = mesh.vertices
    ts = mesh.texcoords
    ns = mesh.normals

    for mname, tris in mesh.groups.items():
        tex_id = material_to_texid.get(mname, 0)
        tex_id = _tex_id_value(tex_id)
        path = mesh.material_diffuse.get(mname, "") or ""
        is_glow = _material_is_glow(mname)
        mb = getattr(mesh, "material_blend", None) or {}
        if mname in mb:
            need_blend = mb[mname]
        else:
            need_blend = _material_needs_blend(path)

        if tex_id == 0:
            glDisable(GL_TEXTURE_2D)
            kd_map = getattr(mesh, "material_kd", None) or {}
            kd = kd_map.get(mname)
            if kd is not None:
                c = (
                    max(0.0, min(1.0, kd[0] * tint[0])),
                    max(0.0, min(1.0, kd[1] * tint[1])),
                    max(0.0, min(1.0, kd[2] * tint[2])),
                )
            else:
                c = (
                    max(0.0, min(1.0, tint[0] * 0.62)),
                    max(0.0, min(1.0, tint[1] * 0.62)),
                    max(0.0, min(1.0, tint[2] * 0.62)),
                )
            if is_glow:
                c = (
                    max(c[0], 0.95),
                    max(c[1], 0.80),
                    max(c[2], 0.46),
                )
                glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.95, 0.72, 0.26, 1.0))
            glColor3f(*c)
            glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.0, 0.0, 0.0, 1.0))
            glBegin(GL_TRIANGLES)
            for tri in tris:
                for vi, vti, vni in tri:
                    x, y, z = vs[vi]
                    if vni is not None:
                        nx, ny, nz = ns[vni]
                        glNormal3f(nx, ny, nz)
                    else:
                        glNormal3f(*default_n)
                    glVertex3f(x, y, z)
            glEnd()
            if is_glow:
                glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.0, 0.0, 0.0, 1.0))
            continue

        glColor3f(*tint)
        if is_glow:
            glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.95, 0.72, 0.26, 1.0))
        if need_blend:
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.04, 0.04, 0.04, 1.0))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 6.0)
        glBegin(GL_TRIANGLES)
        for tri in tris:
            for vi, vti, vni in tri:
                x, y, z = vs[vi]
                if vni is not None:
                    nx, ny, nz = ns[vni]
                    glNormal3f(nx, ny, nz)
                else:
                    glNormal3f(*default_n)
                if vti is not None:
                    u, vv = ts[vti]
                    glTexCoord2f(u, 1.0 - vv)
                else:
                    glTexCoord2f(0.0, 0.0)
                glVertex3f(x, y, z)
        glEnd()
        if need_blend:
            glDisable(GL_BLEND)
        glDisable(GL_TEXTURE_2D)
        if is_glow:
            glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.0, 0.0, 0.0, 1.0))

    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.0, 0.0, 0.0, 1.0))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 0.0)
    glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.0, 0.0, 0.0, 1.0))
    glColor3f(1.0, 1.0, 1.0)
    glPopMatrix()


def load_obj(path):
    mesh = load_scene_mesh(path)
    if mesh is None:
        return None
    if len(mesh.groups) != 1:
        return None
    only = next(iter(mesh.groups.values()))
    from types import SimpleNamespace
    fake = SimpleNamespace()
    fake.vertices = mesh.vertices
    fake.texcoords = mesh.texcoords
    fake.normals = mesh.normals
    fake.triangles = only
    return fake


def normalize_tree_mesh(mesh, target_height=7.0):
    if mesh is None:
        return None
    vs = mesh.vertices
    min_y = min(v[1] for v in vs)
    max_y = max(v[1] for v in vs)
    h = max_y - min_y
    s = target_height / h if h > 1e-6 else 1.0
    cx = sum(v[0] for v in vs) / len(vs)
    cz = sum(v[2] for v in vs) / len(vs)
    new_v = []
    for x, y, z in vs:
        new_v.append([(x - cx) * s, (y - min_y) * s, (z - cz) * s])
    from types import SimpleNamespace
    out = SimpleNamespace()
    out.vertices = new_v
    out.texcoords = mesh.texcoords
    out.normals = mesh.normals
    out.triangles = mesh.triangles
    return out


def draw_obj_mesh(mesh, texture_id, translate_x, translate_y, translate_z, tint=(1.0, 1.0, 1.0)):
    if mesh is None or not texture_id:
        return
    glPushMatrix()
    glTranslatef(translate_x, translate_y, translate_z)
    glColor3f(*tint)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.05, 0.05, 0.05, 1.0))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 8.0)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glBegin(GL_TRIANGLES)
    default_n = (0.0, 1.0, 0.0)
    for tri in mesh.triangles:
        for vi, vti, vni in tri:
            x, y, z = mesh.vertices[vi]
            if vni is not None:
                nx, ny, nz = mesh.normals[vni]
                glNormal3f(nx, ny, nz)
            else:
                glNormal3f(*default_n)
            if vti is not None:
                u, v = mesh.texcoords[vti]
                glTexCoord2f(u, 1.0 - v)
            else:
                glTexCoord2f(0.0, 0.0)
            glVertex3f(x, y, z)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.0, 0.0, 0.0, 1.0))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 0.0)
    glColor3f(1.0, 1.0, 1.0)
    glPopMatrix()
