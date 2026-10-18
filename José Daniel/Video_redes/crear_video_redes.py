# Video vertical para redes sociales (12 s, 1080 x 1920): José Daniel camina por un paisaje,
# saluda, invita a seguirlo en sus redes y termina con "Sígueme en YouTube".
# Copia el personaje de jose_daniel.blend (el original no se modifica) y guarda video_redes.blend.
# Uso (desde la raíz del proyecto): python3 blender_bridge/send.py "José Daniel/Video_redes/crear_video_redes.py"
import bmesh
import bpy
import math
import os
import random
from mathutils import Vector

AQUI = "/home/elvira/Documentos/Claude/animacion-/José Daniel/Video_redes"
PERSONAJE = os.path.join(os.path.dirname(AQUI), "jose_daniel.blend")
FUENTE = os.path.join(AQUI, "fuentes", "Montserrat-Bold.ttf")

FPS, FIN = 24, 288                    # 12 segundos
CANAL = ""                            # p. ej. "@josedaniel": aparece bajo el botón de YouTube
TEXTO_SALUDO = ("¡Hola! Sígueme", "en todas mis redes")
REDES = (("Instagram", "#e1306c"), ("TikTok", "#111111"), ("Facebook", "#1877f2"))
random.seed(7)


def lin(hexstr):
    h = hexstr.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def nodos_limpios(mat):
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    return nt


def mat_color(nombre, color, rough=0.7):
    mat = bpy.data.materials.new(nombre)
    nt = nodos_limpios(mat)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = lin(color)
    bsdf.inputs["Roughness"].default_value = rough
    return mat


def mat_emision(nombre, color):
    """Color plano que no cambia con la luz (para textos y botones)."""
    mat = bpy.data.materials.new(nombre)
    nt = nodos_limpios(mat)
    em = nt.nodes.new("ShaderNodeEmission")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    em.inputs["Color"].default_value = lin(color)
    return mat


def mat_pasto():
    mat = bpy.data.materials.new("Pasto")
    nt = nodos_limpios(mat)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    ruido = nt.nodes.new("ShaderNodeTexNoise")
    ruido.inputs["Scale"].default_value = 0.08
    rampa = nt.nodes.new("ShaderNodeValToRGB")
    rampa.color_ramp.elements[0].color = lin("#4f9a3c")
    rampa.color_ramp.elements[1].color = lin("#7cc35a")
    nt.links.new(ruido.outputs["Fac"], rampa.inputs["Fac"])
    nt.links.new(rampa.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = 0.9
    return mat


_mallas = {}


def _malla_base(tipo, lados):
    """Una malla por tipo de forma, compartida por todos los objetos que la usan (más liviano)."""
    clave = (tipo, lados)
    if clave not in _mallas:
        me = bpy.data.meshes.new(f"forma_{tipo}_{lados}")
        bm = bmesh.new()
        if tipo == "esfera":
            bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=1)
        elif tipo == "cono":
            bmesh.ops.create_cone(bm, cap_ends=True, segments=lados, radius1=1, radius2=0, depth=2)
        elif tipo == "cilindro":
            bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=1, radius2=1, depth=2)
        elif tipo == "plano":
            bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
        bm.to_mesh(me)
        bm.free()
        if tipo in ("esfera", "cilindro"):
            for pol in me.polygons:
                pol.use_smooth = True
        _mallas[clave] = me
    return _mallas[clave]


def malla(nombre, tipo, loc, escala=(1, 1, 1), mat=None, rot=(0, 0, 0), lados=8):
    ob = bpy.data.objects.new(nombre, _malla_base(tipo, lados))
    scene.collection.objects.link(ob)
    ob.location = loc
    ob.scale = escala
    ob.rotation_euler = [math.radians(a) for a in rot]
    _poner_material(ob, mat)
    return ob


def _poner_material(ob, mat):
    if not mat:
        return
    if not ob.data.materials:
        ob.data.materials.append(None)
    ob.material_slots[0].link = "OBJECT"
    ob.material_slots[0].material = mat


# ---------------------------------------------------------------- escena nueva + José Daniel copiado
bpy.ops.wm.read_homefile(use_empty=True)
scene = bpy.context.scene
scene.name = "Video_redes"
with bpy.data.libraries.load(PERSONAJE, link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n not in ("Camara", "Sol", "Referencia")]
for ob in dst.objects:
    scene.collection.objects.link(ob)
    ob.animation_data_clear()          # se borra la animación "Reposo"; aquí se hace una nueva
D = bpy.data.objects
jose, cabeza, cuerpo, boca = D["Jose_Daniel"], D["Control_Cabeza"], D["Cuerpo"], D["Boca"]
ojos = [D["Ojo_izq"], D["Ojo_der"]]

# ---------------------------------------------------------------- paisaje
pasto = mat_pasto()
suelo = malla("Suelo", "plano", (0, 60, 0), (400, 400, 1), pasto)
malla("Sendero", "plano", (0, 30, 0.01), (3.2, 110, 1), mat_color("Tierra", "#d4b07a", 0.95))

verdes = [mat_color(f"Colina_{i}", c, 0.95) for i, c in enumerate(("#5fa84a", "#4d9440", "#6db654"))]
for i, (x, y, rx, rz) in enumerate(((-40, 95, 38, 12), (35, 105, 42, 15), (-5, 130, 60, 20), (70, 140, 50, 18))):
    malla(f"Colina_{i}", "esfera", (x, y, -rz * 0.25), (rx, rx * 0.6, rz), verdes[i % 3])
montana = mat_color("Montana", "#8fb3d9", 0.95)
for i, (x, rx, rz) in enumerate(((-90, 60, 40), (0, 80, 55), (95, 70, 45))):
    malla(f"Montana_{i}", "cono", (x, 230, rz * 0.4), (rx, rx * 0.5, rz), montana, lados=6)

tronco = mat_color("Tronco", "#7a5230", 0.9)
hojas = [mat_color(f"Hojas_{i}", c, 0.85) for i, c in enumerate(("#2f7d32", "#3d8f3a", "#256b2a"))]
for i in range(46):
    x = random.choice((-1, 1)) * random.uniform(5, 38)
    y = random.uniform(-2, 85)
    s = random.uniform(0.8, 1.5)
    malla(f"Tronco_{i}", "cilindro", (x, y, 1.0 * s), (0.28 * s, 0.28 * s, 1.0 * s), tronco)
    malla(f"Copa_{i}", "cono", (x, y, 3.8 * s), (1.7 * s, 1.7 * s, 2.2 * s), hojas[i % 3])
arbusto = mat_color("Arbusto", "#3f9a3f", 0.85)
flores = [mat_color(f"Flor_{i}", c, 0.5) for i, c in enumerate(("#ff6b9a", "#ffd23f", "#ffffff", "#b388ff"))]
for i in range(40):
    lado = random.choice((-1, 1))
    y = random.uniform(-3, 60)
    malla(f"Flor_{i}", "esfera", (lado * random.uniform(2.0, 3.5), y, 0.15), (0.16, 0.16, 0.16), flores[i % 4])
for i in range(14):
    lado = random.choice((-1, 1))
    s = random.uniform(0.7, 1.3)
    malla(f"Arbusto_{i}", "esfera", (lado * random.uniform(3.8, 6), random.uniform(0, 55), 0.5 * s),
          (1.1 * s, 1.1 * s, 0.8 * s), arbusto)
nube = mat_color("Nube", "#ffffff", 1.0)
for i, (x, y, z) in enumerate(((-25, 120, 34), (18, 140, 40), (45, 110, 30), (-55, 150, 44), (5, 170, 52))):
    for j in range(5):
        r = random.uniform(3.5, 6)
        malla(f"Nube_{i}_{j}", "esfera", (x + j * 4.5 - 9, y + random.uniform(-2, 2), z + random.uniform(-1, 2)),
              (r, r * 0.8, r * 0.7), nube)

# cielo: degradado del horizonte (claro) al cenit (azul)
world = bpy.data.worlds.new("Cielo")
scene.world = world
wn = nodos_limpios(world)
coord = wn.nodes.new("ShaderNodeTexCoord")
sep = wn.nodes.new("ShaderNodeSeparateXYZ")
rampa = wn.nodes.new("ShaderNodeValToRGB")
rampa.color_ramp.elements[0].color = lin("#d8eeff")
rampa.color_ramp.elements[1].position = 0.45
rampa.color_ramp.elements[1].color = lin("#4a9be8")
fondo = wn.nodes.new("ShaderNodeBackground")
fondo.inputs["Strength"].default_value = 1.0
wout = wn.nodes.new("ShaderNodeOutputWorld")
wn.links.new(coord.outputs["Generated"], sep.inputs[0])
wn.links.new(sep.outputs["Z"], rampa.inputs["Fac"])
wn.links.new(rampa.outputs["Color"], fondo.inputs["Color"])
wn.links.new(fondo.outputs["Background"], wout.inputs["Surface"])

sol = bpy.data.objects.new("Sol", bpy.data.lights.new("Sol", "SUN"))
scene.collection.objects.link(sol)
sol.data.energy = 3.2
sol.data.color = (1.0, 0.95, 0.86)
sol.data.angle = math.radians(4)
sol.location = (-12, -18, 22)
sol.rotation_euler = (Vector((0, 0, 0)) - sol.location).to_track_quat("-Z", "Y").to_euler()

# ---------------------------------------------------------------- cámara vertical
cam = bpy.data.objects.new("Camara", bpy.data.cameras.new("Camara"))
scene.collection.objects.link(cam)
cam.data.lens = 35
cam.data.clip_end = 1000
scene.camera = cam
MIRA = Vector((0, 0, 3.0))


def cam_en(y, frame):
    cam.location = (0.6, y, 2.6)
    cam.rotation_euler = (MIRA - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.keyframe_insert("location", frame=frame)
    cam.keyframe_insert("rotation_euler", frame=frame)


cam_en(-15.5, 1)
cam_en(-13.0, 150)

# ---------------------------------------------------------------- animación de José
g = math.radians
PASO = 10                              # cuadros por paso
FIN_CAMINATA = 120


def avance(t):                         # 0..1 -> recorrido, frenando al final
    return t if t < 0.75 else 0.75 + 0.25 * math.sin((t - 0.75) / 0.25 * math.pi / 2)


for f in range(1, FIN_CAMINATA + 1):
    t = (f - 1) / (FIN_CAMINATA - 1)
    fase = math.pi * (f - 1) / PASO
    jose.location = (0, 30 * (1 - avance(t)), 0.35 * abs(math.sin(fase)))
    jose.rotation_euler = (0, g(6) * math.sin(fase), 0)
    cabeza.rotation_euler = (0, g(-3) * math.sin(fase), 0)
    jose.keyframe_insert("location", frame=f)
    jose.keyframe_insert("rotation_euler", frame=f)
    cabeza.keyframe_insert("rotation_euler", frame=f)

# saltito de alegría al llegar
for f, z in ((122, 0), (128, 0.9), (134, 0)):
    jose.location = (0, 0, z)
    jose.rotation_euler = (0, 0, 0)
    jose.keyframe_insert("location", frame=f)
    jose.keyframe_insert("rotation_euler", frame=f)
for f, s in ((126, (0.95, 0.95, 1.08)), (134, (1.12, 1.12, 0.86)), (140, (1, 1, 1))):
    cuerpo.scale = s
    cuerpo.keyframe_insert("scale", frame=f)

# mira a la cámara, inclina la cabeza mientras habla
for f, r in ((140, (0, 0, 0)), (150, (g(-4), g(6), 0)), (200, (g(-2), g(-5), 0)), (232, (g(-5), 0, 0)),
             (262, (0, g(4), 0))):
    cabeza.rotation_euler = r
    cabeza.keyframe_insert("rotation_euler", frame=f)

# saltitos finales mientras late el botón de YouTube
for f, z in ((262, 0), (267, 0.55), (272, 0), (277, 0.55), (282, 0)):
    jose.location = (0, 0, z)
    jose.keyframe_insert("location", frame=f)

# parpadeos
for ojo in ojos:
    base = tuple(ojo.scale)
    cerrado = (base[0], base[1], base[2] * 0.08)
    for f0 in (60, 145, 205, 270):
        for f, s in ((f0 - 2, base), (f0, cerrado), (f0 + 3, base)):
            ojo.scale = s
            ojo.keyframe_insert("scale", frame=f)

# boca hablando: "¡Hola! Sígueme en todas mis redes" y "¡Sígueme en YouTube!"
base_boca = tuple(boca.scale)
for ini, fin in ((152, 214), (232, 260)):
    for i, f in enumerate(range(ini, fin, 3)):
        abre = 1.0 if i % 2 == 0 else random.uniform(2.2, 3.6)
        boca.scale = (base_boca[0] * (0.85 if abre > 1 else 1), base_boca[1], base_boca[2] * abre)
        boca.keyframe_insert("scale", frame=f)
    boca.scale = base_boca
    boca.keyframe_insert("scale", frame=fin)

# ---------------------------------------------------------------- textos y botones (pegados a la cámara)
fuente = bpy.data.fonts.load(FUENTE, check_existing=True)
fuente.pack()
DIST = 4.0                                            # distancia de la "capa de textos" a la cámara


def redondeado(w, h, r, pasos=6):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(pasos + 1):
            a = math.radians(a0 + 90 * i / pasos)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def figura(nombre, pts, mat, padre, z=0.0):
    cu = bpy.data.curves.new(nombre, "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, (x, y) in zip(sp.points, pts):
        p.co = (x, y, 0, 1)
    sp.use_cyclic_u = True
    cu.materials.append(mat)
    ob = bpy.data.objects.new(nombre, cu)
    scene.collection.objects.link(ob)
    ob.parent = padre
    ob.location = (0, 0, z)
    return ob


def texto(nombre, cuerpo_txt, tam, mat, padre, x=0.0, y=0.0):
    cu = bpy.data.curves.new(nombre, "FONT")
    cu.body = cuerpo_txt
    cu.font = fuente
    cu.size = tam
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.materials.append(mat)
    ob = bpy.data.objects.new(nombre, cu)
    scene.collection.objects.link(ob)
    ob.parent = padre
    ob.location = (x, y, 0.002)
    return ob


def grupo(nombre, x, y):
    e = bpy.data.objects.new(nombre, None)
    scene.collection.objects.link(e)
    e.parent = cam
    e.location = (x, y, -DIST)
    return e


def aparecer(ob, f0, dur=8, desaparecer=None):
    """Aparece con rebote (escala 0 -> 1,15 -> 1) y, si se indica, se va encogiendo."""
    claves = {1: 0, f0: 0, f0 + int(dur * 0.65): 1.15, f0 + dur: 1}
    if desaparecer:
        claves.update({desaparecer: 1, desaparecer + 3: 1.1, desaparecer + 8: 0})
    for f, s in sorted(claves.items()):
        ob.scale = (s, s, s)
        ob.keyframe_insert("scale", frame=f)


blanco, oscuro = mat_emision("UI_blanco", "#ffffff"), mat_emision("UI_texto", "#1d2433")

# globo de diálogo
globo = grupo("UI_Globo", 0, 1.22)
figura("Globo", redondeado(2.05, 0.72, 0.2), blanco, globo)
figura("Globo_cola", [(-0.12, -0.35), (0.14, -0.35), (-0.02, -0.56)], blanco, globo)
texto("Globo_linea1", TEXTO_SALUDO[0], 0.19, oscuro, globo, y=0.12)
texto("Globo_linea2", TEXTO_SALUDO[1], 0.17, oscuro, globo, y=-0.14)
aparecer(globo, 150, desaparecer=222)

# etiquetas de redes, una por una
for i, (red, color) in enumerate(REDES):
    chip = grupo(f"UI_Red_{red}", -0.7 + 0.7 * i, 0.66)
    figura(f"Red_{red}", redondeado(0.64, 0.2, 0.1), mat_emision(f"UI_{red}", color), chip)
    texto(f"Red_{red}_texto", red, 0.095, blanco, chip)
    aparecer(chip, 168 + 10 * i, desaparecer=222)

# botón final: Sígueme en YouTube
yt = grupo("UI_YouTube", 0, -1.42)
figura("YouTube_boton", redondeado(2.15, 0.44, 0.22), mat_emision("UI_rojo", "#ff0000"), yt)
figura("YouTube_play", [(-0.86, 0.09), (-0.86, -0.09), (-0.7, 0.0)], blanco, yt, z=0.002)
texto("YouTube_texto", "Sígueme en YouTube", 0.15, blanco, yt, x=0.1)
if CANAL:
    texto("YouTube_canal", CANAL, 0.1, blanco, yt, y=-0.38)
aparecer(yt, 228, dur=10)
for k, f in enumerate(range(246, FIN + 1, 6)):     # late suavemente
    s = 1.06 if k % 2 == 0 else 1.0
    yt.scale = (s, s, s)
    yt.keyframe_insert("scale", frame=f)

# ---------------------------------------------------------------- render
scene.render.fps = FPS
scene.frame_start, scene.frame_end = 1, FIN
scene.render.resolution_x, scene.render.resolution_y = 1080, 1920
scene.render.engine = "BLENDER_EEVEE"
scene.view_settings.view_transform = "Standard"
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(AQUI, "video_redes.blend"))
result = {"objetos": len(bpy.data.objects), "archivo": bpy.data.filepath}
