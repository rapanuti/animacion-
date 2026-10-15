# Genera los SVG animados de Mi Centinela (logo completo y solo escudo) a partir del .blend.
# La geometría sale del archivo de Blender (escudo, ojo, iris y las letras convertidas a trazos,
# así que no hace falta tener la fuente instalada). La animación es CSS dentro del SVG:
# misma curva de tiempo que en Blender (6 s en bucle, 144 cuadros a 24 fps).
# Uso:
#   cd "Mi Centinela/Animación"
#   blender --background mi_centinela_animacion.blend --python 2_SVG_animado/generar_svg.py
import bpy
import os
from mathutils import Vector

AQUI = os.path.join(os.path.dirname(bpy.data.filepath), "2_SVG_animado")
ESCALA = 100                 # 1 unidad de Blender = 100 unidades SVG
DURACION = 6                 # segundos
CUADROS = 144
RECORRIDO = 15               # mismo recorrido del iris que en Blender (0.15)

COL = {
    "borde": "#2f72d6", "esc_izq": "#2a66c9", "esc_der": "#10306a", "ojo": "#ffffff",
    "iris": "#2f7de1", "pupila": "#0c2654", "brillo": "#ffffff",
    "mi": "#4b5c72", "centinela": "#14315c", "punto": "#2f7de1",
}

deps = bpy.context.evaluated_depsgraph_get()
bpy.context.scene.frame_set(1)


def svg_xy(v):
    return v.x * ESCALA, -v.y * ESCALA


def num(x):
    return f"{x:.2f}".rstrip("0").rstrip(".")


def poligono(nombre):
    """Contorno de una figura plana (cara principal de su malla) como path SVG."""
    ob = bpy.data.objects[nombre]
    me = ob.data
    cara = max(me.polygons, key=lambda p: len(p.vertices))
    pts = [svg_xy(ob.matrix_world @ me.vertices[i].co) for i in cara.vertices]
    return "M" + " L".join(f"{num(x)} {num(y)}" for x, y in pts) + " Z", pts


def circulo(nombre):
    ob = bpy.data.objects[nombre]
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    c = sum(pts, Vector()) / len(pts)
    r = max((p - c).length for p in pts)
    x, y = svg_xy(c)
    return x, y, r * ESCALA


def texto(nombre):
    """Letras convertidas a curvas Bézier (path SVG con agujeros por evenodd)."""
    ob = bpy.data.objects[nombre]
    cu = ob.evaluated_get(deps).to_curve(deps, apply_modifiers=False)
    m = ob.matrix_world
    partes = []
    for sp in cu.splines:
        bp = sp.bezier_points
        if not bp:
            continue
        p = lambda v: "{} {}".format(*map(num, svg_xy(m @ v)))
        d = f"M{p(bp[0].co)}"
        for a, b in zip(bp, list(bp[1:]) + [bp[0]]):
            d += f" C{p(a.handle_right)} {p(b.handle_left)} {p(b.co)}"
        partes.append(d + " Z")
    ob.to_curve_clear()
    return " ".join(partes)


borde_d, borde_pts = poligono("Escudo_borde")
escudo_d, _ = poligono("Escudo")
ojo_d, _ = poligono("Ojo")
iris = circulo("Iris")
pupila = circulo("Pupila")
brillo = circulo("Brillo")
punto = circulo("Punto_i")
mi_d = texto("Texto_Mi")
centinela_d = texto("Texto_Centinela")


def pct(cuadro):
    return f"{(cuadro - 1) / CUADROS * 100:.2f}%"


ESTILO = f"""
    .parpado {{ transform-box: fill-box; transform-origin: center;
               animation: parpadeo {DURACION}s ease-in-out infinite; }}
    .mirada {{ animation: mirada {DURACION}s ease-in-out infinite; }}
    @keyframes parpadeo {{
      0%, {pct(14)} {{ transform: scaleY(1); }}
      {pct(20)} {{ transform: scaleY(0.04); }}
      {pct(27)}, 100% {{ transform: scaleY(1); }}
    }}
    @keyframes mirada {{
      0%, {pct(36)} {{ transform: translateX(0); }}
      {pct(56)}, {pct(70)} {{ transform: translateX(-{RECORRIDO}px); }}
      {pct(100)}, {pct(114)} {{ transform: translateX({RECORRIDO}px); }}
      {pct(134)}, 100% {{ transform: translateX(0); }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      .parpado, .mirada {{ animation: none; }}
    }}"""


def svg(con_texto, titulo):
    xs = [x for x, _ in borde_pts]
    ys = [y for _, y in borde_pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    if con_texto:
        x1 = max(x1, 0)  # se recalcula abajo con el texto
        # límites del texto a partir de sus puntos
        for nombre in ("Texto_Mi", "Texto_Centinela"):
            ob = bpy.data.objects[nombre]
            ev = ob.evaluated_get(deps)
            for c in ev.bound_box:
                x, y = svg_xy(ob.matrix_world @ Vector(c))
                x0, x1, y0, y1 = min(x0, x), max(x1, x), min(y0, y), max(y1, y)
        y0 = min(y0, punto[1] - punto[2])
    m = 8
    vb = f"{num(x0 - m)} {num(y0 - m)} {num(x1 - x0 + 2 * m)} {num(y1 - y0 + 2 * m)}"
    mitad = f'<rect x="{num(x0 - m)}" y="{num(y0 - m)}" width="{num(-(x0 - m))}" height="{num(y1 - y0 + 2 * m)}"/>'
    letras = f"""
  <g id="texto">
    <path fill="{COL['mi']}" fill-rule="evenodd" d="{mi_d}"/>
    <path fill="{COL['centinela']}" fill-rule="evenodd" d="{centinela_d}"/>
    <circle fill="{COL['punto']}" cx="{num(punto[0])}" cy="{num(punto[1])}" r="{num(punto[2])}"/>
  </g>""" if con_texto else ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" role="img" aria-labelledby="titulo">
  <title id="titulo">{titulo}</title>
  <style>{ESTILO}
  </style>
  <defs>
    <clipPath id="mitad-izquierda">{mitad}</clipPath>
    <clipPath id="forma-ojo"><path d="{ojo_d}"/></clipPath>
  </defs>
  <g id="escudo">
    <path fill="{COL['borde']}" d="{borde_d}"/>
    <path fill="{COL['esc_der']}" d="{escudo_d}"/>
    <path fill="{COL['esc_izq']}" d="{escudo_d}" clip-path="url(#mitad-izquierda)"/>
  </g>
  <g class="parpado">
    <path fill="{COL['ojo']}" d="{ojo_d}"/>
    <g clip-path="url(#forma-ojo)">
      <g class="mirada">
        <circle fill="{COL['iris']}" cx="{num(iris[0])}" cy="{num(iris[1])}" r="{num(iris[2])}"/>
        <circle fill="{COL['pupila']}" cx="{num(pupila[0])}" cy="{num(pupila[1])}" r="{num(pupila[2])}"/>
        <circle fill="{COL['brillo']}" cx="{num(brillo[0])}" cy="{num(brillo[1])}" r="{num(brillo[2])}"/>
      </g>
    </g>
  </g>{letras}
</svg>
"""


for carpeta, archivo, con_texto, titulo in (
        ("logo_completo", "mi_centinela_completo.svg", True, "Mi Centinela"),
        ("solo_escudo", "mi_centinela_escudo.svg", False, "Mi Centinela (escudo)")):
    os.makedirs(os.path.join(AQUI, carpeta), exist_ok=True)
    ruta = os.path.join(AQUI, carpeta, archivo)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(svg(con_texto, titulo))
    print("SVG_LISTO", ruta, os.path.getsize(ruta), "bytes")
