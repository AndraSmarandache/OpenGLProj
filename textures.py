"""2D texture uploads from files and PIL (LDR, EXR, glTF images)"""

import os
from OpenGL.GL import *
from PIL import Image


def _load_texture_exr(path):
    """Tonemap EXR to packed RGB bytes or (None, None, None) on error"""
    import numpy as np
    try:
        import imageio
    except ImportError:
        print("Error: install imageio to use .exr textures: pip install imageio")
        return None, None, None
    try:
        arr = imageio.imread(path, format="EXR-FI")
    except Exception:
        try:
            import imageio.plugins.freeimage
            imageio.plugins.freeimage.download()
            arr = imageio.imread(path, format="EXR-FI")
        except Exception as e2:
            print(f"Error loading EXR {path}: {e2}")
            return None, None, None
    # Expand grayscale to RGB and drop alpha if present
    if arr.ndim == 2:
        arr = arr[:, :, np.newaxis].repeat(3, axis=2)
    elif arr.shape[2] == 4:
        arr = arr[:, :, :3]
    h, w = arr.shape[0], arr.shape[1]
    # Tonemap HDR then convert to uint8 for OpenGL
    if arr.dtype in (np.float32, np.float64):
        try:
            if arr.max() > 1.0:
                arr = arr / (1.0 + arr)
            arr = np.clip(arr, 0, 1)
            arr = (arr * 255).astype(np.uint8)
        except MemoryError:
            print(f"EXR too large for memory, fallback needed: {path}")
            return None, None, None
    else:
        arr = arr.astype(np.uint8, copy=False)
    arr = np.ascontiguousarray(arr[::-1, :, :])
    return w, h, arr.tobytes()

def load_texture(path):
    """Load an image file into a 2D texture, returning 0 on failure"""
    if not os.path.exists(path):
        print(f"Error: {path} not found!")
        return 0
    
    if path.lower().endswith(".exr"):
        result = _load_texture_exr(path)
        if result[0] is None:
            return 0
        w, h, img_data = result
    else:
        try:
            img = Image.open(path)
            max_side = 1024
            try:
                w0, h0 = img.size
                if max(w0, h0) > max_side:
                    img.thumbnail((max_side, max_side), Image.Resampling.BILINEAR)
            except Exception:
                pass
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
            img_data = img.convert("RGB").tobytes()
            w, h = img.width, img.height
        except MemoryError:
            print(f"Texture skipped due to low memory: {path}")
            return 0
    
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)
    return tex_id

def load_texture_from_pil(img):
    """Upload a PIL image to a new 2D texture"""
    if img is None:
        return 0
    img = img.copy()
    img = img.transpose(Image.FLIP_TOP_BOTTOM)
    use_rgba = img.mode == "RGBA"
    if not use_rgba:
        img = img.convert("RGB")
    img_data = img.tobytes()
    w, h = img.width, img.height
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    if use_rgba:
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    else:
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    if use_rgba:
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
    else:
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)
    return tex_id

def load_texture_rgba(path):
    """RGBA texture with CLAMP_TO_EDGE for cutout sprites"""
    if not os.path.exists(path):
        print(f"Error: {path} not found!")
        return 0
    img = Image.open(path)
    img = img.transpose(Image.FLIP_TOP_BOTTOM)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    img_data = img.tobytes()
    w, h = img.width, img.height
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
    return tex_id

def load_texture_diffuse_alpha(diff_path, alpha_path, max_side=2048):
    """Merge diffuse and alpha files into one RGBA texture with optional mipmaps"""
    if not os.path.exists(diff_path):
        return 0
    diff = Image.open(diff_path).convert("RGB")
    if alpha_path and os.path.exists(alpha_path):
        aimg = Image.open(alpha_path)
        aimg = aimg.convert("L") if aimg.mode == "L" else aimg.convert("RGB").split()[0]
        if aimg.size != diff.size:
            aimg = aimg.resize(diff.size, Image.Resampling.LANCZOS)
        r, g, b = diff.split()
        rgba = Image.merge("RGBA", (r, g, b, aimg))
    else:
        rgba = diff.convert("RGBA")
    if max_side and max(rgba.size) > max_side:
        w, h = rgba.size
        scale = max_side / float(max(w, h))
        rgba = rgba.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)
    rgba = rgba.transpose(Image.FLIP_TOP_BOTTOM)
    w, h = rgba.width, rgba.height
    img_data = rgba.tobytes()
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
    try:
        glGenerateMipmap(GL_TEXTURE_2D)
    except Exception:
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    return tex_id

def load_heightmap(path):
    """Load grayscale height map rows or None"""
    if not os.path.exists(path):
        print(f"Heightmap {path} not found; using procedural relief")
        return None
    img = Image.open(path)
    img = img.convert("L")
    w, h = img.size[0], img.size[1]
    data = list(img.getdata())
    pixels = [data[row * w : (row + 1) * w] for row in range(h)]
    return (w, h, pixels)

def sample_heightmap(hm_width, hm_height, hm_pixels, u, v):
    """Nearest sample at normalized uv with v flipped for image row order"""
    u = max(0, min(1, u))
    v = max(0, min(1, v))
    
    col = int(u * (hm_width - 1) + 0.5)
    row = int((1 - v) * (hm_height - 1) + 0.5)
    
    row = max(0, min(hm_height - 1, row))
    col = max(0, min(hm_width - 1, col))
    
    return hm_pixels[row][col] / 255.0
