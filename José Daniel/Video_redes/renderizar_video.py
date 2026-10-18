# Renderiza el video para redes de José Daniel: MP4 (H.264) vertical 1080 x 1920, 24 fps, 12 s,
# más una portada PNG (cuadro con el botón de YouTube).
# 1) cuadros PNG en render/_cuadros (si se corta, al volver a correrlo sigue donde quedó)
# 2) los une en el MP4 con el editor de video de Blender (rápido, no vuelve a renderizar)
# Uso (no toca la escena abierta):
#   cd "José Daniel/Video_redes" && blender --background video_redes.blend --python renderizar_video.py
import bpy
import os
import shutil

AQUI = os.path.dirname(bpy.data.filepath)
SALIDA = os.path.join(AQUI, "render")
CUADROS = os.path.join(SALIDA, "_cuadros")
VIDEO = os.path.join(SALIDA, "jose_daniel_sigueme_en_youtube.mp4")
MUESTRAS = 16          # 64 tarda 15 s por cuadro en la MX150; 16 tarda 4 s y se ve igual

s = bpy.context.scene
r = s.render
r.resolution_percentage = 100
s.eevee.taa_render_samples = MUESTRAS
os.makedirs(CUADROS, exist_ok=True)

# ---------------------------------------------------------------- 1) cuadros PNG (reanudable)
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGB"
r.use_overwrite = False
r.use_placeholder = True
r.filepath = os.path.join(CUADROS, "cuadro_")
bpy.ops.render.render(animation=True)
archivos = sorted(f for f in os.listdir(CUADROS) if f.endswith(".png") and os.path.getsize(os.path.join(CUADROS, f)) > 0)
assert len(archivos) == s.frame_end - s.frame_start + 1, f"faltan cuadros: {len(archivos)}"
shutil.copy(os.path.join(CUADROS, "cuadro_0250.png"), os.path.join(SALIDA, "jose_daniel_redes_portada.png"))

# ---------------------------------------------------------------- 2) unir en MP4
enc = bpy.data.scenes.new("Codificar")
er = enc.render
er.resolution_x, er.resolution_y, er.resolution_percentage = r.resolution_x, r.resolution_y, 100
er.fps = r.fps
enc.frame_start, enc.frame_end = 1, len(archivos)
enc.view_settings.view_transform = "Standard"
sed = enc.sequence_editor_create()
tiras = sed.strips if hasattr(sed, "strips") else sed.sequences
img = tiras.new_image(name="cuadros", filepath=os.path.join(CUADROS, archivos[0]), channel=1, frame_start=1)
for f in archivos[1:]:
    img.elements.append(f)
ims = er.image_settings
if hasattr(ims, "media_type"):
    ims.media_type = "VIDEO"
ims.file_format = "FFMPEG"
ims.color_mode = "RGB"
er.ffmpeg.format = "MPEG4"
er.ffmpeg.codec = "H264"
er.ffmpeg.constant_rate_factor = "HIGH"
er.ffmpeg.gopsize = 24
er.filepath = VIDEO
with bpy.context.temp_override(scene=enc):
    bpy.ops.render.render(animation=True, scene=enc.name)
print("VIDEO_LISTO", VIDEO, os.path.getsize(VIDEO))
