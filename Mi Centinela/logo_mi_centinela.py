# Arma el logo "Mi Centinela" (escudo con ojo + texto) en la escena actual.
# Uso (desde la raíz del proyecto): python3 blender_bridge/send.py "Mi Centinela/logo_mi_centinela.py"
import bpy
import bmesh
import math
from mathutils import Vector

FONT_REG = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"

COL = {
    "fondo": "#dde1e6",
    "borde": "#2f72d6",
    "esc_izq": "#2a66c9",
    "esc_der": "#10306a",
    "ojo": "#ffffff",
    "iris": "#2f7de1",
    "pupila": "#0c2654",
    "mi": "#4b5c72",
    "centinela": "#14315c",
    "punto": "#2f7de1",
}


def lin(hexstr):
    h = hexstr.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def bsdf_de(mat):
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None) or nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return bsdf


def material(nombre, color, rough=0.45):
    mat = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    mat.use_nodes = True
    bsdf = bsdf_de(mat)
    bsdf.inputs["Base Color"].default_value = lin(color)
    bsdf.inputs["Roughness"].default_value = rough
    return mat


def material_dos_tonos(nombre, izq, der):
    """Mitad izquierda clara, mitad derecha oscura (corte en X del objeto)."""
    mat = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = bsdf_de(mat)
    bsdf.inputs["Roughness"].default_value = 0.45
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].color = lin(izq)
    ramp.color_ramp.elements[1].position = 0.5
    ramp.color_ramp.elements[1].color = lin(der)
    nt.links.new(coord.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["X"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def objeto_plano(nombre, puntos, z, grosor, mat, bevel=0.0):
    """Crea una figura 2D rellena (lista de (x, y)) extruida hacia +Z."""
    me = bpy.data.meshes.new(nombre)
    bm = bmesh.new()
    verts = [bm.verts.new((x, y, 0)) for x, y in puntos]
    bm.faces.new(verts)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(nombre, me)
    bpy.context.collection.objects.link(ob)
    ob.location.z = z
    sol = ob.modifiers.new("Grosor", "SOLIDIFY")
    sol.thickness = grosor
    sol.offset = 1.0
    if bevel:
        bev = ob.modifiers.new("Bisel", "BEVEL")
        bev.width = bevel
        bev.segments = 3
        bev.limit_method = "ANGLE"
    ob.data.materials.append(mat)
    return ob


def contorno_escudo(escala=1.0, n=40):
    """Escudo: borde superior con leve curva, lados rectos y punta abajo."""
    w, top, mid, bot = 0.5, 0.55, 0.05, -0.68
    pts = []
    # borde superior (de derecha a izquierda), baja un poco en el centro
    for i in range(n + 1):
        t = i / n
        x = w - 2 * w * t
        y = top - 0.05 * math.sin(math.pi * t)
        pts.append((x, y))
    # lado izquierdo hasta "mid"
    pts.append((-w, mid))
    # curva cuadrática izquierda hasta la punta
    def quad(p0, c, p1, t):
        return tuple((1 - t) ** 2 * p0[k] + 2 * (1 - t) * t * c[k] + t ** 2 * p1[k] for k in (0, 1))
    for i in range(1, n + 1):
        pts.append(quad((-w, mid), (-w, -0.42), (0, bot), i / n))
    for i in range(1, n):
        pts.append(quad((0, bot), (w, -0.42), (w, mid), i / n))
    pts.append((w, mid))
    cy = -0.02
    return [(x * escala, (y - cy) * escala + cy) for x, y in pts]


def contorno_ojo(ancho=0.34, alto=0.2, n=32):
    pts = []
    for i in range(n + 1):
        x = ancho - 2 * ancho * i / n
        pts.append((x, alto * (1 - (x / ancho) ** 2)))
    for i in range(1, n):
        x = -ancho + 2 * ancho * i / n
        pts.append((x, -alto * (1 - (x / ancho) ** 2)))
    return pts


def circulo(r, cx=0.0, cy=0.0, n=48):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def texto(nombre, cuerpo, fuente, size, mat, x, y, z=0.0, grosor=0.03):
    cu = bpy.data.curves.new(nombre, "FONT")
    cu.body = cuerpo
    cu.font = bpy.data.fonts.load(fuente, check_existing=True)
    cu.size = size
    cu.extrude = grosor
    cu.align_y = "BOTTOM_BASELINE"
    ob = bpy.data.objects.new(nombre, cu)
    bpy.context.collection.objects.link(ob)
    ob.location = (x, y, z + grosor)
    ob.data.materials.append(mat)
    return ob


def ancho_texto(cuerpo, fuente, size, caja=False):
    ob = texto("_medida", cuerpo, fuente, size, material("_tmp", "#000000"), 0, 0)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    pts = [ev.matrix_world @ Vector(c) for c in ev.bound_box]
    bpy.data.objects.remove(ob)
    if caja:
        return min(p.x for p in pts), max(p.x for p in pts), max(p.y for p in pts)
    return max(p.x for p in pts)


# ---------------------------------------------------------------- escena limpia
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob)
col = bpy.context.collection

# ---------------------------------------------------------------- escudo
grupo = bpy.data.objects.new("Logo", None)
col.objects.link(grupo)

partes = [
    objeto_plano("Escudo_borde", contorno_escudo(1.0), 0.0, 0.08, material("Borde", COL["borde"]), bevel=0.012),
    objeto_plano("Escudo", contorno_escudo(0.88), 0.0, 0.11, material_dos_tonos("Escudo_2tonos", COL["esc_izq"], COL["esc_der"]), bevel=0.01),
    objeto_plano("Ojo", contorno_ojo(), 0.11, 0.02, material("Ojo", COL["ojo"], 0.3)),
    objeto_plano("Iris", circulo(0.13, 0, 0), 0.13, 0.015, material("Iris", COL["iris"], 0.3)),
    objeto_plano("Pupila", circulo(0.065, 0, 0), 0.145, 0.015, material("Pupila", COL["pupila"], 0.2)),
    objeto_plano("Brillo", circulo(0.025, 0.035, 0.04, 24), 0.16, 0.01, material("Ojo", COL["ojo"], 0.3)),
]
# ojo un poco arriba del centro del escudo
for p in partes[2:]:
    p.location.y = 0.03

# ---------------------------------------------------------------- texto
SIZE = 0.78
BASE = -0.27
X0 = 0.78
t_mi = texto("Texto_Mi", "Mi", FONT_REG, SIZE, material("Mi", COL["mi"]), X0, BASE)
x_cent = X0 + ancho_texto("Mi", FONT_REG, SIZE) + 0.2
# "ı" sin punto: el punto va aparte, en azul
cuerpo = "Centınela"
t_cent = texto("Texto_Centinela", cuerpo, FONT_BOLD, SIZE, material("Centinela", COL["centinela"]), x_cent, BASE)

# centro del trazo de la "ı" y altura del punto según la "i" normal
_, x_fin_i, _ = ancho_texto("Centı", FONT_BOLD, SIZE, caja=True)
i_min, i_max, i_top = ancho_texto("i", FONT_BOLD, SIZE, caja=True)
R_PUNTO = 0.055
cx_i = x_cent + x_fin_i - (i_max - i_min) / 2
punto = objeto_plano("Punto_i", circulo(R_PUNTO, 0, 0), 0.0, 0.03, material("Punto", COL["punto"]))
punto.location = (cx_i, BASE + i_top - R_PUNTO + 0.035, 0.0)

partes += [t_mi, t_cent, punto]
for p in partes:
    p.parent = grupo

# ---------------------------------------------------------------- mundo, luz, cámara
scene = bpy.context.scene
world = scene.world or bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
wnt = world.node_tree
fondo = next((n for n in wnt.nodes if n.type == "BACKGROUND"), None)
if fondo is None:
    fondo = wnt.nodes.new("ShaderNodeBackground")
    wout = next((n for n in wnt.nodes if n.type == "OUTPUT_WORLD"), None) or wnt.nodes.new("ShaderNodeOutputWorld")
    wnt.links.new(fondo.outputs["Background"], wout.inputs["Surface"])
fondo.inputs["Color"].default_value = lin(COL["fondo"])
fondo.inputs["Strength"].default_value = 1.0

sol_data = bpy.data.lights.new("Sol", "SUN")
sol_data.energy = 0.6
sol_data.angle = math.radians(10)
sol = bpy.data.objects.new("Sol", sol_data)
col.objects.link(sol)
sol.rotation_euler = (math.radians(25), math.radians(-20), 0)

centro_x = (-0.55 + x_cent + ancho_texto(cuerpo, FONT_BOLD, SIZE)) / 2
cam_data = bpy.data.cameras.new("Camara")
cam_data.type = "ORTHO"
cam_data.ortho_scale = (x_cent + ancho_texto(cuerpo, FONT_BOLD, SIZE) + 0.55) * 1.12
cam = bpy.data.objects.new("Camara", cam_data)
col.objects.link(cam)
cam.location = (centro_x, 0.0, 10)
scene.camera = cam

scene.render.resolution_x = 1900
scene.render.resolution_y = 500
scene.view_settings.view_transform = "Standard"
scene.render.film_transparent = False

result = {"centro_x": round(centro_x, 3), "x_centinela": round(x_cent, 3), "punto_i": round(cx_i, 3)}
