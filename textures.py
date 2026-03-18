import os
from OpenGL.GL import *
from PIL import Image

# loads an EXR (HDR) image and returns (width, height, rgb_bytes) for use with glTexImage2D; returns (None, None, None) on failure
# EXR stores float values (can be > 1.0) so we tonemap and convert to 8-bit; OpenGL expects origin at bottom so we flip rows
def _load_texture_exr(path):
    import numpy as np
    try:
        import imageio
    except ImportError:
        print("Error: install imageio to use .exr textures: pip install imageio")
        return None, None, None
    try:
        arr = imageio.imread(path, format="EXR-FI")  # FreeImage plugin required for EXR
    except Exception:
        try:
            import imageio.plugins.freeimage
            imageio.plugins.freeimage.download()  # first run may download FreeImage DLL
            arr = imageio.imread(path, format="EXR-FI")
        except Exception as e2:
            print(f"Error loading EXR {path}: {e2}")
            return None, None, None
    # grayscale: duplicate to RGB; RGBA: drop alpha
    if arr.ndim == 2:
        arr = arr[:, :, np.newaxis].repeat(3, axis=2)
    elif arr.shape[2] == 4:
        arr = arr[:, :, :3]
    h, w = arr.shape[0], arr.shape[1]
    # tonemap HDR values > 1 so they don't blow out; then clamp to [0,1] and convert to uint8 for OpenGL
    if arr.dtype in (np.float32, np.float64):
        if arr.max() > 1.0:
            arr = arr / (1.0 + arr)  # simple Reinhard-style: compresses bright areas
        arr = np.clip(arr, 0, 1)
    arr = (arr * 255).astype(np.uint8)
    arr = np.ascontiguousarray(arr[::-1, :, :])  # flip Y so texture origin matches OpenGL bottom-left
    return w, h, arr.tobytes()

# helper function for loading texture; supports .jpg/.png (PIL) and .exr (imageio + FreeImage); returns OpenGL texture id or 0 on error
def load_texture(path):
    if not os.path.exists(path):
        print(f"Error: {path} not found!")
        return 0
    
    if path.lower().endswith(".exr"):
        result = _load_texture_exr(path)
        if result[0] is None:
            return 0
        w, h, img_data = result
    else:
        img = Image.open(path)
        img = img.transpose(Image.FLIP_TOP_BOTTOM) # flip for OpenGL coordinates(in OpenGl, (0, 0) is at bottom-left and we want it at top-left)
        img_data = img.convert("RGB").tobytes()
        w, h = img.width, img.height
    
    tex_id = glGenTextures(1) # id number to store the new texture
    glBindTexture(GL_TEXTURE_2D, tex_id) # binds future modifications to the newly created texture
    
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR) # texture minimizing function (used when the pixel being textured maps to an area > than one texture element)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR) # texture magnification function (used when the pixel being textured maps to an area <= than one texture element)

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT) # integer part of coordinate s is ignored => repeating pattern
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT) # same for coordinate t
    
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data) # sends raw pixels to GPU memory
    return tex_id

# load heightmap: grayscale image where brightness = height (white = high, black = low); returns (width, height, 2D list of 0..255) or None
def load_heightmap(path):
    if not os.path.exists(path):
        print(f"Heightmap {path} not found; using procedural relief.")
        return None
    img = Image.open(path)
    img = img.convert("L")  # lightness channel - grayscale
    w, h = img.size[0], img.size[1]
    data = list(img.getdata())
    pixels = [data[row * w : (row + 1) * w] for row in range(h)] # save image coordinates in a matrix
    return (w, h, pixels)

# sample heightmap at normalized (u,v) in [0,1]; returns height in [0..1] (image row 0 is top so v is flipped for OpenGL-style Y)
def sample_heightmap(hm_width, hm_height, hm_pixels, u, v):
    u = max(0, min(1, u))
    v = max(0, min(1, v))
    
    col = int(u * (hm_width - 1) + 0.5) # transform u in a pixel coordinate
    row = int((1 - v) * (hm_height - 1) + 0.5) # transform v (inversed) in a pixel coordinate
    
    row = max(0, min(hm_height - 1, row))
    col = max(0, min(hm_width - 1, col))
    
    return hm_pixels[row][col] / 255.0  # [0..1]
