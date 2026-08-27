import math
import json
import os

def calcular_cortes_caja():
    print("=== Calculadora Automática Acústica MDF (Slot Port L + Deflectores 45°) ===\n")
    
    archivo_json = "parametros_ts.json"
    
    # Carga de parámetros TS
    if not os.path.exists(archivo_json):
        print(f"[!] Error crítico: No se encontró el archivo '{archivo_json}'.")
        return

    try:
        with open(archivo_json, 'r') as f:
            ts_data = json.load(f)
            vas = float(ts_data['Vas'])
            qts = float(ts_data['Qts'])
            fs = float(ts_data['Fs'])
            sd = float(ts_data['Sd'])
            print(f"[+] Parámetros importados: Vas={vas}L, Qts={qts}, Fs={fs}Hz, Sd={sd}cm2\n")
    except Exception as e:
        print(f"[!] Error al leer JSON: {e}")
        return

    # Entrada de variables de diseño de gabinete
    try:
        espesor_mdf_mm = float(input("Espesor del MDF (mm): "))
        vol_crossover = float(input("Volumen del crossover (Litros): "))
        vol_driver = float(input("Volumen desplazado por el imán/cono (Litros): "))
        ganancia_napa = float(input("% de ganancia de volumen aparente por napa (ej. 15): "))
    except ValueError:
        print("Error: Ingresa únicamente valores numéricos.")
        return

    espesor_cm = round(espesor_mdf_mm / 10.0, 1)
    
    # Alineamiento Acústico Objetivo
    vb_neto_litros = 15.0 * (qts ** 2.87) * vas
    fb_target = fs
    print(f"\n[+] Volumen Acústico Neto Objetivo: {vb_neto_litros:.2f} Litros")
    print(f"[+] Frecuencia de Sintonía (Fb) anclada a Fs: {fb_target:.2f} Hz")

    area_puerto_cm2 = sd * 0.30
    
    # Bucle Iterativo
    phi = 1.61803398875
    root_phi = math.sqrt(phi)
    factor_napa = 1.0 + (ganancia_napa / 100.0)
    
    vol_bruto_base = vb_neto_litros + vol_crossover + vol_driver
    vol_puerto_total_litros = 0.0
    
    w_int = 0.0
    h_puerto_cm = 0.0
    l_puerto_cm = 0.0
    
    for _ in range(15):
        vb_fisico_litros = (vol_bruto_base + vol_puerto_total_litros) / factor_napa
        vol_cm3 = vb_fisico_litros * 1000.0
        
        w_int = (vol_cm3 / (phi ** 1.5)) ** (1.0 / 3.0)
        h_puerto_cm = area_puerto_cm2 / w_int
        
        l_puerto_cm = (30000.0 * area_puerto_cm2) / (vb_neto_litros * (fb_target ** 2)) - (0.823 * math.sqrt(area_puerto_cm2))
        if l_puerto_cm < 0: l_puerto_cm = 0.1
        
        vol_aire_puerto_cm3 = w_int * h_puerto_cm * l_puerto_cm
        vol_madera_puerto_cm3 = w_int * espesor_cm * l_puerto_cm
        vol_puerto_total_litros = (vol_aire_puerto_cm3 + vol_madera_puerto_cm3) / 1000.0

    # Redondeo metrológico
    w_int = round(w_int, 1)
    d_int = round(w_int * root_phi, 1)
    h_int = round(w_int * phi, 1)
    
    h_puerto_cm = round(h_puerto_cm, 1)
    l_puerto_cm = round(l_puerto_cm, 1)
    
    print("\n--- Dimensiones del Laberinto Helmholtz Calculado ---")
    print(f"Alto de ranura:  {h_puerto_cm:.1f} cm")
    print(f"Ancho (piso):    {w_int:.1f} cm")
    print(f"Largo total:     {l_puerto_cm:.1f} cm")
    
    print("\n--- Dimensiones Internas Físicas ---")
    print(f"Ancho (W):       {w_int:.1f} cm")
    print(f"Profundidad (D): {d_int:.1f} cm")
    print(f"Alto (H):        {h_int:.1f} cm")
    
    # Cálculo de Paneles (Chasis Exterior)
    h_ext = round(h_int + (2 * espesor_cm), 1)
    d_ext = round(d_int + (2 * espesor_cm), 1)
    
    print("\n--- Lista de Cortes MDF (Caja Principal) ---")
    print(f"2x Laterales:          {h_ext:.1f} cm x {d_ext:.1f} cm")
    print(f"2x Superior/Inferior:  {w_int:.1f} cm x {d_ext:.1f} cm")
    print(f"2x Frontal/Trasero:    {h_int:.1f} cm x {w_int:.1f} cm")
    
    # Lógica del Puerto en L y Deflectores a 45°
    print("\n--- Lista de Cortes MDF (Laberinto interno y Codo) ---")
    
    # Distancia máxima horizontal dejando el hueco trasero del tamaño h_puerto_cm para flujo
    largo_maximo_base = d_int - h_puerto_cm
    
    if l_puerto_cm <= largo_maximo_base:
        # Puerto recto
        l_panel_base = round(l_puerto_cm - espesor_cm, 1)
        print(f"1x Techo de Ranura Recta: {w_int:.1f} cm x {l_panel_base:.1f} cm")
        print("[i] El puerto no requiere doblarse en L (cabe en el piso).")
    else:
        # Puerto en L
        l_panel_base = round(largo_maximo_base - espesor_cm, 1)
        l_panel_vertical = round(l_puerto_cm - largo_maximo_base, 1)
        
        # Deflectores a 45° para mantener la sección H constante en el codo
        cateto = h_puerto_cm * (1.0 - (math.sqrt(2.0) / 2.0))
        deflector_face = round(cateto * math.sqrt(2.0), 2)
        
        print(f"1x Techo de Ranura (Piso):  {w_int:.1f} cm x {l_panel_base:.1f} cm")
        print(f"1x Pared de Ranura (Sube):  {w_int:.1f} cm x {l_panel_vertical:.1f} cm")
        print(f"2x Deflectores a 45°:       {w_int:.1f} cm x {deflector_face:.2f} cm (Ancho interno x Cara diagonal visible)")
        print("[i] Deflectores: Listones con ambos cantos cortados a 45° para pegar en los dos vértices del codo de 90°.")

if __name__ == "__main__":
    calcular_cortes_caja()