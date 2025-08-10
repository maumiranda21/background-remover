import streamlit as st
from PIL import Image
import io
import os
import zipfile
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Try to import rembg; show helpful install message if missing.
try:
    from rembg import remove
except Exception as e:
    remove = None
    _rembg_import_error = e

st.set_page_config(page_title="Auto Background Remover", layout="centered")

st.title("Auto Background Remover — Batch & Zip export (Parallel)")
st.write(
    "Sube imágenes (jpg, png, webp, etc.). La app removerá el fondo automáticamente sin intervención humana. "
    "Procesa varias imágenes en paralelo para mayor velocidad. "
    "Si subes varias, puedes descargarlas en un ZIP. Mantén nombres originales si lo deseas."
)

if remove is None:
    st.error(
        "La librería `rembg` no está instalada en el entorno. Para ejecutar esta app debes instalar las dependencias:\n\n"
        "`pip install -r requirements.txt`\n\n"
        "En entornos como Streamlit Cloud, añade `requirements.txt` a tu repo y desplega desde GitHub.\n\n"
        f"Import error: {_rembg_import_error}"
    )
    st.stop()

uploaded = st.file_uploader("Sube una o varias imágenes", type=["png","jpg","jpeg","webp","bmp","tiff"], accept_multiple_files=True)

col1, col2 = st.columns([1,1])
with col1:
    keep_names = st.checkbox("Mantener nombres originales (añadir sufijo '_nobg' si hay conflicto)", value=True)
with col2:
    out_format = st.selectbox("Formato de salida", ("png (transparente)", "webp", "png (no-transparency)"))
    if out_format.startswith("png (no"):
        save_mode = "PNG_NO_ALPHA"
    elif out_format.startswith("webp"):
        save_mode = "WEBP"
    else:
        save_mode = "PNG_ALPHA"

process_btn = st.button("Procesar imágenes ahora (Paralelo)")

def process_image(up_file):
    try:
        raw = up_file.read()
        out_bytes = remove(raw)
        img = Image.open(io.BytesIO(out_bytes)).convert("RGBA")
        stem = os.path.splitext(up_file.name)[0]
        if save_mode == "WEBP":
            out_ext = ".webp"
        else:
            out_ext = ".png"
        if keep_names:
            candidate = f"{stem}_nobg{out_ext}"
        else:
            ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
            candidate = f"image_{ts}{out_ext}"
        return (candidate, img, None)
    except Exception as e:
        return (up_file.name, None, str(e))

if process_btn and uploaded:
    processed_files = []
    errors = []
    progress = st.progress(0)
    n = len(uploaded)
    with ThreadPoolExecutor(max_workers=min(4, n)) as executor:
        futures = {executor.submit(process_image, up): up.name for up in uploaded}
        for i, future in enumerate(as_completed(futures), start=1):
            fname, img, err = future.result()
            if err:
                errors.append((fname, err))
            else:
                processed_files.append((fname, img))
            progress.progress(int(i / n * 100))
    progress.empty()

    if errors:
        st.warning("Algunas imágenes fallaron al procesarse:")
        for name, err in errors:
            st.write(f"- {name}: {err}")
    if processed_files:
        st.success(f"Procesadas {len(processed_files)} imagen(es).")
        st.subheader("Previsualización y descargas individuales")
        for fname, pil_img in processed_files:
            st.image(pil_img, caption=fname, use_column_width=True)
            buf = io.BytesIO()
            if save_mode == "WEBP":
                pil_img.save(buf, format="WEBP", quality=95, lossless=True)
            else:
                if save_mode == "PNG_NO_ALPHA":
                    rgb = Image.new("RGB", pil_img.size, (255,255,255))
                    rgb.paste(pil_img, mask=pil_img.split()[3])
                    rgb.save(buf, format="PNG", optimize=True)
                else:
                    pil_img.save(buf, format="PNG", optimize=True)
            buf.seek(0)
            st.download_button(label=f"Descargar {fname}", data=buf, file_name=fname, mime="image/png")

        if len(processed_files) > 1:
            st.subheader("Descargar todas en ZIP")
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                existing = set()
                for fname, pil_img in processed_files:
                    safe_name = fname
                    j = 1
                    base_name = os.path.splitext(safe_name)[0]
                    ext = os.path.splitext(safe_name)[1]
                    while safe_name in existing:
                        safe_name = f"{base_name}_{j}{ext}"
                        j += 1
                    existing.add(safe_name)
                    img_bytes = io.BytesIO()
                    if save_mode == "WEBP":
                        pil_img.save(img_bytes, format="WEBP", quality=95, lossless=True)
                    else:
                        if save_mode == "PNG_NO_ALPHA":
                            rgb = Image.new("RGB", pil_img.size, (255,255,255))
                            rgb.paste(pil_img, mask=pil_img.split()[3])
                            rgb.save(img_bytes, format="PNG", optimize=True)
                        else:
                            pil_img.save(img_bytes, format="PNG", optimize=True)
                    img_bytes.seek(0)
                    zf.writestr(safe_name, img_bytes.read())
            zip_buf.seek(0)
            st.download_button("Descargar ZIP con todas las imágenes", zip_buf, file_name="processed_images.zip", mime="application/zip")
else:
    if not uploaded:
        st.info("Sube una o varias imágenes para comenzar.")