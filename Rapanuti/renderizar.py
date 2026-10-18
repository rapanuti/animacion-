# Renderiza el logo de Rapanuti en fondo claro y oscuro (de frente, transparente y en perspectiva 3D)
# y el ícono "R" solo. Salida en Rapanuti/render/.
# Uso (no toca la escena abierta):
#   cd Rapanuti && blender --background rapanuti.blend --python renderizar.py
import bpy
import math
import os
from mathutils import Matrix, Vector

CARPETA = os.path.dirname(bpy.data.filepath)
SALIDA = os.path.join(CARPETA, "render")
os.makedirs(SALIDA, exist_ok=True)

# aplicar_tema() vive en el script que arma el logo; se reutiliza aquí
ns = {}
fuente = open(os.path.join(CARPETA, "logo_rapanuti.py"), encoding="utf-8").read()
inicio = fuente.index("def lin(")
fin = fuente.index("# ---------------------------------------------------------------- escena nueva")
exec(fuente[:fuente.index("# ---------------------------------------------------------------- geometría")] +
     fuente[inicio:fin], ns)
aplicar_tema = ns["aplicar_tema"]

s = bpy.context.scene
r = s.render
cam = s.camera
frente = (cam.location.copy(), cam.rotation_euler.copy(), cam.data.type, cam.data.ortho_scale,
          r.resolution_x, r.resolution_y)


def restaurar_frente():
    cam.location, cam.rotation_euler, cam.data.type, cam.data.ortho_scale, r.resolution_x, r.resolution_y = frente


def mirar(ob, objetivo, arriba=Vector((0, 1, 0))):
    """Apunta la cámara al objetivo manteniendo "arriba" el eje Y del logo."""
    adelante = (objetivo - ob.location).normalized()
    derecha = adelante.cross(arriba).normalized()
    sube = derecha.cross(adelante)
    ob.rotation_euler = Matrix((derecha, sube, -adelante)).transposed().to_euler()


def render(nombre, transparente=False):
    r.film_transparent = transparente
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA" if transparente else "RGB"
    r.filepath = os.path.join(SALIDA, nombre)
    bpy.ops.render.render(write_still=True)
    print("RENDER", nombre)


texto = [bpy.data.objects["Texto_Rapanuti"]]
for tema in ("claro", "oscuro"):
    aplicar_tema(tema)
    # logo completo, de frente
    restaurar_frente()
    render(f"rapanuti_fondo_{tema}.png")
    render(f"rapanuti_fondo_{tema}_transparente.png", transparente=True)

    # logo completo en perspectiva: se ve el relieve y los biseles
    cam.data.type = "PERSP"
    cam.data.lens = 55
    centro = Vector((2.62, 0.3, 0.0))
    cam.location = centro + Vector((-3.4, -0.9, 8.6))
    mirar(cam, centro)
    r.resolution_x, r.resolution_y = 2400, 1000
    render(f"rapanuti_3d_{tema}.png")

    # ícono "R" solo (cuadrado, transparente y con fondo)
    restaurar_frente()
    for o in texto:
        o.hide_render = True
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 1.3
    cam.location = (0.56, 0.33 - 0.105 / 2, 10)
    r.resolution_x = r.resolution_y = 1024
    render(f"icono_r_fondo_{tema}.png")
    render(f"icono_r_fondo_{tema}_transparente.png", transparente=True)
    for o in texto:
        o.hide_render = False

restaurar_frente()
aplicar_tema("claro")
