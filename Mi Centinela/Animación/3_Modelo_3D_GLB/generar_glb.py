# Exporta la animación del ojo de Mi Centinela como modelo 3D GLB (glTF binario) para la web.
# Genera logo_completo/mi_centinela_completo.glb y solo_escudo/mi_centinela_escudo.glb.
# glTF no admite la máscara (booleano) que recorta el iris, por eso aquí el iris recorre
# un poco menos para quedar siempre dentro del ojo; el parpadeo es igual.
# Uso:
#   cd "Mi Centinela/Animación"
#   blender --background mi_centinela_animacion.blend --python 3_Modelo_3D_GLB/generar_glb.py
import bpy
import bmesh
import math
import os

AQUI = os.path.join(os.path.dirname(bpy.data.filepath), "3_Modelo_3D_GLB")
RECORRIDO_GLB = 0.09

scene = bpy.context.scene
scene.name = "Parpadeo_y_mirada"
scene.frame_set(1)
D = bpy.data.objects


def lin(hexstr):
    h = hexstr.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def material_plano(nombre, color, rough=0.45):
    mat = bpy.data.materials.new(nombre)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = lin(color)
    bsdf.inputs["Roughness"].default_value = rough
    return mat


def emparentar(hijo, padre):
    bpy.context.view_layer.update()
    mundo = hijo.matrix_world.copy()
    hijo.parent = padre
    hijo.matrix_world = mundo


# ---------------------------------------------------------------- quitar lo que glTF no entiende
for nombre in ("Iris", "Pupila", "Brillo"):
    D[nombre].modifiers.clear()
bpy.data.objects.remove(D["Mascara_ojo"])
for nombre in ("Camara", "Sol"):
    bpy.data.objects.remove(D[nombre])

# el iris cuelga ahora del control del ojo: al parpadear se aplasta junto con el ojo
emparentar(D["Control_Iris"], D["Control_Ojo"])

# mirada con recorrido corto (re-hace las claves con los mismos tiempos)
ctl = D["Control_Iris"]
cx = ctl.location.x
ctl.animation_data_clear()
for f, v in {1: cx, 36: cx, 56: cx - RECORRIDO_GLB, 70: cx - RECORRIDO_GLB, 100: cx + RECORRIDO_GLB,
             114: cx + RECORRIDO_GLB, 134: cx, scene.frame_end + 1: cx}.items():
    ctl.location.x = v
    ctl.keyframe_insert("location", index=0, frame=f)
scene.frame_set(1)

# parpadeo y mirada en UNA sola animación: pistas NLA con el mismo nombre se exportan juntas
# (los visores web reproducen una animación a la vez)
for ob in (D["Control_Ojo"], ctl):
    ad = ob.animation_data
    accion = ad.action
    slot = getattr(ad, "action_slot", None)
    pista = ad.nla_tracks.new()
    pista.name = scene.name
    tira = pista.strips.new(scene.name, 1, accion)
    if slot is not None and hasattr(tira, "action_slot"):
        tira.action_slot = slot
    ad.action = None
scene.frame_set(1)

# ---------------------------------------------------------------- todo a mallas con colores planos
deps = bpy.context.evaluated_depsgraph_get()
COLORES = {
    "Escudo_borde": "#2f72d6", "Ojo": "#ffffff", "Iris": "#2f7de1", "Pupila": "#0c2654",
    "Brillo": "#ffffff", "Texto_Mi": "#4b5c72", "Texto_Centinela": "#14315c", "Punto_i": "#2f7de1",
}
for nombre, color in COLORES.items():
    ob = D[nombre]
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps))
    me.materials.clear()
    me.materials.append(material_plano(nombre, color, 0.3 if nombre in ("Ojo", "Iris", "Pupila", "Brillo") else 0.45))
    if ob.type == "MESH":
        ob.modifiers.clear()
        ob.data = me
    else:  # texto -> objeto malla nuevo en la misma posición y jerarquía
        nuevo = bpy.data.objects.new(nombre, me)
        scene.collection.objects.link(nuevo)
        nuevo.parent = ob.parent
        nuevo.matrix_parent_inverse = ob.matrix_parent_inverse.copy()
        nuevo.matrix_basis = ob.matrix_basis.copy()
        bpy.data.objects.remove(ob)
        nuevo.name = nombre

# escudo de dos tonos -> dos mallas (izquierda clara, derecha oscura)
esc = D["Escudo"]
base = bpy.data.meshes.new_from_object(esc.evaluated_get(deps))
for lado, color in (("izq", "#2a66c9"), ("der", "#10306a")):
    bm = bmesh.new()
    bm.from_mesh(base)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0), plane_no=(1, 0, 0),
                           clear_outer=(lado == "izq"), clear_inner=(lado == "der"))
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    me = bpy.data.meshes.new(f"Escudo_{lado}")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(material_plano(f"Escudo_{lado}", color))
    ob = bpy.data.objects.new(f"Escudo_{lado}", me)
    scene.collection.objects.link(ob)
    ob.parent = esc.parent
    ob.matrix_parent_inverse = esc.matrix_parent_inverse.copy()
    ob.matrix_basis = esc.matrix_basis.copy()
bpy.data.objects.remove(esc)

# de pie, mirando al frente (en glTF el frente es +Z y arriba +Y)
D["Logo"].rotation_euler.x = math.radians(90)
bpy.context.view_layer.update()


def exportar(ruta):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=ruta, export_format="GLB", export_animations=True,
                              export_animation_mode="NLA_TRACKS", export_yup=True, export_apply=True,
                              export_lights=False, export_cameras=False)
    print("GLB_LISTO", ruta, os.path.getsize(ruta), "bytes")


exportar(os.path.join(AQUI, "logo_completo", "mi_centinela_completo.glb"))
for nombre in ("Texto_Mi", "Texto_Centinela", "Punto_i"):
    bpy.data.objects.remove(D[nombre])
# el escudo queda centrado (el Logo tenía el origen en el centro del escudo)
exportar(os.path.join(AQUI, "solo_escudo", "mi_centinela_escudo.glb"))
