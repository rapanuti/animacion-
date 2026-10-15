# Exporta a José Daniel para impresión 3D: 3MF, STL, OBJ y PLY en la carpeta "Impresión 3D".
# Uso (no toca la escena abierta):
#   cd "José Daniel" && blender --background jose_daniel.blend --python exportar_impresion_3d.py
import bpy
import bmesh
import os
import zipfile
from mathutils import Matrix

ALTO_MM = 90.0        # alto final de la figura, con base
BASE_R = 0.85         # base redonda para que quede de pie (unidades de Blender)
BASE_ALTO = 0.2
CARPETA = os.path.dirname(bpy.data.filepath)
OUT = os.path.join(CARPETA, "Impresión 3D")

# De mayor a menor prioridad: cada color se recorta con los que están antes en la lista,
# así ninguna pieza ocupa el espacio de otra (necesario para multicolor).
PRIORIDAD = [
    ("brillo",       ["Brillo_izq", "Brillo_der"]),
    ("gorra",        ["Gorra", "Gorra_banda", "Visera_base", "Visera"]),
    ("parpados",     ["Parpado_izq", "Parpado_der"]),
    ("negro",        ["Pupila_izq", "Pupila_der", "Boca"] + [f"Pelo_{i}" for i in range(1, 8)]),
    ("ojos_blancos", ["Ojo_izq", "Ojo_der"]),
    ("cara",         ["Cara"]),
    ("cuerpo",       ["Cuerpo"]),
    ("base",         ["Base"]),
]
# Archivos finales: un filamento por grupo
COLORES = {
    "1_base_gris_oscuro":   ("#3c3c3c", ["base"]),
    "2_cuerpo_gris_claro":  ("#c8c8c8", ["cuerpo"]),
    "3_piel":               ("#b6946e", ["cara", "parpados"]),
    "4_negro":              ("#111111", ["negro"]),
    "5_gorra_gris_metal":   ("#7d7d7d", ["gorra"]),
    "6_blanco":             ("#ffffff", ["brillo", "ojos_blancos"]),
}


def lin(hexstr):
    h = hexstr.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def material_color(nombre, color):
    mat = bpy.data.materials.new(nombre)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None) or nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = lin(color)
    mat.diffuse_color = lin(color)
    return mat


# ------------------------------------------------ escena de trabajo con las mallas "congeladas"
scene_src = bpy.context.scene
scene_src.frame_set(1)                       # pose de reposo (ojos abiertos)
deps = bpy.context.evaluated_depsgraph_get()
scene = bpy.data.scenes.new("Impresion")
vl = scene.view_layers[0]


def nuevo_objeto(nombre, me, coleccion=None):
    ob = bpy.data.objects.new(nombre, me)
    (coleccion or scene.collection).objects.link(ob)
    return ob


fuentes = {}
for nombres in (n for _, n in PRIORIDAD):
    for nombre in nombres:
        if nombre == "Base":
            continue
        src = bpy.data.objects[nombre]
        me = bpy.data.meshes.new_from_object(src.evaluated_get(deps))
        me.transform(src.matrix_world)
        fuentes[nombre] = me

# base redonda bajo el cuerpo (se mete 0.01 en el cuerpo para que la pieza única quede soldada)
pie = min(v.co.z for v in fuentes["Cuerpo"].vertices)
cx = sum(v.co.x for v in fuentes["Cuerpo"].vertices) / len(fuentes["Cuerpo"].vertices)
cy = sum(v.co.y for v in fuentes["Cuerpo"].vertices) / len(fuentes["Cuerpo"].vertices)
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=64, radius1=BASE_R, radius2=BASE_R, depth=BASE_ALTO,
                      matrix=Matrix.Translation((cx, cy, pie - BASE_ALTO / 2 + 0.01)))
fuentes["Base"] = bpy.data.meshes.new("Base")
bm.to_mesh(fuentes["Base"])
bm.free()

# ------------------------------------------------ booleanos: unir cada grupo y recortarlo con los de arriba
deps = None


def evaluar(ob, capa):
    capa.update()
    return bpy.data.meshes.new_from_object(ob.evaluated_get(capa.depsgraph))


def booleano(me, coleccion, operacion):
    ob = nuevo_objeto("_tmp", me)
    mod = ob.modifiers.new("B", "BOOLEAN")
    mod.operation = operacion
    mod.solver = "EXACT"
    mod.operand_type = "COLLECTION"
    mod.collection = coleccion
    mod.use_self = True
    mod.use_hole_tolerant = True
    resultado = evaluar(ob, vl)
    bpy.data.objects.remove(ob)
    return resultado


def coleccion_con(mallas, nombre):
    col = bpy.data.collections.new(nombre)
    scene.collection.children.link(col)
    for i, me in enumerate(mallas):
        nuevo_objeto(f"{nombre}_{i}", me.copy(), col)
    return col


arriba = []          # mallas de los grupos con más prioridad (cortadores)
piezas = {}
for grupo, nombres in PRIORIDAD:
    mallas = [fuentes[n] for n in nombres]
    if len(mallas) > 1:
        unido = booleano(mallas[0].copy(), coleccion_con(mallas[1:], f"union_{grupo}"), "UNION")
    else:
        unido = mallas[0].copy()
    pieza = booleano(unido.copy(), coleccion_con(arriba, f"corte_{grupo}"), "DIFFERENCE") if arriba else unido
    piezas[grupo] = pieza
    arriba.append(unido)

# pieza única (un color): unión de las formas originales, sin las caras pegadas de los recortes
piezas["una_pieza"] = booleano(arriba[0].copy(), coleccion_con(arriba[1:], "una_pieza"), "UNION")


def soldar(me):
    """Une vértices duplicados que dejan los booleanos, tapa huecos y orienta normales."""
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=5e-4)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=5e-4)
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context="EDGES")
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()


for me in piezas.values():
    soldar(me)

# ------------------------------------------------ escala a milímetros y apoyo en z = 0
zs = [v.co.z for me in piezas.values() for v in me.vertices]
k = ALTO_MM / (max(zs) - min(zs))
ajuste = Matrix.Translation((-cx * k, -cy * k, -min(zs) * k)) @ Matrix.Scale(k, 4)
for me in piezas.values():
    me.transform(ajuste)

# ------------------------------------------------ objetos finales por color
final = bpy.data.scenes.new("Impresion_final")
fvl = final.view_layers[0]
objetos = {}
for archivo, (color, grupos) in COLORES.items():
    bm = bmesh.new()  # une las piezas de los grupos de este color
    for g in grupos:
        bm.from_mesh(piezas[g])
    me = bpy.data.meshes.new(archivo)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(material_color(archivo, color))
    ob = bpy.data.objects.new(archivo, me)
    final.collection.objects.link(ob)
    objetos[archivo] = ob
ctx = {"scene": final, "view_layer": fvl}


def seleccionar(obs):
    for o in objetos.values():
        o.select_set(False, view_layer=fvl)
    for o in obs:
        o.select_set(True, view_layer=fvl)


def triangulos(obs):
    verts, tris = [], []
    for o in obs:
        me = o.data
        me.calc_loop_triangles()
        base = len(verts)
        verts += [tuple(v.co) for v in me.vertices]
        tris += [tuple(base + i for i in t.vertices) for t in me.loop_triangles]
    return verts, tris


def malla_3mf(verts, tris):
    vs = "".join(f'<vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in verts)
    ts = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tris)
    return f"<mesh><vertices>{vs}</vertices><triangles>{ts}</triangles></mesh>"


def escribir_3mf(ruta, partes):
    """partes: lista de (nombre, color_hex, [objetos]). Varias partes = un objeto multicolor."""
    mats = "".join(f'<base name="{n}" displaycolor="{c.upper()}FF"/>' for n, c, _ in partes)
    objs, comps = [], []
    for i, (n, _, obs) in enumerate(partes):
        oid = i + 2
        objs.append(f'<object id="{oid}" type="model" name="{n}" pid="1" pindex="{i}">'
                    f"{malla_3mf(*triangulos(obs))}</object>")
        comps.append(f'<component objectid="{oid}"/>')
    if len(partes) > 1:
        raiz = len(partes) + 2
        objs.append(f'<object id="{raiz}" type="model" name="José Daniel"><components>{"".join(comps)}</components></object>')
    else:
        raiz = 2
    modelo = ('<?xml version="1.0" encoding="UTF-8"?>'
              '<model unit="millimeter" xml:lang="es-ES" '
              'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
              '<metadata name="Title">José Daniel</metadata>'
              f'<resources><basematerials id="1">{mats}</basematerials>{"".join(objs)}</resources>'
              f'<build><item objectid="{raiz}"/></build></model>')
    tipos = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
             '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(ruta, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", tipos)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", modelo)


def carpeta(*partes):
    ruta = os.path.join(OUT, *partes)
    os.makedirs(ruta, exist_ok=True)
    return ruta


todos = list(objetos.values())
por_color = [(a, c, [objetos[a]]) for a, (c, _) in COLORES.items()]

me_una = piezas.pop("una_pieza")
ob_una = bpy.data.objects.new("una_pieza", me_una)
final.collection.objects.link(ob_una)
objetos_todos = dict(objetos, una_pieza=ob_una)


def seleccionar_obs(obs):
    for o in objetos_todos.values():
        o.select_set(False, view_layer=fvl)
    for o in obs:
        o.select_set(True, view_layer=fvl)


d = carpeta("1_3MF_recomendado")
escribir_3mf(os.path.join(d, "jose_daniel_multicolor.3mf"), por_color)
escribir_3mf(os.path.join(d, "jose_daniel_un_color.3mf"), [("José Daniel", "#7d7d7d", [ob_una])])

d = carpeta("2_STL", "por_color")
for archivo, _, obs in por_color:
    seleccionar_obs(obs)
    with bpy.context.temp_override(**ctx):
        bpy.ops.wm.stl_export(filepath=os.path.join(d, f"jose_daniel_{archivo}.stl"),
                              export_selected_objects=True, global_scale=1.0)
seleccionar_obs([ob_una])
with bpy.context.temp_override(**ctx):
    bpy.ops.wm.stl_export(filepath=os.path.join(carpeta("2_STL"), "jose_daniel_una_pieza.stl"),
                          export_selected_objects=True, global_scale=1.0)

seleccionar_obs(todos)
with bpy.context.temp_override(**ctx):
    bpy.ops.wm.obj_export(filepath=os.path.join(carpeta("3_OBJ_con_colores"), "jose_daniel.obj"),
                          export_selected_objects=True, export_materials=True,
                          forward_axis="Y", up_axis="Z", global_scale=1.0)

for archivo, (color, _) in COLORES.items():
    attr = objetos[archivo].data.color_attributes.new("Color", "BYTE_COLOR", "POINT")
    for d_ in attr.data:
        d_.color = lin(color)
seleccionar_obs(todos)
with bpy.context.temp_override(**ctx):
    bpy.ops.wm.ply_export(filepath=os.path.join(carpeta("4_PLY_con_colores"), "jose_daniel.ply"),
                          export_selected_objects=True, export_colors="SRGB",
                          forward_axis="Y", up_axis="Z", global_scale=1.0, ascii_format=False)

# ------------------------------------------------ informe: medidas y mallas cerradas
informe = []
for nombre, ob in objetos_todos.items():
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    abiertos = sum(1 for e in bm.edges if not e.is_manifold)
    vol = bm.calc_volume()
    zs = [v.co.z for v in bm.verts]
    bm.free()
    informe.append(f"{nombre:22s} z {min(zs):6.2f}-{max(zs):6.2f} mm  vol {vol / 1000:7.2f} cm3  bordes abiertos: {abiertos}")
xs = [v.co.x for v in ob_una.data.vertices]
ys = [v.co.y for v in ob_una.data.vertices]
zs = [v.co.z for v in ob_una.data.vertices]
informe.append(f"Tamaño: {max(xs) - min(xs):.1f} x {max(ys) - min(ys):.1f} x {max(zs) - min(zs):.1f} mm")
print("\n".join(informe))
