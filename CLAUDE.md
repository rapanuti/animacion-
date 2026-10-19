# animacion-

Proyecto para trabajar en Blender junto con Claude. El usuario habla español.

## Control de Blender (Claude Bridge)

- Blender 5.2 (snap, `/snap/bin/blender`) en Ubuntu.
- El add-on `blender_bridge/claude_bridge.py` está enlazado (symlink) en
  `~/.config/blender/5.2/scripts/addons/` y activado en las preferencias: al abrir
  Blender con interfaz, escucha en `127.0.0.1:9876`. Panel: Vista 3D > barra lateral (N) > Claude.
- Para ejecutar Python dentro del Blender abierto:
  - `python3 blender_bridge/send.py -c "código"` o `python3 blender_bridge/send.py archivo.py`
  - El espacio de nombres persiste entre llamadas; asignar `result = ...` devuelve su repr.
- Si el puerto no responde, abrir Blender: `setsid nohup blender >/dev/null 2>&1 &`
- Para ver la escena: `bpy.ops.screen.screenshot_area(filepath=...)` con `temp_override`
  sobre el área `VIEW_3D`, o renderizar a un PNG, y luego leer la imagen.
- Trabajo sin interfaz: `blender --background archivo.blend --python script.py`.

## Estructura: una carpeta por diseño

**Regla del usuario:** antes de empezar cualquier trabajo en Blender, preguntar en qué
proyecto (carpeta) se va a trabajar (Mi Centinela, José Daniel, Rapanuti, Celulares, Cámaras o uno nuevo), salvo que el
usuario ya lo haya dicho en ese mensaje. Todo lo que se genere (.blend, renders, exportaciones)
va dentro de la carpeta de ese proyecto, y antes de construir se abre su `.blend` en Blender.

- `Mi Centinela/`: logo (escudo con ojo + texto). `logo_mi_centinela.py` arma la escena,
  `exportar_impresion_3d.py` genera `Impresión 3D/` (3MF, STL, OBJ, PLY, .blend, LEEME)
  y el ZIP para entregar a quien imprime. Las fuentes Noto Sans van empaquetadas en el .blend.
  `Animación/`: `mi_centinela_animacion.blend` (parpadeo + mirada, 6 s en bucle, creado por
  `animar_ojo.py` sobre el logo base) y tres formatos web, cada uno en `logo_completo/`,
  `logo_completo_fondo_oscuro/` (solo cambia el texto: Mi #a9b8cc, Centinela #ffffff,
  punto #3d8bff) y `solo_escudo/`: `1_Video_web/` (WebM transparente + MP4), `2_SVG_animado/` (CSS) y
  `3_Modelo_3D_GLB/` (model-viewer). Cada uno tiene su script `generar_*.py` y `ejemplo.html`.
  Para ver los ejemplos: launch config `animacion-mi-centinela` (http.server en el puerto 8765).
  El navegador interno no tiene WebGL: el GLB se verifica reimportándolo en Blender.
- `José Daniel/`: personaje (dibujo de José Daniel en `referencia.png`). `personaje_jose_daniel.py`
  lo arma con controles para animar; también se imprime en 3D.
  `Video_redes/`: video vertical 1080x1920 de 12 s ("Sígueme en YouTube"). `crear_video_redes.py`
  copia a José desde `jose_daniel.blend` (no lo modifica), arma el paisaje, la animación (camina a
  saltitos, salta, habla) y los textos pegados a la cámara (Montserrat Bold en `fuentes/`); constante
  `CANAL` para el @ del canal. `renderizar_video.py` genera `render/` (MP4 + portada). Blender con
  interfaz se cierra a veces: estos scripts corren bien con `blender --background`.
- `Rapanuti/`: logo (ícono "R" de 3 piezas + "Rapanuti" en Montserrat Medium, tracking -3,5 %,
  azul #132136; fuentes en `fuentes/`, descargadas de JulietaUla/Montserrat). `logo_rapanuti.py`
  lo arma (geometría del ícono en píxeles de `referencia.png`, 100 px = 1 unidad) y define
  `aplicar_tema("claro"|"oscuro")` con colores de material calibrados; `renderizar.py` y
  `exportar_svg.py` generan `render/` y `svg/`. Vista previa: launch config `rapanuti` (puerto 8766).
- `Celulares/`: modelos de celulares para Blender. `LISTA - Modelos de celulares para Blender.txt`
  (búsqueda de modelos gratis y de pago). `modelos/` guarda los descargados (+ `CREDITOS.txt`; el
  usuario los baja desde Opera porque Sketchfab pide sesión). `escena_celular.py` importa
  `modern_generic_smartphone.glb` (Ottto3d, CC BY 4.0) bajo el vacío `Celular` con estudio y
  cámara, y guarda `celulares.blend` (material en modo DITHERED: en BLENDED se ve transparente).
  `exportar_web.py` genera `web/celular.glb` para el sitio de MiCentinela (website/public/models/):
  origen en el centro de la pantalla, 1 unidad = ancho de pantalla, material opaco, texturas WebP
  1024. Se corre con `blender --background --python Celulares/exportar_web.py`.
- `Cámaras/`: cámara domo de seguridad para El Ojo de Odin, modelada desde cero (sin licencias de
  terceros). `camara_domo.py` arma la escena (piezas Base con anillo azul de marca, Domo de vidrio
  ahumado y Ojo, el módulo del lente con su origen en el centro de giro y mirando a -Y), guarda
  `camara_domo.blend`, renderiza `render/camara_domo.png` y exporta `web/camara_domo.glb` para el
  sitio (website/public/models/). Blender está en español: busca nodos por tipo, no por nombre.
- Cada diseño nuevo sigue el mismo patrón: `<nombre>.blend`, script que lo arma, `render/`
  y, si se imprime, `Impresión 3D/` + ZIP.
