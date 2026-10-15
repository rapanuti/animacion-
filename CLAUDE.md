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
proyecto (carpeta) se va a trabajar (Mi Centinela, José Daniel o uno nuevo), salvo que el
usuario ya lo haya dicho en ese mensaje. Todo lo que se genere (.blend, renders, exportaciones)
va dentro de la carpeta de ese proyecto, y antes de construir se abre su `.blend` en Blender.

- `Mi Centinela/`: logo (escudo con ojo + texto). `logo_mi_centinela.py` arma la escena,
  `exportar_impresion_3d.py` genera `Impresión 3D/` (3MF, STL, OBJ, PLY, .blend, LEEME)
  y el ZIP para entregar a quien imprime. Las fuentes Noto Sans van empaquetadas en el .blend.
  `Animación/`: `mi_centinela_animacion.blend` (parpadeo + mirada, 6 s en bucle, creado por
  `animar_ojo.py` sobre el logo base) y tres formatos web, cada uno en `logo_completo/` y
  `solo_escudo/`: `1_Video_web/` (WebM transparente + MP4), `2_SVG_animado/` (CSS) y
  `3_Modelo_3D_GLB/` (model-viewer). Cada uno tiene su script `generar_*.py` y `ejemplo.html`.
  Para ver los ejemplos: launch config `animacion-mi-centinela` (http.server en el puerto 8765).
  El navegador interno no tiene WebGL: el GLB se verifica reimportándolo en Blender.
- `José Daniel/`: personaje (dibujo de José Daniel en `referencia.png`). `personaje_jose_daniel.py`
  lo arma con controles para animar; también se imprime en 3D.
- Cada diseño nuevo sigue el mismo patrón: `<nombre>.blend`, script que lo arma, `render/`
  y, si se imprime, `Impresión 3D/` + ZIP.
