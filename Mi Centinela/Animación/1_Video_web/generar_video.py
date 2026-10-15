# Genera los videos web de la animación del ojo de Mi Centinela.
#   - WebM (VP9) con fondo transparente: para Chrome, Edge, Firefox y Android.
#   - MP4 (H.264) sobre fondo blanco: respaldo para Safari / iPhone.
#   - PNG del primer cuadro: imagen de portada (poster) mientras carga el video.
# Uso (variante: completo | escudo):
#   cd "Mi Centinela/Animación"
#   blender --background mi_centinela_animacion.blend --python 1_Video_web/generar_video.py -- completo
import bpy
import os
import shutil
import sys

variante = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "completo"
AQUI = os.path.join(os.path.dirname(bpy.data.filepath), "1_Video_web")
SALIDA = os.path.join(AQUI, "logo_completo" if variante == "completo" else "solo_escudo")
NOMBRE = "mi_centinela_completo" if variante == "completo" else "mi_centinela_escudo"
CUADROS = os.path.join(AQUI, f"_cuadros_{variante}")
FONDO_MP4 = (1.0, 1.0, 1.0)

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
