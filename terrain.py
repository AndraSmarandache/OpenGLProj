import math
from OpenGL.GL import *
from textures import sample_heightmap

def terrain_height(x, z): 
    """
    Creates terrain by Gaussian Hills and layeres noise. The Gaussian Hills
    are created using Bell's Curve: A * e^(-(distance^2/spread))
    We also use procedural noise for bumpy, natural textures, with pattern:
    amplitude * sin(x * frequency) * cos(x * frequency)
    Notice we also use offsets to 'scramble' the waves so they look more natural
    """
    hill1 = 2.2 * math.exp(-((x - 1.5) ** 2 + (z + 5) ** 2) / 8.0) # hill centered at x = 1.5, z = -5, peak height of 2.2, spread of 8
    hill2 = 1.8 * math.exp(-((x + 2) ** 2 + (z + 2) ** 2) / 6.0)
    hill3 = 1.2 * math.exp(-((x - 2.5) ** 2 + (z + 7) ** 2) / 10.0)
    
    noise1 = 0.5 * math.sin(x * 0.4) * math.cos(z * 0.4) # base noise - general unevenness
    noise2 = 0.3 * math.sin(x * 0.9 + 1.3) * math.cos(z * 0.85 + 0.7) # medium noise - small mounds and dips
    noise3 = 0.2 * math.sin(2.1 * x + 2) * math.cos(1.6 * z + 1) # high noise - rougher texture
    
    return max(0.0, hill1 + hill2 + hill3 + noise1 + noise2 + noise3 + 0.6) # adds hills and noise woth an offset to 'lift' the terrain; if sum is negative it keeps the ground flat (returns 0)

def _relief_normal(x, z, step, h_func):
    """
    Calculates the surface normal at point (x,z) from finite differences (neighbors) so lighting looks correct on the relief
    OpenGL uses (nx ny, nz) values to calculate shadows; if normal points towards the light source, the texture looks brighter, and vice-versa
    """
    dx, dz = step * 0.5, step * 0.5 # tiny offsets with which to sample the neighboring heights
   
    hx0 = h_func(x - dx, z) # left neighbor
    hx1 = h_func(x + dx, z) # right neighbor
    hz0 = h_func(x, z - dz) # front neighbor
    hz1 = h_func(x, z + dz) # back neighbor
   
    tx = (hx1 - hx0) / (2 * dx) # slope (gardient) for x-axis
    tz = (hz1 - hz0) / (2 * dz) # gradient for z-axis
   
    nx, ny, nz = -tx, 1.0, -tz # normal vector - the normal needs to tilt to the opposite of the slope to stay perpendicular
    L = math.sqrt(nx * nx + ny * ny + nz * nz) # Pythagorean theorem to calculate the current normal arrow length
    if L > 1e-6: # safety check - avoid division by 0
        nx, ny, nz = nx/L, ny/L, nz/L # make arrow of length 1 (brightness is calculated by the dot product of the normal vector and light vector - they have be of length 1 so the result is just cos(angle))
    return (nx, ny, nz)

def draw_relief(texture_id, x_min = -5.0, x_max = 5.0, z_min = -10.0, z_max = 0.0):
    def height_mapped(x, z):
        x_can = -5.0 + (x - x_min) / (x_max - x_min) * 10.0
        z_can = -10.0 + (z - z_min) / (z_max - z_min) * 10.0
        return terrain_height(x_can, z_can)
    glColor3f(1.0, 1.0, 1.0)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    n_x, n_z = 36, 40 # how many squares (divisions) to make up the relief
    
    # steps necessary to cover the relief surface
    step_x = (x_max - x_min) / n_x # width
    step_z = (z_max - z_min) / n_z # length
    
    for i in range(n_x): # for every width division (columns)
        x = x_min + i * step_x # x coordinate of left edge of the div
        x2 = x_min + (i + 1) * step_x # x coordinate of right edge of the div
        glBegin(GL_TRIANGLE_STRIP) # start a strip of triangles to connect x and x2
        
        for j in range(n_z + 1): # for every length division (rows)
            z = z_min + j * step_z # current z coordinate
            
            # height: find the y for both edges of the strip; subtract 1 to align base of hill to ground level
            y1 = -1.0 + height_mapped(x, z)
            y2 = -1.0 + height_mapped(x2, z)
            
            # lighting: calculate normal vector for correct shading
            n1 = _relief_normal(x, z, step_x, height_mapped)
            n2 = _relief_normal(x2, z, step_x, height_mapped)
            
            # texture: convert to UV coordinates (0 to 1 scale), and multiply by 2 to repeat the texture so it doesn't look stretched
            u1 = (x - x_min) / (x_max - x_min) * 2
            u2 = (x2 - x_min) / (x_max - x_min) * 2
            v = (z - z_min) / (z_max - z_min) * 2
            
            # drawing: send the normals, coords and 3D position to the GPU
            # this crates a 'zig-zag' pattern that fills the triag strip:  GL_TRIANGLE_STRIP connects the last 2 points so the new ones, creating 2 triangles
            """
            [l0] ---- [r0]
            | \\  trig2 |
            |    \\     |
            | trig1 \\  |
            [l1] ---- [r1]
            """
            glNormal3f(*n1); glTexCoord2f(u1, v); glVertex3f(x, y1, z) # left point
            glNormal3f(*n2); glTexCoord2f(u2, v); glVertex3f(x2, y2, z) # right point
        glEnd() # finish the current column strip
        
    glDisable(GL_TEXTURE_2D) # turn off texturing to not accidentally affect other objects 

# relief from a heightmap image (grayscale: white = high, black = low) - logic similar to draw_relief
def draw_relief_heightmap(hm_data, texture_id, height_scale = 3.0, x_min = -5.0, x_max = 5.0, z_min = -10.0, z_max = 0.0):
    hm_width, hm_height, hm_pixels = hm_data
    n_x, n_z = 36, 40
    step_x = (x_max - x_min) / n_x
    step_z = (z_max - z_min) / n_z

    def height_at(x, z):
        u = (x - x_min) / (x_max - x_min)
        v = (z - z_min) / (z_max - z_min)
        return height_scale * sample_heightmap(hm_width, hm_height, hm_pixels, u, v)

    glColor3f(1.0, 1.0, 1.0)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    for i in range(n_x):
        x = x_min + i * step_x
        x2 = x_min + (i + 1) * step_x
        glBegin(GL_TRIANGLE_STRIP)
        
        for j in range(n_z + 1):
            z = z_min + j * step_z
            
            y1 = -1.0 + height_at(x, z)
            y2 = -1.0 + height_at(x2, z)
            
            n1 = _relief_normal(x, z, step_x, height_at)
            n2 = _relief_normal(x2, z, step_x, height_at)
            
            u1 = (x - x_min) / (x_max - x_min) * 2
            u2 = (x2 - x_min) / (x_max - x_min) * 2
            v = (z - z_min) / (z_max - z_min) * 2
            
            glNormal3f(*n1); glTexCoord2f(u1, v); glVertex3f(x, y1, z)
            glNormal3f(*n2); glTexCoord2f(u2, v); glVertex3f(x2, y2, z)
        glEnd()
    glDisable(GL_TEXTURE_2D)
