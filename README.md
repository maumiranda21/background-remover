# Auto Background Remover — Fixed requirements for Streamlit Cloud

Se actualizó `requirements.txt` para evitar conflictos de dependencias en entornos con Python 3.13 (por ejemplo Streamlit Cloud).
- ahora usamos `rembg[cpu]==2.0.67` (compatible con Python 3.10–3.13), que instalará una versión de `onnxruntime` compatible para CPU.
- elimina el pin conflictivo a `onnxruntime` que causaba el error.
