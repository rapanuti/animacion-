# Arma el logo de Rapanuti (ícono "R" + palabra "Rapanuti") en 3D en una escena nueva.
# Uso (desde la raíz del proyecto): python3 blender_bridge/send.py "Rapanuti/logo_rapanuti.py"
# Medidas tomadas de referencia.png (1600 x 475 px): 100 px = 1 unidad de Blender.
# Origen: borde izquierdo del ícono, sobre la línea base del texto.
import bpy
import math
import os
from mathutils import Vector

CARPETA = "/home/elvira/Documentos/Claude/animacion-/Rapanuti"
FUENTE = os.path.join(CARPETA, "fuentes", "Montserrat-Medium.ttf")

GROSOR = 0.06        # relieve (profundidad) del logo
BISEL = 0.007        # borde redondeado que atrapa la luz

# Temas. "logo" es el color de marca; "base" es el color del material (lineal) calibrado para
# que, con la luz de la escena, la cara del logo se vea exactamente del color de marca
# (los biseles quedan más claros u oscuros: eso da el efecto 3D). "luz" multiplica las luces.
TEMAS = {
    "claro":  {"logo": "#132136", "fondo": "#f4f6f8", "base": (0.00098, 0.01308, 0.0555), "luz": 1.0},
    "oscuro": {"logo": "#f4f6fa", "fondo": "#0e1726", "base": (0.88805, 0.90479, 0.94734), "luz": 2.0},
}
LUCES = {"Luz_principal": 260, "Luz_relleno": 60, "ambiente": 0.25}

# ---------------------------------------------------------------- geometría del ícono (en píxeles)
# Segmentos: ("L", (x, y)) línea hasta el punto; ("A", (cx, cy), r, a0, a1) arco (grados, y hacia abajo).
# Todos los cortes diagonales tienen la misma inclinación (~40°).
PIEZA_R = [
    ("L", (536, 193)), ("L", (631, 193)),
    ("A", (631, 210), 17, -90, 0),              # esquina superior derecha
    ("L", (648, 223)),
    ("A", (629.5, 223), 18.5, 0, 90),           # curva inferior de la panza
    ("L", (618.5, 241.5)),
    ("L", (648, 266.5)), ("L", (627.5, 266.5)),  # pierna diagonal
    ("L", (598, 241.5)),
    ("L", (577, 223.5)),                        # corte de la barra media
    ("L", (628, 223.5)),
    ("A", (628, 220.5), 3, 90, 0),
    ("L", (631, 213)),
    ("A", (628, 213), 3, 0, -90),
    ("L", (556, 210)),                          # corte de la barra superior
]
PILAR = [("L", (563, 223.5)), ("L", (589, 245.5)), ("L", (589, 277)), ("L", (563, 263.5))]

X0, BASE = 536, 266.5            # origen en píxeles
TEXTO_X = 681                    # borde izquierdo de la "R" del texto
TEXTO_ANCHO = 1059 - 681         # de la "R" a la "i"
ALTO_MAYUS = 266.5 - 203         # altura de la "R" del texto


def a_unidades(x, y):
    return (x - X0) / 100, (BASE - y) / 100


def puntos(segmentos, pasos_por_grado=0.25):
    pts = []
    for s in segmentos:
        if s[0] == "L":
            pts.append(s[1])
        else:
            _, (cx, cy), r, a0, a1 = s
            n = max(2, int(abs(a1 - a0) * pasos_por_grado))
            for i in range(n + 1):
                a = math.radians(a0 + (a1 - a0) * i / n)
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return [a_unidades(x, y) for x, y in pts]


def lin(hexstr):
    h = hexstr.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def material_logo():
    mat = bpy.data.materials.new("Logo")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = 0.4
    bsdf.inputs["Specular IOR Level"].default_value = 0.25
    bsdf.inputs["Coat Weight"].default_value = 0.12
    bsdf.inputs["Coat Roughness"].default_value = 0.15
    return mat


def relieve(cu):
    cu.extrude = GROSOR / 2
    cu.bevel_depth = BISEL
    cu.bevel_resolution = 3
    cu.offset = -BISEL           # el bisel no engorda el contorno


def pieza(nombre, segmentos, mat):
    cu = bpy.data.curves.new(nombre, "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    sp = cu.splines.new("POLY")
    pts = puntos(segmentos)
    sp.points.add(len(pts) - 1)
    for p, (x, y) in zip(sp.points, pts):
        p.co = (x, y, 0, 1)
    sp.use_cyclic_u = True
    relieve(cu)
    ob = bpy.data.objects.new(nombre, cu)
    bpy.context.collection.objects.link(ob)
    ob.location.z = GROSOR / 2
    cu.materials.append(mat)
    return ob


def caja_x(ob):
    bpy.context.view_layer.update()
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    xs = [(ob.matrix_world @ v.co).x for v in ev.to_mesh().vertices]
    ys = [(ob.matrix_world @ v.co).y for v in ev.to_mesh().vertices]
    ev.to_mesh_clear()
    return min(xs), max(xs), min(ys), max(ys)


def aplicar_tema(tema):
    """Cambia colores del logo y del fondo: 'claro' o 'oscuro'."""
    t = TEMAS[tema]
    bsdf = next(n for n in bpy.data.materials["Logo"].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*t["base"], 1.0)
    nodos = bpy.context.scene.world.node_tree.nodes
    nodos["Fondo_camara"].inputs["Color"].default_value = lin(t["fondo"])
    nodos["Luz_ambiente"].inputs["Strength"].default_value = LUCES["ambiente"] * t["luz"]
    for nombre in ("Luz_principal", "Luz_relleno"):
        bpy.data.objects[nombre].data.energy = LUCES[nombre] * t["luz"]
    bpy.context.scene["tema"] = tema


# ---------------------------------------------------------------- escena nueva
bpy.ops.wm.read_homefile(use_empty=True)
scene = bpy.context.scene
scene.name = "Rapanuti"
mat = material_logo()

raiz = bpy.data.objects.new("Logo_Rapanuti", None)
bpy.context.collection.objects.link(raiz)

icono = bpy.data.objects.new("Icono_R", None)
bpy.context.collection.objects.link(icono)
icono.parent = raiz
for p in (pieza("R_principal", PIEZA_R, mat), pieza("R_pilar", PILAR, mat)):
    p.parent = icono

# ---------------------------------------------------------------- texto en Montserrat Medium
fuente = bpy.data.fonts.load(FUENTE, check_existing=True)
fuente.pack()
cu = bpy.data.curves.new("Rapanuti", "FONT")
cu.body = "Rapanuti"
cu.font = fuente
cu.align_y = "BOTTOM_BASELINE"
relieve(cu)
cu.materials.append(mat)
texto = bpy.data.objects.new("Texto_Rapanuti", cu)
bpy.context.collection.objects.link(texto)
texto.parent = raiz
texto.location.z = GROSOR / 2

# tamaño: misma altura de mayúscula que la "R" del original
cu.body = "R"
_, _, y0, y1 = caja_x(texto)
cu.size = cu.size * (ALTO_MAYUS / 100) / (y1 - y0)
cu.body = "Rapanuti"
# espaciado: las letras del original están más juntas que el valor normal de la fuente
# (tracking uniforme de ~ -3,5 %). Se usa el kerning por letra (entero) y un retoque mínimo
# del espaciado general para llegar exacto al ancho del original sin deformar el reparto.
objetivo = TEXTO_ANCHO / 100


def ancho_con(kern, espacio):
    for f in cu.body_format:
        f.kerning = kern
    cu.space_character = espacio
    xa, xb, _, _ = caja_x(texto)
    return xb - xa


kern = min(range(-8, 1), key=lambda k: abs(ancho_con(k, 1.0) - objetivo))
bajo, alto = 0.95, 1.05
for _ in range(20):
    medio = (bajo + alto) / 2
    if ancho_con(kern, medio) > objetivo:
        alto = medio
    else:
        bajo = medio
xa, _, _, _ = caja_x(texto)
texto.location.x += (TEXTO_X - X0) / 100 - xa

# ---------------------------------------------------------------- mundo: fondo para la cámara + luz suave
world = bpy.data.worlds.new("Mundo")
scene.world = world
world.use_nodes = True
wnt = world.node_tree
for n in list(wnt.nodes):
    wnt.nodes.remove(n)
camino = wnt.nodes.new("ShaderNodeLightPath")
luz_amb = wnt.nodes.new("ShaderNodeBackground")
luz_amb.name = "Luz_ambiente"
luz_amb.inputs["Color"].default_value = (1, 1, 1, 1)
luz_amb.inputs["Strength"].default_value = 0.25
fondo = wnt.nodes.new("ShaderNodeBackground")
fondo.name = "Fondo_camara"
mezcla = wnt.nodes.new("ShaderNodeMixShader")
wout = wnt.nodes.new("ShaderNodeOutputWorld")
wnt.links.new(camino.outputs["Is Camera Ray"], mezcla.inputs["Fac"])
wnt.links.new(luz_amb.outputs["Background"], mezcla.inputs[1])
wnt.links.new(fondo.outputs["Background"], mezcla.inputs[2])
wnt.links.new(mezcla.outputs["Shader"], wout.inputs["Surface"])

# luz principal desde arriba a la izquierda (los biseles de arriba brillan, los de abajo hacen sombra)
CENTRO = Vector((2.6, 0.25, 0.0))
for nombre, energia, pos, tam in (("Luz_principal", 260, (-1.5, 4.5, 5.5), 5),
                                  ("Luz_relleno", 60, (7.0, -2.5, 6.0), 8)):
    ld = bpy.data.lights.new(nombre, "AREA")
    ld.energy = energia
    ld.size = tam
    lo = bpy.data.objects.new(nombre, ld)
    bpy.context.collection.objects.link(lo)
    lo.location = pos
    lo.rotation_euler = (lo.location - CENTRO).to_track_quat("Z", "Y").to_euler()

# ---------------------------------------------------------------- cámara frontal ortográfica
_, xmax, _, _ = caja_x(texto)
xmin, ymin, ymax = -0.0, -0.105, 0.735
margen = 0.35
cam_data = bpy.data.cameras.new("Camara")
cam_data.type = "ORTHO"
cam_data.ortho_scale = (xmax - xmin) + 2 * margen
cam = bpy.data.objects.new("Camara", cam_data)
bpy.context.collection.objects.link(cam)
cam.location = ((xmin + xmax) / 2, (ymin + 0.735) / 2 - 0.02, 10)
scene.camera = cam
scene.render.resolution_x = 2400
scene.render.resolution_y = int(2400 * ((ymax - ymin) + 2 * margen) / cam_data.ortho_scale)
scene.render.resolution_y += scene.render.resolution_y % 2
scene.view_settings.view_transform = "Standard"
scene.render.engine = "BLENDER_EEVEE"

aplicar_tema("claro")
os.makedirs(os.path.join(CARPETA, "render"), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(CARPETA, "rapanuti.blend"))
result = {"tamano_texto": round(cu.size, 4), "kerning": kern, "espaciado": round(cu.space_character, 4),
          "texto_x": [round(v, 3) for v in caja_x(texto)[:2]], "res": (scene.render.resolution_x, scene.render.resolution_y)}
