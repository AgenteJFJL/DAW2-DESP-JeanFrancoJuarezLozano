"""Utilidades de imagen: valida, normaliza a 512x512 PNG y guarda en el volumen."""
import io
import os
import secrets

from PIL import Image, ImageOps, UnidentifiedImageError

LADO = 512
MAX_BYTES = 3 * 1024 * 1024
MAX_PIXELES = 25_000_000
FORMATOS = {"PNG", "JPEG", "WEBP"}


def procesar(fichero):
    """Devuelve (bytes_png, aviso). Lanza ValueError con un mensaje claro si no vale."""
    datos = fichero.read(MAX_BYTES + 1)
    if not datos:
        raise ValueError("Selecciona una imagen.")
    if len(datos) > MAX_BYTES:
        raise ValueError("La imagen pesa más de 3 MB.")
    try:
        img = Image.open(io.BytesIO(datos))
        formato = img.format
        ancho, alto = img.size
        if ancho * alto > MAX_PIXELES:
            raise ValueError("La imagen es demasiado grande (más de 25 megapíxeles).")
        img.load()
    except ValueError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValueError("El fichero no es una imagen válida.")
    if formato not in FORMATOS:
        raise ValueError("Formato no admitido: usa PNG, JPG o WebP (lo ideal, PNG con fondo transparente).")

    img = img.convert("RGBA")
    aviso = None
    if (ancho, alto) != (LADO, LADO):
        aviso = f"La imagen era de {ancho}×{alto} px y se ha ajustado a {LADO}×{LADO} px."
    img = ImageOps.contain(img, (LADO, LADO), Image.LANCZOS)
    lienzo = Image.new("RGBA", (LADO, LADO), (0, 0, 0, 0))
    lienzo.paste(img, ((LADO - img.width) // 2, (LADO - img.height) // 2))
    salida = io.BytesIO()
    lienzo.save(salida, "PNG", optimize=True)        # se reescribe: se pierden metadatos y datos ocultos
    return salida.getvalue(), aviso


def guardar(png, base, carpeta):
    """Guarda con nombre generado (nunca el del usuario) y devuelve ese nombre."""
    nombre = f"{base}-{secrets.token_hex(4)}.png"
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, nombre)
    with open(destino + ".tmp", "wb") as f:
        f.write(png)
    os.replace(destino + ".tmp", destino)
    return nombre
