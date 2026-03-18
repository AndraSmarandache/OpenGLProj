import os
from OpenGL.GL import *
from PIL import Image

# helper function for loading texture
def load_texture(path):
    if not os.path.exists(path):
        print(f"Error: {path} not found!")
        return 0
    
    img = Image.open(path)
    img = img.transpose(Image.FLIP_TOP_BOTTOM) # flip for OpenGL coordinates(in OpenGl, (0, 0) is at bottom-left and we want it at top-left)
    img_data = img.convert("RGB").tobytes()
    
    tex_id = glGenTextures(1) # id number to store the new texture
    glBindTexture(GL_TEXTURE_2D, tex_id) # binds future modifications to the newly created texture
    
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR) # texture minimizing function (used when the pixel being textured maps to an area > than one texture element)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR) # texture magnification function (used when the pixel being textured maps to an area <= than one texture element)

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT) # integer part of coordinate s is ignored => repeating pattern
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT) # same for coordinate t
    
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, img.width, img.height, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data) # sends raw pixels to GPU memory
    return tex_id

# load heightmap - grayscale image where brightness = height (white = high, black = low)
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

def sample_heightmap(hm_width, hm_height, hm_pixels, u, v):
    # u,v coordinates in [0,1]; image row 0 is top so v = 0 -> row h-1 (axis is inversed)
    u = max(0, min(1, u))
    v = max(0, min(1, v))
    
    col = int(u * (hm_width - 1) + 0.5) # transform u in a pixel coordinate
    row = int((1 - v) * (hm_height - 1) + 0.5) # transform v (inversed) in a pixel coordinate
    
    row = max(0, min(hm_height - 1, row))
    col = max(0, min(hm_width - 1, col))
    
    return hm_pixels[row][col] / 255.0  # [0..1]
