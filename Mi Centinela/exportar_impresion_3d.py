# Exporta el logo "Mi Centinela" para impresión 3D: 3MF, STL, OBJ y PLY en la carpeta "Impresión 3D".
# Uso (no toca la escena abierta):
#   cd "Mi Centinela" && blender --background mi_centinela.blend --python exportar_impresion_3d.py
import bpy
import bmesh
import math
import os
import zipfile
from mathutils import Matrix

ANCHO_MM = 120.0      # ancho final de la pieza
MARGEN = 0.12         # margen de la base alrededor del logo (unidades de Blender)
RADIO_BASE = 0.15
ALTO_BASE = 0.08      # ~2 mm a la escala final
OUT = os.path.join(os.path.dirname(bpy.data.filepath), "Impresión 3D")

# Grupos por color (un filamento por grupo)
GRUPOS = {
    "1_base_blanco":      ("#f2f2f2", ["Placa"]),
    "2_azul":             ("#2f72d6", ["Escudo_borde", "Escudo_izq", "Iris", "Punto_i"]),
    "3_azul_marino":      ("#14315c", ["Escudo_der", "Pupila", "Texto_Centinela"]),
    "4_blanco_ojo":       ("#ffffff", ["Ojo", "Brillo"]),
    "5_gris_azulado":     ("#4b5c72", ["Texto_Mi"]),
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


# ------------------------------------------------ ajustes para que las piezas no se superpongan
src = bpy.data.objects
# el relleno del escudo se apoya ENCIMA del borde (en vez de meterse dentro)
src["Escudo"].location.z = src["Escudo_borde"].modifiers["Grosor"].thickness
src["Escudo"].modifiers["Grosor"].thickness = 0.03
# el punto de la i tan alto como el texto
src["Punto_i"].modifiers["Grosor"].thickness = 0.06
bpy.context.view_layer.update()
deps = bpy.context.evaluated_depsgraph_get()


def malla_mundo(ob):
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps))
    me.transform(ob.matrix_world)
    return me


def mitad(me, lado):
    """Corta la malla en x=0 y tapa el corte. lado: 'izq' o 'der'."""
    bm = bmesh.new()
    bm.from_mesh(me)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0), plane_no=(1, 0, 0),
                           clear_outer=(lado == "izq"), clear_inner=(lado == "der"))
    bmesh.ops.holes_fill(bm, edges=bm.edges[:], sides=0)
    nuevo = bpy.data.meshes.new(me.name + "_" + lado)
    bm.to_mesh(nuevo)
    bm.free()
    return nuevo


mallas = {}
for nombre in ["Escudo_borde", "Ojo", "Iris", "Pupila", "Brillo", "Punto_i", "Texto_Mi", "Texto_Centinela"]:
    mallas[nombre] = malla_mundo(src[nombre])
escudo = malla_mundo(src["Escudo"])
mallas["Escudo_izq"] = mitad(escudo, "izq")
mallas["Escudo_der"] = mitad(escudo, "der")


def soldar(me):
    """Une vértices duplicados (las fuentes salen con tapas sueltas), tapa huecos y orienta normales."""
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()


for me in mallas.values():
    soldar(me)

# ------------------------------------------------ base rectangular con esquinas redondeadas
xs, ys = [], []
for me in mallas.values():
    for v in me.vertices:
        xs.append(v.co.x)
        ys.append(v.co.y)
x0, x1 = min(xs) - MARGEN, max(xs) + MARGEN
y0, y1 = min(ys) - MARGEN, max(ys) + MARGEN

contorno = []
for cx, cy, a0 in ((x1 - RADIO_BASE, y1 - RADIO_BASE, 0), (x0 + RADIO_BASE, y1 - RADIO_BASE, 90),
                   (x0 + RADIO_BASE, y0 + RADIO_BASE, 180), (x1 - RADIO_BASE, y0 + RADIO_BASE, 270)):
    for i in range(9):
        a = math.radians(a0 + 90 * i / 8)
        contorno.append((cx + RADIO_BASE * math.cos(a), cy + RADIO_BASE * math.sin(a)))

bm = bmesh.new()
abajo = [bm.verts.new((x, y, -ALTO_BASE)) for x, y in contorno]
arriba = [bm.verts.new((x, y, 0.0)) for x, y in contorno]
bm.faces.new(list(reversed(abajo)))
bm.faces.new(arriba)
n = len(contorno)
for i in range(n):
    j = (i + 1) % n
    bm.faces.new((abajo[i], abajo[j], arriba[j], arriba[i]))
mallas["Placa"] = bpy.data.meshes.new("Placa")
bm.to_mesh(mallas["Placa"])
bm.free()

# ------------------------------------------------ escala a milímetros (1 unidad = 1 mm en el STL)
k = ANCHO_MM / (x1 - x0)
escala = Matrix.Scale(k, 4)
# bajar todo para que la base apoye en z = 0
subir = Matrix.Translation((0, 0, ALTO_BASE * k))
for me in mallas.values():
    me.transform(escala)
    me.transform(subir)

# ------------------------------------------------ objetos nuevos en una escena limpia
scene = bpy.data.scenes.new("Impresion")
objetos = {}
for grupo, (color, nombres) in GRUPOS.items():
    mat = material_color(grupo, color)
    for nombre in nombres:
        me = mallas[nombre]
        me.materials.clear()
        me.materials.append(mat)
        ob = bpy.data.objects.new(nombre, me)
        scene.collection.objects.link(ob)
        objetos[nombre] = (grupo, ob)

vl = scene.view_layers[0]
ctx = {"scene": scene, "view_layer": vl}


def exportar_stl(ruta, obs):
    for _, o in objetos.values():
        o.select_set(False, view_layer=vl)
    for o in obs:
        o.select_set(True, view_layer=vl)
    with bpy.context.temp_override(**ctx):
        bpy.ops.wm.stl_export(filepath=ruta, export_selected_objects=True,
                              global_scale=1.0, apply_modifiers=True)


def seleccionar(obs):
    for _, o in objetos.values():
        o.select_set(False, view_layer=vl)
    for o in obs:
        o.select_set(True, view_layer=vl)


def triangulos(obs):
    """Vértices y triángulos (en mm) de varios objetos unidos en una sola malla."""
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
        objs.append(f'<object id="{raiz}" type="model" name="Mi Centinela"><components>{"".join(comps)}</components></object>')
    else:
        raiz = 2
    modelo = ('<?xml version="1.0" encoding="UTF-8"?>'
              '<model unit="millimeter" xml:lang="es-ES" '
              'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
              '<metadata name="Title">Mi Centinela</metadata>'
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


todos = [o for _, o in objetos.values()]
por_grupo = [(g, c, [objetos[n][1] for n in ns]) for g, (c, ns) in GRUPOS.items()]

# 3MF (recomendado)
d = carpeta("1_3MF_recomendado")
escribir_3mf(os.path.join(d, "mi_centinela_multicolor.3mf"), por_grupo)
escribir_3mf(os.path.join(d, "mi_centinela_un_color.3mf"), [("Mi Centinela", "#2f72d6", todos)])

# STL
d = carpeta("2_STL", "por_color")
for grupo, _, obs in por_grupo:
    seleccionar(obs)
    with bpy.context.temp_override(**ctx):
        bpy.ops.wm.stl_export(filepath=os.path.join(d, f"mi_centinela_{grupo}.stl"),
                              export_selected_objects=True, global_scale=1.0, apply_modifiers=True)
seleccionar(todos)
with bpy.context.temp_override(**ctx):
    bpy.ops.wm.stl_export(filepath=os.path.join(carpeta("2_STL"), "mi_centinela_una_pieza.stl"),
                          export_selected_objects=True, global_scale=1.0, apply_modifiers=True)

# OBJ con colores (.mtl)
seleccionar(todos)
with bpy.context.temp_override(**ctx):
    bpy.ops.wm.obj_export(filepath=os.path.join(carpeta("3_OBJ_con_colores"), "mi_centinela.obj"),
                          export_selected_objects=True, export_materials=True,
                          forward_axis="Y", up_axis="Z", global_scale=1.0)

# PLY con color por vértice
for grupo, color, obs in por_grupo:
    for o in obs:
        attr = o.data.color_attributes.new("Color", "BYTE_COLOR", "POINT")
        col = lin(color)
        for d_ in attr.data:
            d_.color = col
seleccionar(todos)
with bpy.context.temp_override(**ctx):
    bpy.ops.wm.ply_export(filepath=os.path.join(carpeta("4_PLY_con_colores"), "mi_centinela.ply"),
                          export_selected_objects=True, export_colors="SRGB",
                          forward_axis="Y", up_axis="Z", global_scale=1.0, ascii_format=False)

# ------------------------------------------------ informe: medidas y mallas cerradas
informe = []
for nombre, (grupo, ob) in objetos.items():
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    abiertos = sum(1 for e in bm.edges if not e.is_manifold)
    zs = [v.co.z for v in bm.verts]
    bm.free()
    informe.append(f"{nombre:16s} {grupo:16s} z {min(zs):5.2f}-{max(zs):5.2f} mm  bordes abiertos: {abiertos}")
xs = [v.co.x for v in mallas["Placa"].vertices]
ys = [v.co.y for v in mallas["Placa"].vertices]
alto_total = max(max(v.co.z for v in me.vertices) for me in mallas.values())
informe.append(f"Tamaño: {max(xs) - min(xs):.1f} x {max(ys) - min(ys):.1f} x {alto_total:.1f} mm")
print("\n".join(informe))
