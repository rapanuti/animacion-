# Prepara "Dome Camera [FREE]" (MiguelRamos, CC BY 4.0; ver modelos/CREDITOS.txt) para la web
# de MiCentinela: la cuelga del techo con el lente mirando al espectador, separa la bola del
# lente ("Ojo", que gira para seguir al cursor) del resto ("Base"), la escala al tamaño de
# camara_domo.glb (base de 2 unidades de ancho) y exporta web/camara_domo_free.glb y un render
# de respaldo en render/camara_domo_free.png.
#
# Uso (desde la raíz de animacion-):
#   blender --background --python Cámaras/exportar_domo_free.py
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

CARPETA = os.path.dirname(os.path.abspath(__file__))
MODELO = os.path.join(CARPETA, "modelos", "dome_camera_free.glb")
GLB = os.path.join(CARPETA, "web", "camara_domo_free.glb")
RENDER = os.path.join(CARPETA, "render", "camara_domo_free.png")
ANCHO_BASE = 2.0
ANCHO_MAX_OJO = 0.09  # piezas sueltas más angostas que esto son la bola y el lente

bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=MODELO)
bpy.context.view_layer.update()

# El original trae el cuerpo dos veces: "Electrics_Glass" es una copia idéntica de la geometría
# de "Electrics_Plastic". Superpuestas, en la web pelean por dibujarse (z-fighting) y el
# plástico se ve "rasgado". Se descarta la copia.
for o in [o for o in bpy.data.objects if o.type == "MESH"]:
    if any(m and m.name.startswith("Electrics_Glass") for m in o.data.materials):
        bpy.data.objects.remove(o)

# Unir todo en una malla con sus materiales, en coordenadas de mundo.
mallas = [o for o in bpy.data.objects if o.type == "MESH"]
for o in mallas:
    o.data = o.data.copy()
    o.data.transform(o.matrix_world)
    o.parent = None
    o.matrix_world = Matrix.Identity(4)
for o in [o for o in bpy.data.objects if o.type != "MESH"]:
    bpy.data.objects.remove(o)
bpy.ops.object.select_all(action="DESELECT")
for o in mallas:
    o.select_set(True)
bpy.context.view_layer.objects.active = mallas[0]
bpy.ops.object.join()
todo = bpy.context.active_object
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.remove_doubles(threshold=1e-6)
bpy.ops.object.mode_set(mode="OBJECT")

# Clasificar piezas sueltas: angostas = ojo, anchas = base.
bm = bmesh.new()
bm.from_mesh(todo.data)
bm.verts.ensure_lookup_table()
vistos, del_ojo = set(), set()
centro_bola, mayor = None, 0
for v in bm.verts:
    if v.index in vistos:
        continue
    pila, comp = [v], []
    while pila:
        x = pila.pop()
        if x.index in vistos:
            continue
        vistos.add(x.index)
        comp.append(x)
        pila.extend(e.other_vert(x) for e in x.link_edges)
    xs = [c.co.x for c in comp]
    ys = [c.co.y for c in comp]
    zs = [c.co.z for c in comp]
    if max(max(xs) - min(xs), max(ys) - min(ys)) < ANCHO_MAX_OJO:
        del_ojo.update(c.index for c in comp)
        if len(comp) > mayor:  # la pieza más grande del ojo es la bola
            mayor = len(comp)
            centro_bola = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2))
bm.free()

# Selección coherente en vértices, aristas y caras (lo importado viene todo seleccionado).
for v in todo.data.vertices:
    v.select = v.index in del_ojo
for e in todo.data.edges:
    e.select = all(i in del_ojo for i in e.vertices)
for p in todo.data.polygons:
    p.select = all(i in del_ojo for i in p.vertices)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.separate(type="SELECTED")
bpy.ops.object.mode_set(mode="OBJECT")
base = todo
base.name = "Base"
ojo = next(o for o in bpy.data.objects if o.type == "MESH" and o is not base)
ojo.name = "Ojo"

# Colgar del techo (giro de 180° en X) y que el lente, que mira a +X, mire a -Y (al espectador
# en glTF), escalado a ANCHO_BASE.
xs = [v.co.x for v in base.data.vertices]
escala = ANCHO_BASE / (max(xs) - min(xs))
giro = Matrix.Rotation(math.radians(-90), 4, "Z") @ Matrix.Rotation(math.radians(180), 4, "X")
# La base del modelo original ya está en z = 0: al voltearla queda pegada al techo y el resto
# cuelga hacia abajo.
transformar = Matrix.Scale(escala, 4) @ giro
for o in (base, ojo):
    o.data.transform(transformar)
    for p in o.data.polygons:
        p.use_smooth = True
centro = transformar @ centro_bola
# Origen del Ojo en el centro de la bola (su centro de giro).
ojo.data.transform(Matrix.Translation(-centro))
ojo.location = centro

# LED rojo de grabación sobre la bola, arriba a la izquierda del lente (parte del Ojo, así
# gira con él). La web lo hace parpadear (pieza "LedRec").
led_mat = bpy.data.materials.new("LED_Rec")
led_mat.use_nodes = True
pl = next(n for n in led_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
pl.inputs["Base Color"].default_value = (1.0, 0.05, 0.03, 1)
pl.inputs["Emission Color"].default_value = (1.0, 0.05, 0.03, 1)
pl.inputs["Emission Strength"].default_value = 4.0
# Se ubica sobre el anillo de LEDs infrarrojos que rodea al lente (material Electrics_Camera),
# arriba a la izquierda, como uno de esos "bombillos" encendido en rojo.
bpy.context.view_layer.update()  # que matrix_world refleje la nueva ubicación del Ojo
idx_lente = [i for i, m in enumerate(ojo.data.materials) if m and m.name.startswith("Electrics_Camera")][0]
pts_lente = [ojo.matrix_world @ ojo.data.vertices[i].co
             for p in ojo.data.polygons if p.material_index == idx_lente for i in p.vertices]
c_lente = sum(pts_lente, Vector()) / len(pts_lente)
normal = (c_lente - ojo.location).normalized()           # hacia donde mira el lente
r_lente = max((q - c_lente).length for q in pts_lente)    # radio del disco del lente
arriba = Vector((0, 0, 1))
arriba = (arriba - normal * arriba.dot(normal)).normalized()
izquierda = normal.cross(arriba).normalized()
if izquierda.x > 0:
    izquierda = -izquierda
sobre_anillo = (arriba * 0.62 + izquierda * 0.62).normalized() * r_lente * 0.78
bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=r_lente * 0.1,
                                     location=c_lente + sobre_anillo + normal * r_lente * 0.06)
led = bpy.context.active_object
led.name = "LedRec"
led.data.materials.append(led_mat)
for p in led.data.polygons:
    p.use_smooth = True
# El LED cuelga del Ojo para girar con él, con su propia pieza para que la web lo encienda.
led.parent = ojo
led.matrix_parent_inverse = ojo.matrix_world.inverted()

# Carcasa de metal pintado satinado: el original es un gris plano (0,38) que en la web se ve
# como plástico de dibujo animado. Con algo de metal y brillo, refleja el entorno de la escena.
# El lente y los LED quedan como vienen.
for m in bpy.data.materials:
    if m.name.startswith("Electrics_Plastic") and m.use_nodes:
        p = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if not p.inputs["Base Color"].is_linked:
            p.inputs["Base Color"].default_value = (0.74, 0.76, 0.79, 1)
        p.inputs["Metallic"].default_value = 0.65
        p.inputs["Roughness"].default_value = 0.3

# Sombreado suave por ángulo: el modelo es de pocos polígonos y con sombreado plano se ven las
# caras; así las curvas se ven curvas y las aristas marcadas siguen marcadas.
for o in (base, ojo):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))

# Render de respaldo, con estudio claro
esc = bpy.context.scene
w = bpy.data.worlds.new("Estudio")
esc.world = w
w.use_nodes = True
fondo = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
fondo.inputs["Color"].default_value = (0.9, 0.93, 1.0, 1)
fondo.inputs["Strength"].default_value = 1.0
objetivo = Vector((0, 0, -0.8))
for nombre, energia, pos in (("Clave", 900, (-2.5, -3.5, 1.5)), ("Relleno", 350, (3, -2.5, -1.5)), ("Contra", 400, (0.5, 3, 0.5))):
    ld = bpy.data.lights.new(nombre, "AREA")
    ld.energy = energia
    ld.size = 3
    lo = bpy.data.objects.new(nombre, ld)
    esc.collection.objects.link(lo)
    lo.location = pos
    lo.rotation_euler = (objetivo - lo.location).to_track_quat("-Z", "Y").to_euler()
cd = bpy.data.cameras.new("Camara")
cd.lens = 60
cam = bpy.data.objects.new("Camara", cd)
esc.collection.objects.link(cam)
cam.location = (1.4, -4.6, -1.9)
cam.rotation_euler = (objetivo - cam.location).to_track_quat("-Z", "Y").to_euler()
esc.camera = cam
esc.render.engine = "BLENDER_EEVEE"
esc.render.resolution_x = esc.render.resolution_y = 1000
esc.render.film_transparent = True
esc.render.filepath = RENDER
os.makedirs(os.path.dirname(RENDER), exist_ok=True)
bpy.ops.render.render(write_still=True)

bpy.ops.object.select_all(action="DESELECT")
base.select_set(True)
ojo.select_set(True)
led.select_set(True)
os.makedirs(os.path.dirname(GLB), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=GLB, export_format="GLB", use_selection=True, export_yup=True,
                          export_apply=True, export_extras=False)
zs = [v.co.z for v in base.data.vertices] + [(ojo.matrix_world @ v.co).z for v in ojo.data.vertices]
print("LISTO", round(os.path.getsize(GLB) / 1024, 1), "kB", "alto", round(max(zs) - min(zs), 3), "centro ojo", tuple(round(c, 3) for c in centro))
