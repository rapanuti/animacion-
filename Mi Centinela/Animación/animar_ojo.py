# Animación del ojo de Mi Centinela: parpadeo suave + el iris mira a la izquierda, a la derecha
# y vuelve al centro. Se ejecuta con el logo base (mi_centinela.blend) abierto y guarda el
# resultado en Animación/mi_centinela_animacion.blend (el logo base no se modifica).
# Uso (desde la raíz del proyecto):
#   python3 blender_bridge/send.py -c "import bpy; bpy.ops.wm.open_mainfile(filepath='Mi Centinela/mi_centinela.blend')"
#   python3 blender_bridge/send.py "Mi Centinela/Animación/animar_ojo.py"
import bpy
import bmesh
import os

CARPETA = "/home/elvira/Documentos/Claude/animacion-/Mi Centinela/Animación"
FPS = 24
FIN = 144                 # 6 segundos, en bucle
RECORRIDO = 0.15          # cuánto se mueve el iris a cada lado (el ojo mide 0.34 de medio ancho)
CERRADO = 0.04            # escala vertical del ojo con el párpado cerrado

scene = bpy.context.scene
logo = bpy.data.objects["Logo"]
ojo = bpy.data.objects["Ojo"]
centro = ojo.matrix_world.translation.copy()


def control(nombre):
    ob = bpy.data.objects.new(nombre, None)
    ob.empty_display_type = "CIRCLE"
    ob.empty_display_size = 0.4
    bpy.context.collection.objects.link(ob)
    ob.parent = logo
    ob.location = centro
    return ob


def emparentar(hijo, padre):
    bpy.context.view_layer.update()
    mundo = hijo.matrix_world.copy()
    hijo.parent = padre
    hijo.matrix_world = mundo


# ---------------------------------------------------------------- controles
# Control_Ojo: su escala vertical (Y) abre y cierra el ojo.
# Control_Iris: su posición X mueve iris, pupila y brillo juntos.
ctl_ojo = control("Control_Ojo")
ctl_iris = control("Control_Iris")
bpy.context.view_layer.update()
emparentar(ojo, ctl_ojo)
for nombre in ("Iris", "Pupila", "Brillo"):
    emparentar(bpy.data.objects[nombre], ctl_iris)

# ---------------------------------------------------------------- máscara con la forma del ojo
# Copia del contorno del ojo, alta en Z, que recorta el iris para que nunca se salga del ojo.
# Como cuelga de Control_Ojo, al parpadear también tapa el iris (hace de párpado).
bm = bmesh.new()
bm.from_mesh(ojo.data)          # contorno plano (el grosor del ojo lo da un modificador)
for v in bm.verts:
    v.co.z = -0.05
nuevo = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])["geom"]
for v in (g for g in nuevo if isinstance(g, bmesh.types.BMVert)):
    v.co.z = 0.3
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
mascara_me = bpy.data.meshes.new("Mascara_ojo")
bm.to_mesh(mascara_me)
bm.free()
mascara = bpy.data.objects.new("Mascara_ojo", mascara_me)
bpy.context.collection.objects.link(mascara)
mascara.parent = ctl_ojo
mascara.location = (0, 0, -centro.z)
mascara.display_type = "WIRE"
mascara.hide_render = True
for nombre in ("Iris", "Pupila", "Brillo"):
    mod = bpy.data.objects[nombre].modifiers.new("Dentro_del_ojo", "BOOLEAN")
    mod.operation = "INTERSECT"
    mod.solver = "EXACT"
    mod.object = mascara
mascara.hide_set(True)

# ---------------------------------------------------------------- animación
scene.render.fps = FPS
scene.frame_start, scene.frame_end = 1, FIN


def claves(ob, prop, indice, cuadros, accion):
    for f, v in cuadros.items():
        getattr(ob, prop)[indice] = v
        ob.keyframe_insert(prop, index=indice, frame=f)
    ob.animation_data.action.name = accion


# Parpadeo suave: baja en 6 cuadros (1/4 s), sube en 7
claves(ctl_ojo, "scale", 1, {1: 1, 14: 1, 20: CERRADO, 27: 1, FIN + 1: 1}, "Parpadeo")
# Mirada: centro -> izquierda (pausa) -> derecha (pausa) -> centro
claves(ctl_iris, "location", 0, {1: centro.x, 36: centro.x, 56: centro.x - RECORRIDO, 70: centro.x - RECORRIDO,
                                 100: centro.x + RECORRIDO, 114: centro.x + RECORRIDO, 134: centro.x,
                                 FIN + 1: centro.x}, "Mirada")
scene.frame_set(1)

os.makedirs(CARPETA, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(CARPETA, "mi_centinela_animacion.blend"))
result = bpy.data.filepath
