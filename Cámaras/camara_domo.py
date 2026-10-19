# Cámara domo de seguridad para El Ojo de Odin (MiCentinela), modelada desde cero (sin
# licencias de terceros). Arma la escena, guarda Cámaras/camara_domo.blend, renderiza una
# vista previa en Cámaras/render/ y exporta Cámaras/web/camara_domo.glb para el sitio.
#
# Piezas (nombres que usa la web):
#   Base   — montura de techo blanca con anillo azul de marca
#   Domo   — cúpula de vidrio ahumado (semitransparente)
#   Ojo    — módulo interior con el lente; su origen es el centro de giro, y mira hacia -Y
#            (en glTF, +Z: hacia el espectador). La web lo gira para seguir al cursor.
#
# Uso (desde la raíz de animacion-):
#   blender --background --python Cámaras/camara_domo.py
import math
import os

import bpy
from mathutils import Vector

CARPETA = os.path.dirname(os.path.abspath(__file__))
BLEND = os.path.join(CARPETA, "camara_domo.blend")
RENDER = os.path.join(CARPETA, "render", "camara_domo.png")
GLB = os.path.join(CARPETA, "web", "camara_domo.glb")

AZUL_MARCA = (0.0, 0.19, 1.0, 1)  # #007aff en lineal (aprox.)

bpy.ops.wm.read_homefile(use_empty=True)
escena = bpy.context.scene


def material(nombre, color, rugosidad=0.4, metal=0.0, alfa=1.0, emision=None):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    p = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    p.inputs["Base Color"].default_value = color
    p.inputs["Roughness"].default_value = rugosidad
    p.inputs["Metallic"].default_value = metal
    if alfa < 1:
        p.inputs["Alpha"].default_value = alfa
        m.surface_render_method = "BLENDED"
    if emision:
        p.inputs["Emission Color"].default_value = emision
        p.inputs["Emission Strength"].default_value = 2.0
    return m


m_blanco = material("Plastico_blanco", (0.86, 0.88, 0.9, 1), 0.35)
m_azul = material("Azul_marca", AZUL_MARCA, 0.3)
m_vidrio = material("Vidrio_ahumado", (0.02, 0.03, 0.05, 1), 0.04, alfa=0.32)
m_oscuro = material("Plastico_oscuro", (0.03, 0.035, 0.045, 1), 0.45)
m_lente = material("Lente", (0.005, 0.01, 0.03, 1), 0.02, metal=0.2)
m_brillo = material("Lente_brillo", (0.05, 0.25, 0.9, 1), 0.05, emision=(0.05, 0.3, 1.0, 1))
m_led = material("LED_IR", (0.12, 0.02, 0.02, 1), 0.2)


def suavizar(ob, bisel=None):
    for pol in ob.data.polygons:
        pol.use_smooth = True
    if bisel:
        mod = ob.modifiers.new("Bisel", "BEVEL")
        mod.width = bisel
        mod.segments = 3
        mod.limit_method = "ANGLE"


def aplicar(ob):
    bpy.context.view_layer.objects.active = ob
    for mod in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def unir(objetos, nombre):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objetos:
        aplicar(o)
        o.select_set(True)
    bpy.context.view_layer.objects.active = objetos[0]
    bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = nombre
    return ob


# ---------------------------------------------------------------- Base (techo arriba, z > 0)
bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1.0, depth=0.2, location=(0, 0, 0.1))
base = bpy.context.active_object
base.data.materials.append(m_blanco)
suavizar(base, bisel=0.05)

bpy.ops.mesh.primitive_torus_add(major_radius=0.88, minor_radius=0.03, major_segments=64,
                                 minor_segments=8, location=(0, 0, 0.0))
anillo = bpy.context.active_object
anillo.data.materials.append(m_azul)
suavizar(anillo)

# Collar blanco que abraza la cúpula
bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.86, depth=0.08, location=(0, 0, -0.02))
collar = bpy.context.active_object
collar.data.materials.append(m_blanco)
suavizar(collar, bisel=0.02)

base = unir([base, anillo, collar], "Base")

# ---------------------------------------------------------------- Domo (media esfera hacia abajo)
bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=0.82, location=(0, 0, -0.05))
domo = bpy.context.active_object
domo.name = "Domo"
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="DESELECT")
bpy.ops.object.mode_set(mode="OBJECT")
for v in domo.data.vertices:
    v.select = v.co.z > 0.001
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.delete(type="VERT")
bpy.ops.object.mode_set(mode="OBJECT")
domo.data.materials.append(m_vidrio)
suavizar(domo)

# ---------------------------------------------------------------- Ojo (módulo que gira)
CENTRO_OJO = Vector((0, 0, -0.32))
partes = []
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=0.46, location=CENTRO_OJO)
bola = bpy.context.active_object
bola.scale = (1, 1, 0.92)
bola.data.materials.append(m_oscuro)
suavizar(bola)
partes.append(bola)

# Barril del lente, apuntando a -Y
adelante = Vector((0, -1, 0))
rot_lente = (math.radians(90), 0, 0)
for radio, largo, desplazamiento, mat in (
    (0.22, 0.16, 0.42, m_oscuro),   # barril
    (0.17, 0.04, 0.51, m_lente),    # vidrio del lente
    (0.07, 0.01, 0.535, m_brillo),  # reflejo azul
):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=radio, depth=largo,
                                        location=CENTRO_OJO + adelante * desplazamiento,
                                        rotation=rot_lente)
    pieza = bpy.context.active_object
    pieza.data.materials.append(mat)
    suavizar(pieza, bisel=0.008 if mat is m_oscuro else None)
    partes.append(pieza)

# LEDs infrarrojos alrededor del lente, apoyados sobre la superficie del módulo
APERTURA = math.radians(38)  # ángulo entre el eje del lente y cada LED
for i in range(8):
    ang = i / 8 * math.tau
    direccion = Vector((math.cos(ang) * math.sin(APERTURA), -math.cos(APERTURA),
                        math.sin(ang) * math.sin(APERTURA))).normalized()
    pos = CENTRO_OJO + Vector((direccion.x * 0.46, direccion.y * 0.46, direccion.z * 0.46 * 0.92))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=0.03, location=pos)
    led = bpy.context.active_object
    led.data.materials.append(m_led)
    suavizar(led)
    partes.append(led)

ojo = unir(partes, "Ojo")
# Origen del Ojo = centro de giro
bpy.context.scene.cursor.location = CENTRO_OJO
bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
bpy.context.scene.cursor.location = (0, 0, 0)

# ---------------------------------------------------------------- Estudio y cámara de render
mundo = bpy.data.worlds.new("Estudio")
escena.world = mundo
mundo.use_nodes = True
fondo = next(n for n in mundo.node_tree.nodes if n.type == "BACKGROUND")
fondo.inputs["Color"].default_value = (0.92, 0.95, 1.0, 1)
fondo.inputs["Strength"].default_value = 0.8
for nombre, energia, pos in (("Luz_clave", 600, (-2.5, -3, 2)), ("Luz_relleno", 200, (3, -2, -1)),
                             ("Luz_contra", 300, (0.5, 3, 1.5))):
    ld = bpy.data.lights.new(nombre, "AREA")
    ld.energy = energia
    ld.size = 2.5
    lo = bpy.data.objects.new(nombre, ld)
    escena.collection.objects.link(lo)
    lo.location = pos
    lo.rotation_euler = (Vector((0, 0, -0.3)) - lo.location).to_track_quat("-Z", "Y").to_euler()

cam_data = bpy.data.cameras.new("Camara")
cam_data.lens = 60
cam = bpy.data.objects.new("Camara", cam_data)
escena.collection.objects.link(cam)
cam.location = (1.6, -4.2, -1.4)
cam.rotation_euler = (Vector((0, 0, -0.25)) - cam.location).to_track_quat("-Z", "Y").to_euler()
escena.camera = cam

escena.render.engine = "BLENDER_EEVEE"
escena.render.resolution_x = escena.render.resolution_y = 1000
escena.render.film_transparent = True
escena.render.filepath = RENDER
os.makedirs(os.path.dirname(RENDER), exist_ok=True)
bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=BLEND)

# ---------------------------------------------------------------- Exportar para la web
bpy.ops.object.select_all(action="DESELECT")
for o in (base, domo, ojo):
    o.select_set(True)
os.makedirs(os.path.dirname(GLB), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=GLB, export_format="GLB", use_selection=True,
                          export_yup=True, export_apply=True, export_extras=False)
print("LISTO", round(os.path.getsize(GLB) / 1024, 1), "kB")
