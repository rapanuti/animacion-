# Genera los videos web de la animación del ojo de Mi Centinela.
#   - WebM (VP9) con fondo transparente: para Chrome, Edge, Firefox y Android.
#   - MP4 (H.264) sobre fondo blanco (o azul oscuro en la versión oscura): respaldo para Safari / iPhone.
#   - PNG del primer cuadro: imagen de portada (poster) mientras carga el video.
# Uso (variante: completo | oscuro | escudo; "oscuro" = logo completo con texto claro para fondo oscuro):
#   cd "Mi Centinela/Animación"
#   blender --background mi_centinela_animacion.blend --python 1_Video_web/generar_video.py -- completo
import bpy
import os
import shutil
import sys

variante = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "completo"
AQUI = os.path.join(os.path.dirname(bpy.data.filepath), "1_Video_web")
CARPETA, NOMBRE = {
    "completo": ("logo_completo", "mi_centinela_completo"),
    "oscuro": ("logo_completo_fondo_oscuro", "mi_centinela_completo_oscuro"),
    "escudo": ("solo_escudo", "mi_centinela_escudo"),
}[variante]
SALIDA = os.path.join(AQUI, CARPETA)
CUADROS = os.path.join(AQUI, f"_cuadros_{variante}")
FONDO_MP4 = (15 / 255, 30 / 255, 54 / 255) if variante == "oscuro" else (1.0, 1.0, 1.0)   # #0f1e36 / blanco
# Versión oscura: el escudo no cambia, solo el texto se aclara (mismos colores que el SVG)
TEXTO_OSCURO = {"Mi": "#a9b8cc", "Centinela": "#ffffff", "Punto": "#3d8bff"}


def lin(hexstr):
    h = hexstr.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


scene = bpy.context.scene
cam = scene.camera
if variante == "escudo":
    for nombre in ("Texto_Mi", "Texto_Centinela", "Punto_i"):
        bpy.data.objects[nombre].hide_render = True
    cam.location.x, cam.location.y = 0.0, -0.065
    cam.data.ortho_scale = 1.45
    ancho, alto = 600, 700
else:
    ancho, alto = 1440, 380
if variante == "oscuro":
    for nombre, color in TEXTO_OSCURO.items():
        bsdf = next(n for n in bpy.data.materials[nombre].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = lin(color)

# ---------------------------------------------------------------- 1) cuadros PNG transparentes
r = scene.render
r.resolution_x, r.resolution_y, r.resolution_percentage = ancho, alto, 100
r.film_transparent = True
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGBA"
shutil.rmtree(CUADROS, ignore_errors=True)
os.makedirs(CUADROS)
r.filepath = os.path.join(CUADROS, "cuadro_")
bpy.ops.render.render(animation=True)
archivos = sorted(f for f in os.listdir(CUADROS) if f.endswith(".png"))
os.makedirs(SALIDA, exist_ok=True)
shutil.copy(os.path.join(CUADROS, archivos[0]), os.path.join(SALIDA, f"{NOMBRE}_portada.png"))

# ---------------------------------------------------------------- 2) codificar con el editor de video
enc = bpy.data.scenes.new("Codificar")
er = enc.render
er.resolution_x, er.resolution_y, er.resolution_percentage = ancho, alto, 100
er.fps = scene.render.fps
enc.frame_start, enc.frame_end = 1, len(archivos)
enc.view_settings.view_transform = "Standard"
sed = enc.sequence_editor_create()
tiras = sed.strips if hasattr(sed, "strips") else sed.sequences
img = tiras.new_image(name="cuadros", filepath=os.path.join(CUADROS, archivos[0]), channel=2, frame_start=1)
for f in archivos[1:]:
    img.elements.append(f)
img.blend_type = "ALPHA_OVER"


def codificar(ruta, formato, codec, color):
    ims = er.image_settings
    if hasattr(ims, "media_type"):
        ims.media_type = "VIDEO"
    ims.file_format = "FFMPEG"
    er.ffmpeg.format = formato
    er.ffmpeg.codec = codec
    er.ffmpeg.constant_rate_factor = "HIGH"
    ims.color_mode = color
    er.filepath = ruta
    with bpy.context.temp_override(scene=enc):
        bpy.ops.render.render(animation=True, scene=enc.name)


codificar(os.path.join(SALIDA, f"{NOMBRE}.webm"), "WEBM", "WEBM", "RGBA")
fondo = tiras.new_effect(name="fondo", type="COLOR", channel=1, frame_start=1, length=len(archivos))
fondo.color = FONDO_MP4
er.film_transparent = False
codificar(os.path.join(SALIDA, f"{NOMBRE}.mp4"), "MPEG4", "H264", "RGB")

shutil.rmtree(CUADROS, ignore_errors=True)
print("VIDEO_LISTO", variante, sorted(os.listdir(SALIDA)))
