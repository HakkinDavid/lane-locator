Dataset: https://github.com/biankatpas/Cracks-and-Potholes-in-Road-Images-Dataset/tree/master/Dataset

### Instrucciones
Los modelos fueron serializados en formato .pth utilizando PyTorch. Se almacenó un checkpoint con los pesos del modelo (state_dict) y metadatos necesarios para la inferencia, como nombre del modelo, tamaño de entrada, umbral de binarización y parámetros de normalización. La deserialización se realiza con torch.load(...), seguida de la reconstrucción de la arquitectura y la carga de pesos mediante load_state_dict(...).

#### Para arrancar el sistema
- Clonar el repositorio.
- Backend:
  - Entrar a la carpeta `backend`.
  - Activar el entorno virtual de Python 3.12.3.
  - Instalar las dependencias de PiP del backend (`requirements.txt`).
  - Ejecutar con `fastapi run --host 0.0.0.0 --port 8000`.
- Frontend:
  - Entrar a la carpeta `frontend`.
  - Instalar dependencias con `npm i`.
  - Ejecutar con `npm run build && npm run preview -- --open`.
- Uso:
  - Ingresar a la dirección URL proporcionada por el frontend.
  - Si compete, ingresar la URL del endpoint backend (necesario si es en otro dominio).
  - Subir una fotografía de un camino o encender la cámara web.
  - Disfrute.
