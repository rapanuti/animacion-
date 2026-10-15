# Arma el personaje de José Daniel (gorra metálica, pelo rizado, ojos enojados) en una escena nueva.
# Uso (desde la raíz del proyecto): python3 blender_bridge/send.py "José Daniel/personaje_jose_daniel.py"
# Medidas tomadas de referencia.png (197 x 218 px): 50 px = 1 unidad, origen en el centro de la cara.
import bpy
import bmesh
import math
import os
from mathutils import Euler, Vector

CARPETA = "/home/elvira/Documentos/Claude/animacion-/José Daniel"

COL = {
    "piel": "#b6946e",
    "pelo": "#111111",
    "gorra": "#7d7d7d",
    "blanco_ojo": "#f2f2f2",
    "ojo": "#121212",
    "brillo": "#ffffff",
    "boca": "#3b2a1c",
    "cuerpo_arriba": "#555555",
    "cuerpo_abajo": "#e2e2e2",
    "fondo": "#ffffff",
}

R_CARA = 0.92      # radio de la cara (ancho 92 px)
FONDO_CARA = 0.7   # profundidad de la cara (hacia la cámara)


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


def material(nombre, color, rough=0.55, metal=0.0):
    mat = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    mat.use_nodes = True
    bsdf = bsdf_de(mat)
    bsdf.inputs["Base Color"].default_value = lin(color)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    mat.diffuse_color = lin(color)
    return mat


def material_degradado(nombre, arriba, abajo):
    """Degradado vertical (coordenada Z del objeto): oscuro arriba, claro abajo."""
    mat = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = bsdf_de(mat)
    bsdf.inputs["Roughness"].default_value = 0.5
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = lin(abajo)
    ramp.color_ramp.elements[1].color = lin(arriba)
    nt.links.new(coord.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def objeto(nombre, forma, loc, escala=(1, 1, 1), rot=(0, 0, 0), mat=None, suave=True, **kw):
    me = bpy.data.meshes.new(nombre)
    bm = bmesh.new()
    if forma == "esfera":
        bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=1.0)
    elif forma == "cubo":
        bmesh.ops.create_cube(bm, size=1.0)
    elif forma == "cono":
        bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=kw["r_abajo"],
                              radius2=kw["r_arriba"], depth=kw["alto"])
    if kw.get("solo_arriba"):
        # media esfera: se queda con la mitad superior y tapa el corte
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0), plane_no=(0, 0, 1), clear_inner=True)
        bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    bm.to_mesh(me)
    bm.free()
    if suave:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(nombre, me)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    ob.scale = escala
    ob.rotation_euler = [math.radians(a) for a in rot]
    if mat:
        me.materials.append(mat)
    return ob


def en_cara(x, z, salir=0.0):
    """Punto sobre la superficie frontal de la cara (la cámara mira desde -Y), movido
    `salir` unidades hacia afuera siguiendo la curva, y la rotación que lo deja pegado a ella."""
    k = max(0.0, 1 - (x / R_CARA) ** 2 - (z / R_CARA) ** 2)
    p = Vector((x, -FONDO_CARA * math.sqrt(k), z))
    n = Vector((p.x / R_CARA ** 2, p.y / FONDO_CARA ** 2, p.z / R_CARA ** 2)).normalized()
    return p + n * salir, n.to_track_quat("-Y", "Z")


def sobre_cara(nombre, forma, x, z, salir, escala, giro=0.0, mat=None, suave=True):
    """Objeto apoyado en la cara; `giro` lo inclina (grados) sobre su propio frente."""
    loc, q = en_cara(x, z, salir)
    q = q @ Euler((0, math.radians(giro), 0)).to_quaternion()
    ob = objeto(nombre, forma, loc, escala, mat=mat, suave=suave)
    ob.rotation_euler = q.to_euler()
    return ob


def emparentar(hijo, padre):
    bpy.context.view_layer.update()
    mundo = hijo.matrix_world.copy()
    hijo.parent = padre
    hijo.matrix_world = mundo


# ---------------------------------------------------------------- escena nueva y vacía
bpy.ops.wm.read_homefile(use_empty=True)
scene = bpy.context.scene
scene.name = "José Daniel"

raiz = bpy.data.objects.new("Jose_Daniel", None)
bpy.context.collection.objects.link(raiz)

m_piel = material("Piel", COL["piel"], 0.6)
m_pelo = material("Pelo", COL["pelo"], 0.7)
m_gorra = material("Gorra_metal", COL["gorra"], 0.3, 0.9)
m_blanco_ojo = material("Blanco_ojo", COL["blanco_ojo"], 0.3)
m_ojo = material("Ojo", COL["ojo"], 0.25)
m_brillo = material("Brillo", COL["brillo"], 0.2)
m_boca = material("Boca", COL["boca"], 0.6)
m_cuerpo = material_degradado("Cuerpo", COL["cuerpo_arriba"], COL["cuerpo_abajo"])

# ---------------------------------------------------------------- controles (para animar)
raiz.location = (0, 0.1, -2.36)                    # a los pies del personaje
cabeza = bpy.data.objects.new("Control_Cabeza", None)
cabeza.empty_display_type = "SPHERE"
cabeza.empty_display_size = 0.25
cabeza.location = (0, 0.1, -0.85)                  # el cuello: la cabeza gira desde aquí
bpy.context.collection.objects.link(cabeza)
emparentar(cabeza, raiz)
de_cabeza = []

# ---------------------------------------------------------------- cabeza y cuerpo
de_cabeza.append(objeto("Cara", "esfera", (0, 0, 0), (R_CARA, FONDO_CARA, R_CARA), mat=m_piel))
cuerpo = objeto("Cuerpo", "cono", (0, 0.1, -1.61), mat=m_cuerpo, r_abajo=0.51, r_arriba=0.48, alto=1.5)
emparentar(cuerpo, raiz)

# ---------------------------------------------------------------- pelo rizado (bolitas a los lados)
for i, (x, z, r) in enumerate([(-1.0, 0.62, 0.27), (-1.1, 0.3, 0.3), (-1.08, -0.02, 0.3), (-1.0, -0.3, 0.26),
                               (0.98, 0.2, 0.27), (1.05, -0.1, 0.3), (0.98, -0.36, 0.26)]):
    de_cabeza.append(objeto(f"Pelo_{i + 1}", "esfera", (x, 0.15, z), (r, r * 0.9, r), mat=m_pelo))

# ---------------------------------------------------------------- gorra (cúpula + visera hacia la derecha)
de_cabeza.append(objeto("Gorra", "esfera", (0, 0.05, 0.38), (1.2, 0.95, 1.52), mat=m_gorra, solo_arriba=True))
de_cabeza.append(objeto("Gorra_banda", "cono", (0, 0.05, 0.42), (1, 0.8, 1), mat=m_gorra,
                        r_abajo=1.2, r_arriba=1.19, alto=0.08))
de_cabeza.append(objeto("Visera_base", "cubo", (0.94, 0.0, 0.91), (0.64, 0.75, 0.74), mat=m_gorra, suave=False))
de_cabeza.append(objeto("Visera", "cubo", (1.58, 0.0, 0.66), (0.7, 0.62, 0.32), (0, -4, 0), mat=m_gorra, suave=False))
for nombre in ("Visera_base", "Visera"):
    bev = bpy.data.objects[nombre].modifiers.new("Bisel", "BEVEL")
    bev.width = 0.04
    bev.segments = 3

# ---------------------------------------------------------------- cara: ojos enojados, párpados, boca
# Cada ojo tiene 3 capas: base blanca (Ojo_*), parte negra (Pupila_*) y brillo (Brillo_*).
# Pupila y brillo cuelgan del ojo blanco: al parpadear (escala Z del ojo) se cierran juntos.
for lado, x in (("izq", -0.48), ("der", 0.47)):
    s = -1 if lado == "izq" else 1
    ojo = sobre_cara(f"Ojo_{lado}", "esfera", x, 0.14, -0.03, (0.34, 0.07, 0.24), s * 6, m_blanco_ojo)
    pupila = sobre_cara(f"Pupila_{lado}", "esfera", x - s * 0.01, 0.12, -0.01, (0.28, 0.06, 0.2), s * 6, m_ojo)
    brillo = sobre_cara(f"Brillo_{lado}", "esfera", x - s * 0.08, 0.1, 0.06, (0.05, 0.03, 0.05), 0, m_brillo)
    emparentar(pupila, ojo)
    emparentar(brillo, ojo)
    de_cabeza.append(ojo)
    # párpado color piel que tapa la parte de arriba del ojo, más bajo hacia la nariz -> enojo
    de_cabeza.append(sobre_cara(f"Parpado_{lado}", "cubo", x - s * 0.02, 0.33, 0.02, (0.74, 0.1, 0.2),
                                s * -26, m_piel, suave=False))
de_cabeza.append(sobre_cara("Boca", "cubo", 0.0, -0.51, 0.0, (0.42, 0.06, 0.045), 0, m_boca, suave=False))

for p in de_cabeza:
    emparentar(p, cabeza)

# ---------------------------------------------------------------- imagen de referencia (solo en el visor)
img = bpy.data.images.load(os.path.join(CARPETA, "referencia.png"), check_existing=True)
ref = bpy.data.objects.new("Referencia", None)
ref.empty_display_type = "IMAGE"
ref.data = img
ref.empty_display_size = 218 / 50
ref.location = (0.19, 3.0, -0.2)
ref.rotation_euler = (math.radians(90), 0, 0)
ref.hide_render = True
bpy.context.collection.objects.link(ref)

# ---------------------------------------------------------------- mundo, luces, cámara
world = bpy.data.worlds.new("Mundo")
scene.world = world
world.use_nodes = True
wnt = world.node_tree
fondo = next((n for n in wnt.nodes if n.type == "BACKGROUND"), None)
if fondo is None:
    fondo = wnt.nodes.new("ShaderNodeBackground")
    wout = next((n for n in wnt.nodes if n.type == "OUTPUT_WORLD"), None) or wnt.nodes.new("ShaderNodeOutputWorld")
    wnt.links.new(fondo.outputs["Background"], wout.inputs["Surface"])
fondo.inputs["Color"].default_value = lin(COL["fondo"])
fondo.inputs["Strength"].default_value = 0.6
# la cámara ve el fondo blanco puro; la luz del ambiente queda más suave
camino = wnt.nodes.new("ShaderNodeLightPath")
blanco = wnt.nodes.new("ShaderNodeBackground")
blanco.inputs["Color"].default_value = (1, 1, 1, 1)
mezcla = wnt.nodes.new("ShaderNodeMixShader")
wout = next(n for n in wnt.nodes if n.type == "OUTPUT_WORLD")
wnt.links.new(camino.outputs["Is Camera Ray"], mezcla.inputs["Fac"])
wnt.links.new(fondo.outputs["Background"], mezcla.inputs[1])
wnt.links.new(blanco.outputs["Background"], mezcla.inputs[2])
wnt.links.new(mezcla.outputs["Shader"], wout.inputs["Surface"])

sol_data = bpy.data.lights.new("Sol", "SUN")
sol_data.energy = 1.3
sol = bpy.data.objects.new("Sol", sol_data)
bpy.context.collection.objects.link(sol)
sol.rotation_euler = (math.radians(55), math.radians(-25), math.radians(-20))

cam_data = bpy.data.cameras.new("Camara")
cam_data.type = "ORTHO"
cam_data.ortho_scale = 218 / 50
cam = bpy.data.objects.new("Camara", cam_data)
bpy.context.collection.objects.link(cam)
cam.location = (0.19, -10, -0.2)
cam.rotation_euler = (math.radians(90), 0, 0)
scene.camera = cam

scene.render.resolution_x = 197 * 4
scene.render.resolution_y = 218 * 4
scene.view_settings.view_transform = "Standard"

# ---------------------------------------------------------------- animación "Reposo" (bucle de 4 s)
FPS, FIN = 24, 96
scene.render.fps = FPS
scene.frame_start, scene.frame_end = 1, FIN


def claves(ob, prop, cuadros):
    """cuadros: {frame: valor}. El último frame repite el primero para que el bucle no salte."""
    for f, v in cuadros.items():
        setattr(ob, prop, v)
        ob.keyframe_insert(prop, frame=f)
    ob.animation_data.action.name = f"Reposo_{ob.name}"


g = math.radians
claves(cabeza, "rotation_euler", {1: (0, 0, 0), 25: (g(-3), g(4), g(8)), 49: (0, 0, 0),
                                  73: (g(-2), g(-4), g(-8)), FIN + 1: (0, 0, 0)})
claves(cuerpo, "scale", {1: (1, 1, 1), 49: (1.03, 1.03, 1.01), FIN + 1: (1, 1, 1)})
for lado in ("izq", "der"):
    ojo = bpy.data.objects[f"Ojo_{lado}"]
    base = tuple(ojo.scale)
    cerrado = (base[0], base[1], base[2] * 0.08)
    claves(ojo, "scale", {1: base, 38: base, 41: cerrado, 44: base, 84: base, 87: cerrado, 90: base,
                          FIN + 1: base})
scene.frame_set(1)

result = sorted(o.name for o in bpy.data.objects)
