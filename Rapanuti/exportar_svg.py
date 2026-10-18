# Genera los SVG (vector plano) del logo de Rapanuti para fondo claro y oscuro, y del ícono "R" solo.
# El ícono sale de la misma geometría que usa Blender (con arcos exactos) y las letras de
# Montserrat Medium se convierten a trazos (no hace falta tener la fuente instalada).
# Uso:
#   cd Rapanuti && blender --background rapanuti.blend --python exportar_svg.py
import bpy
import math
import os

CARPETA = os.path.dirname(bpy.data.filepath)
SALIDA = os.path.join(CARPETA, "svg")
COLORES = {"claro": "#132136", "oscuro": "#ffffff"}

# geometría y medidas compartidas con logo_rapanuti.py
ns = {}
fuente = open(os.path.join(CARPETA, "logo_rapanuti.py"), encoding="utf-8").read()
exec(fuente[fuente.index("PIEZA_R = ["):fuente.index("def a_unidades(")], ns)
PIEZA_R, PILAR, X0, BASE = ns["PIEZA_R"], ns["PILAR"], ns["X0"], ns["BASE"]


def num(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def path_icono(segmentos):
    d, actual = "", None
    for s in segmentos:
        if s[0] == "L":
            x, y = s[1]
            d += f"{'L' if d else 'M'}{num(x)} {num(y)} "
        else:
            _, (cx, cy), r, a0, a1 = s
            x = cx + r * math.cos(math.radians(a1))
            y = cy + r * math.sin(math.radians(a1))
            d += f"A{num(r)} {num(r)} 0 0 {1 if a1 > a0 else 0} {num(x)} {num(y)} "
    return d + "Z"


def path_texto():
    ob = bpy.data.objects["Texto_Rapanuti"]
    deps = bpy.context.evaluated_depsgraph_get()
    cu = ob.evaluated_get(deps).to_curve(deps, apply_modifiers=False)
    m = ob.matrix_world
    px = lambda v: (X0 + (m @ v).x * 100, BASE - (m @ v).y * 100)
    p = lambda v: "{} {}".format(*map(num, px(v)))
    partes, ys, xs = [], [], []
    for sp in cu.splines:
        bp = sp.bezier_points
        if not bp:
            continue
        d = f"M{p(bp[0].co)}"
        for a, b in zip(bp, list(bp[1:]) + [bp[0]]):
            d += f" C{p(a.handle_right)} {p(b.handle_left)} {p(b.co)}"
            x, y = px(b.co)
            xs.append(x)
            ys.append(y)
        partes.append(d + " Z")
    ob.to_curve_clear()
    return " ".join(partes), (min(xs), min(ys), max(xs), max(ys))


icono_d = path_icono(PIEZA_R) + " " + path_icono(PILAR)
texto_d, (tx0, ty0, tx1, ty1) = path_texto()


def svg(caja, color, con_texto, titulo, margen=12):
    x0, y0, x1, y1 = caja
    vb = f"{num(x0 - margen)} {num(y0 - margen)} {num(x1 - x0 + 2 * margen)} {num(y1 - y0 + 2 * margen)}"
    texto = f'\n  <path fill-rule="evenodd" d="{texto_d}"/>' if con_texto else ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" role="img" aria-labelledby="titulo">
  <title id="titulo">{titulo}</title>
  <g fill="{color}">
  <path d="{icono_d}"/>{texto}
  </g>
</svg>
"""


caja_icono = (536, 193, 648, 277)
caja_logo = (536, min(193, ty0), max(648, tx1), max(277, ty1))
os.makedirs(SALIDA, exist_ok=True)
for tema, color in COLORES.items():
    for archivo, caja, con_texto, titulo in ((f"rapanuti_fondo_{tema}.svg", caja_logo, True, "Rapanuti"),
                                             (f"icono_r_fondo_{tema}.svg", caja_icono, False, "Rapanuti")):
        ruta = os.path.join(SALIDA, archivo)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(svg(caja, color, con_texto, titulo))
        print("SVG_LISTO", archivo, os.path.getsize(ruta), "bytes")
