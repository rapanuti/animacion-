# Exporta el celular "Modern Generic Smartphone" (Ottto3d, CC BY 4.0) como GLB liviano para la
# web de MiCentinela (website/public/models/celular.glb), preparado para alinear la pantalla HTML:
#   - origen en el centro de la pantalla, sobre el plano del vidrio (la pantalla queda en z = 0
#     mirando a +Z en glTF);
#   - escala: el ancho de la pantalla mide 1 unidad;
#   - material opaco (el modo transparente del original solo afecta al vidrio de las cámaras y en
#     la web provoca errores de orden de dibujo);
#   - texturas reducidas a 1024 px y en WebP.
# Uso (sin interfaz, desde la raíz de animacion-):
#   blender --background --python Celulares/exportar_web.py
import json
import os

import bpy
from mathutils import Matrix, Vector

CARPETA = os.path.dirname(os.path.abspath(__file__))
MODELO = os.path.join(CARPETA, "modelos", "modern_generic_smartphone.glb")
SALIDA = os.path.join(CARPETA, "web", "celular.glb")
TEXTURA_PX = 1024

bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=MODELO)
ob = next(o for o in bpy.data.objects if o.type == "MESH")
bpy.context.view_layer.update()

# Aplicar toda la jerarquía (rotaciones/escala de Sketchfab) a la malla y dejarla sin padres.
ob.data.transform(ob.matrix_world)
for otro in [o for o in bpy.data.objects if o is not ob]:
    bpy.data.objects.remove(otro)
ob.parent = None
ob.matrix_world = Matrix.Identity(4)

# La pantalla es la capa frontal más adelantada (normal -Y en Blender).
frontales = [p for p in ob.data.polygons if p.normal.y < -0.95]
y_vidrio = min(ob.data.vertices[p.vertices[0]].co.y for p in frontales)
pantalla = [p for p in frontales if abs(ob.data.vertices[p.vertices[0]].co.y - y_vidrio) < 5e-5]
vs = [ob.data.vertices[i].co for p in pantalla for i in p.vertices]
x0, x1 = min(v.x for v in vs), max(v.x for v in vs)
z0, z1 = min(v.z for v in vs), max(v.z for v in vs)
ancho_pantalla = x1 - x0
centro = Vector(((x0 + x1) / 2, y_vidrio, (z0 + z1) / 2))
escala = 1 / ancho_pantalla
ob.data.transform(Matrix.Scale(escala, 4) @ Matrix.Translation(-centro))

todos = [v.co for v in ob.data.vertices]
caja = {
    "x": [min(v.x for v in todos), max(v.x for v in todos)],
    "alto": [min(v.z for v in todos), max(v.z for v in todos)],
    "fondo": [min(v.y for v in todos), max(v.y for v in todos)],
}

mat = ob.data.materials[0]
mat.surface_render_method = "DITHERED"
for nodo in mat.node_tree.nodes:
    if nodo.type == "BSDF_PRINCIPLED":
        alfa = nodo.inputs["Alpha"]
        for enlace in list(alfa.links):
            mat.node_tree.links.remove(enlace)
        alfa.default_value = 1.0
for img in bpy.data.images:
    if img.size[0] > TEXTURA_PX:
        img.scale(TEXTURA_PX, TEXTURA_PX)

os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=SALIDA,
    export_format="GLB",
    export_image_format="WEBP",
    export_image_quality=82,
    export_yup=True,
    export_apply=True,
    export_materials="EXPORT",
    export_extras=False,
)

info = {
    "pantalla_alto": round((z1 - z0) * escala, 5),
    "pantalla_ancho": 1,
    "caja_celular": {k: [round(a, 5) for a in v] for k, v in caja.items()},
    "kb": round(os.path.getsize(SALIDA) / 1024, 1),
}
print("INFO_WEB", json.dumps(info))
