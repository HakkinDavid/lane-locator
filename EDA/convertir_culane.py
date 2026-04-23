from pathlib import Path
import shutil
import cv2
import numpy as np

culane_root = Path(r"C:\Users\Rafael\Documents\GitHub\lane-locator\Dataset\CULane")
salida_root = Path(r"C:\Users\Rafael\Documents\GitHub\lane-locator\Dataset\CULane_formateado")

nombre_raw = "raw.jpg"
nombre_lane = "lane.jpg"
nombre_crack = "crack.jpg"
nombre_pothhole = "pothhole.jpg"

usar_lineas_si_falla_area = True
grosor_linea_fallback = 12
muestras_interpolacion = 150

def leer_carriles(ruta_txt):
    carriles = []
    with open(ruta_txt, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            valores = [float(v) for v in linea.split()]
            if len(valores) < 4:
                continue
            puntos = np.array(valores, dtype=np.float32).reshape(-1, 2)
            puntos = puntos[(puntos[:, 0] >= 0) & (puntos[:, 1] >= 0)]
            if len(puntos) >= 2:
                puntos = puntos[np.argsort(puntos[:, 1])]
                carriles.append(puntos)
    return carriles

def interp_x_en_y(carril, ys):
    carril = carril[np.argsort(carril[:, 1])]
    y = carril[:, 1]
    x = carril[:, 0]

    y_unicos, indices = np.unique(y, return_index=True)
    x_unicos = x[indices]

    if len(y_unicos) < 2:
        return np.full_like(ys, np.nan, dtype=np.float32)

    resultado = np.interp(ys, y_unicos, x_unicos, left=np.nan, right=np.nan)
    mascara_fuera = (ys < y_unicos.min()) | (ys > y_unicos.max())
    resultado[mascara_fuera] = np.nan
    return resultado.astype(np.float32)

def x_en_y_referencia(carril, y_ref):
    ys = np.array([y_ref], dtype=np.float32)
    xs = interp_x_en_y(carril, ys)
    return xs[0]

def seleccionar_par_central(carriles, ancho, alto):
    centro = ancho / 2.0
    y_ref = alto - 10

    candidatos = []
    for i, carril in enumerate(carriles):
        x_ref = x_en_y_referencia(carril, y_ref)
        if np.isnan(x_ref):
            y_alt = min(alto - 1, np.max(carril[:, 1]))
            x_ref = x_en_y_referencia(carril, y_alt)
        if not np.isnan(x_ref):
            candidatos.append((i, float(x_ref)))

    if len(candidatos) < 2:
        return None

    izquierdos = [(i, x) for i, x in candidatos if x < centro]
    derechos = [(i, x) for i, x in candidatos if x > centro]

    if izquierdos and derechos:
        idx_izq = max(izquierdos, key=lambda t: t[1])[0]
        idx_der = min(derechos, key=lambda t: t[1])[0]
        return carriles[idx_izq], carriles[idx_der]

    candidatos_ordenados = sorted(candidatos, key=lambda t: t[1])
    mejor_par = None
    mejor_puntaje = float("inf")

    for a in range(len(candidatos_ordenados)):
        for b in range(a + 1, len(candidatos_ordenados)):
            i1, x1 = candidatos_ordenados[a]
            i2, x2 = candidatos_ordenados[b]
            mitad = (x1 + x2) / 2.0
            puntaje = abs(mitad - centro)
            if puntaje < mejor_puntaje:
                mejor_puntaje = puntaje
                mejor_par = (carriles[i1], carriles[i2])

    return mejor_par

def crear_mascara_area(carriles, alto, ancho, muestras=150):
    if len(carriles) < 2:
        return None

    par = seleccionar_par_central(carriles, ancho, alto)
    if par is None:
        return None

    carril_izq, carril_der = par

    y_superior = max(np.min(carril_izq[:, 1]), np.min(carril_der[:, 1]))
    y_inferior = min(np.max(carril_izq[:, 1]), np.max(carril_der[:, 1]))

    if y_inferior - y_superior < 30:
        return None

    ys = np.linspace(y_superior, y_inferior, muestras).astype(np.float32)
    xs_izq = interp_x_en_y(carril_izq, ys)
    xs_der = interp_x_en_y(carril_der, ys)

    validos = ~np.isnan(xs_izq) & ~np.isnan(xs_der) & (xs_izq < xs_der)
    if np.count_nonzero(validos) < 20:
        return None

    ys = ys[validos]
    xs_izq = xs_izq[validos]
    xs_der = xs_der[validos]

    puntos_izq = np.stack([xs_izq, ys], axis=1)
    puntos_der = np.stack([xs_der, ys], axis=1)[::-1]
    poligono = np.vstack([puntos_izq, puntos_der])

    poligono[:, 0] = np.clip(poligono[:, 0], 0, ancho - 1)
    poligono[:, 1] = np.clip(poligono[:, 1], 0, alto - 1)
    poligono = np.round(poligono).astype(np.int32)

    mascara = np.zeros((alto, ancho), dtype=np.uint8)
    cv2.fillPoly(mascara, [poligono], 255)
    return mascara

def crear_mascara_lineas(carriles, alto, ancho, grosor=12):
    mascara = np.zeros((alto, ancho), dtype=np.uint8)
    for carril in carriles:
        puntos = np.round(carril).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(mascara, [puntos], False, 255, thickness=grosor)
    return mascara

def nombre_carpeta_desde_relativa(ruta_relativa):
    base = ruta_relativa.with_suffix("")
    partes = list(base.parts)
    nombre = "__".join(partes)
    nombre = nombre.replace(" ", "_")
    return nombre

def crear_imagen_negra(alto, ancho):
    return np.zeros((alto, ancho), dtype=np.uint8)

def buscar_imagenes_recursivo(root):
    extensiones = ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]
    imagenes = []
    for patron in extensiones:
        imagenes.extend(root.rglob(patron))
    return sorted(set(imagenes))

def procesar_imagen(ruta_imagen, culane_root, salida_root):
    ruta_txt = ruta_imagen.with_suffix(".lines.txt")
    if not ruta_txt.exists():
        return False, "sin_txt"

    imagen = cv2.imread(str(ruta_imagen))
    if imagen is None:
        return False, "imagen_invalida"

    alto, ancho = imagen.shape[:2]
    carriles = leer_carriles(ruta_txt)

    if len(carriles) == 0:
        return False, "sin_carriles"

    mascara_lane = crear_mascara_area(carriles, alto, ancho, muestras=muestras_interpolacion)

    if mascara_lane is None and usar_lineas_si_falla_area:
        mascara_lane = crear_mascara_lineas(carriles, alto, ancho, grosor=grosor_linea_fallback)

    if mascara_lane is None:
        return False, "no_se_pudo_generar_mascara"

    mascara_crack = crear_imagen_negra(alto, ancho)
    mascara_pothhole = crear_imagen_negra(alto, ancho)

    ruta_relativa = ruta_imagen.relative_to(culane_root)
    nombre_carpeta = nombre_carpeta_desde_relativa(ruta_relativa)
    carpeta_salida = salida_root / nombre_carpeta
    carpeta_salida.mkdir(parents=True, exist_ok=True)

    shutil.copy2(ruta_imagen, carpeta_salida / nombre_raw)
    cv2.imwrite(str(carpeta_salida / nombre_lane), mascara_lane)
    cv2.imwrite(str(carpeta_salida / nombre_crack), mascara_crack)
    cv2.imwrite(str(carpeta_salida / nombre_pothhole), mascara_pothhole)

    return True, "ok"

def main():
    print(f"Buscando en: {culane_root}")
    print(f"Existe la carpeta: {culane_root.exists()}")

    if not culane_root.exists():
        print("La ruta de CULane no existe.")
        return

    salida_root.mkdir(parents=True, exist_ok=True)

    imagenes = buscar_imagenes_recursivo(culane_root)

    print(f"Total de imágenes encontradas recursivamente: {len(imagenes)}")
    if len(imagenes) > 0:
        print("Primeras 5 imágenes encontradas:")
        for ruta in imagenes[:5]:
            print(ruta)

    total = 0
    ok = 0
    sin_txt = 0
    imagen_invalida = 0
    sin_carriles = 0
    sin_mascara = 0

    for ruta_imagen in imagenes:
        total += 1
        exito, estado = procesar_imagen(ruta_imagen, culane_root, salida_root)

        if exito:
            ok += 1
        elif estado == "sin_txt":
            sin_txt += 1
        elif estado == "imagen_invalida":
            imagen_invalida += 1
        elif estado == "sin_carriles":
            sin_carriles += 1
        else:
            sin_mascara += 1

        if total % 100 == 0:
            print(f"Procesadas: {total} | Exitosas: {ok}")

    print("\nResumen final")
    print(f"Total encontradas: {total}")
    print(f"Convertidas correctamente: {ok}")
    print(f"Sin .lines.txt: {sin_txt}")
    print(f"Imagen inválida: {imagen_invalida}")
    print(f"Sin carriles válidos: {sin_carriles}")
    print(f"Sin máscara generada: {sin_mascara}")
    print(f"Salida en: {salida_root}")

if __name__ == "__main__":
    main()