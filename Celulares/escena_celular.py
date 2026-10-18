# Importa el celular "Modern Generic Smartphone" (Ottto3d, CC BY 4.0) en una escena nueva con
# luces de estudio y cámara, y la guarda como Celulares/celulares.blend.
# Uso (desde la raíz del proyecto): python3 blender_bridge/send.py "Celulares/escena_celular.py"
import bpy
import math
import os
from mathutils import Vector

CARPETA = "/home/elvira/Documentos/Claude/animacion-/Celulares"
MODELO = os.path.join(CARPETA, "modelos", "modern_generic_smartphone.glb")

bpy.ops.wm.read_homefile(use_empty=True)
scene = bpy.context.scene
scene.name = "Celulares"
antes = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=MODELO)

# todo lo importado cuelga de un vacío "Celular" para moverlo y animarlo como una sola pieza
importados = [o for o in bpy.data.objects if o not in antes]
celular = bpy.data.objects.new("Celular", None)
celular.empty_display_type = "ARROWS"
celular.empty_display_size = 0.05
scene.collection.objects.link(celular)
for ob in importados:
    if ob.parent is None:
        ob.parent = celular
bpy.context.view_layer.update()

# El GLB trae el material en modo transparente ("BLEND"), aunque solo el vidrio de las cámaras
# (0,2 % de la textura) es semitransparente. En Eevee ese modo deja ver a través del celular;
# el modo "tramado" lo dibuja sólido y conserva el vidrio.
for o in importados:
    for slot in getattr(o, "material_slots", []):
        if slot.material:
            slot.material.surface_render_method = "DITHERED"

# medir el celular ya importado
mallas = [o for o in importados if o.type == "MESH"]
pts = [o.matrix_world @ Vector(c) for o in mallas for c in o.bound_box]
minimo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
maximo = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
tam = maximo - minimo
centro = (minimo + maximo) / 2
# centrar en el origen, apoyado en el suelo (z = 0)
celular.location = Vector((-centro.x, -centro.y, -minimo.z))
bpy.context.view_layer.update()
alto = max(tam)

# ---------------------------------------------------------------- mundo y luces de estudio
world = bpy.data.worlds.new("Estudio")
scene.world = world
world.use_nodes = True
fondo = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
fondo.inputs["Color"].default_value = (0.18, 0.19, 0.21, 1)
fondo.inputs["Strength"].default_value = 0.6

objetivo = Vector((0, 0, tam.z / 2))
for nombre, energia, pos, tam_luz in (("Luz_principal", 40, (-0.35, -0.4, 0.45), 0.4),
                                      ("Luz_relleno", 12, (0.45, -0.25, 0.2), 0.5),
                                      ("Luz_contra", 25, (0.1, 0.45, 0.35), 0.3)):
    ld = bpy.data.lights.new(nombre, "AREA")
    ld.energy = energia
    ld.size = tam_luz
    lo = bpy.data.objects.new(nombre, ld)
    scene.collection.objects.link(lo)
    lo.location = pos
    lo.rotation_euler = (lo.location - objetivo).to_track_quat("Z", "Y").to_euler()

# ---------------------------------------------------------------- cámara en tres cuartos
cam_data = bpy.data.cameras.new("Camara")
cam_data.lens = 70
cam = bpy.data.objects.new("Camara", cam_data)
scene.collection.objects.link(cam)
d = alto * 3.6
cam.location = objetivo + Vector((-0.55 * d, -0.8 * d, 0.25 * d))
cam.rotation_euler = (objetivo - cam.location).to_track_quat("-Z", "Y").to_euler()
scene.camera = cam

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 1080, 1350
scene.view_settings.view_transform = "AgX"

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(CARPETA, "celulares.blend"))
result = {"objetos": [o.name for o in importados], "tamano_m": [round(v, 4) for v in tam]}
