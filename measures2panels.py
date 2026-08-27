import math
import json
import os
import csv

def calcular_cortes_caja():
    print("=== Calculadora Automática Acústica MDF (Slot Port L + Exportación CSV) ===\n")
    
    archivo_json = "parametros_ts.json"
    
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
            prefijo = ts_data.get('PrefijoArchivo', 'Gabinete')
            print(f"[+] Parámetros importados: Vas={vas}L, Qts={qts}, Fs={fs}Hz, Sd={sd}cm2\n")
    except Exception as e:
        print(f"[!] Error al leer JSON: {e}")
        return

    try:
        espesor_mdf_mm = float(input("Espesor del MDF (mm): "))
        vol_crossover = float(input("Volumen del crossover (Litros): "))
        vol_driver = float(input("Volumen desplazado por el imán/cono (Litros): "))
        ganancia_napa = float(input("% de ganancia de volumen aparente por napa (ej. 15): "))
    except ValueError:
        print("Error: Ingresa únicamente valores numéricos.")
        return

    espesor_cm = round(espesor_mdf_mm / 10.0, 1)
    
    vb_neto_litros = 15.0 * (qts ** 2.87) * vas
    fb_target = fs
    print(f"\n[+] Volumen Acústico Neto Objetivo: {vb_neto_litros:.2f} Litros")
    print(f"[+] Frecuencia de Sintonía (Fb) anclada a Fs: {fb_target:.2f} Hz")

    area_puerto_cm2 = sd * 0.30
    
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

    w_int = round(w_int, 1)
    d_int = round(w_int * root_phi, 1)
    h_int = round(w_int * phi, 1)
    h_puerto_cm = round(h_puerto_cm, 1)
    l_puerto_cm = round(l_puerto_cm, 1)
    
    h_ext = round(h_int + (2 * espesor_cm), 1)
    d_ext = round(d_int + (2 * espesor_cm), 1)
    
    # --- Matriz de Cortes para Exportación ---
    cortes = [
        ["2x Laterales", h_ext, d_ext],
        ["2x Superior/Inferior", w_int, d_ext],
        ["2x Frontal/Trasero", h_int, w_int]
    ]
    
    largo_maximo_base = d_int - h_puerto_cm
    estado_puerto = ""
    
    if l_puerto_cm <= largo_maximo_base:
        l_panel_base = round(l_puerto_cm - espesor_cm, 1)
        cortes.append(["1x Techo de Ranura Recta", w_int, l_panel_base])
        estado_puerto = "El puerto no requiere doblarse en L (cabe en el piso)."
    else:
        l_panel_base = round(largo_maximo_base - espesor_cm, 1)
        l_panel_vertical = round(l_puerto_cm - largo_maximo_base, 1)
        
        cateto = h_puerto_cm * (1.0 - (math.sqrt(2.0) / 2.0))
        deflector_face = round(cateto * math.sqrt(2.0), 2)
        
        cortes.append(["1x Techo de Ranura (Piso)", w_int, l_panel_base])
        cortes.append(["1x Pared de Ranura (Sube)", w_int, l_panel_vertical])
        cortes.append(["2x Deflectores a 45 grados", w_int, deflector_face])
        estado_puerto = "Deflectores: Listones con ambos cantos cortados a 45 grados para pegar en los dos vértices del codo."

    # --- Generación de Archivo CSV ---
    archivo_csv_paneles = f"{prefijo}_panels.csv"
    try:
        with open(archivo_csv_paneles, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Panel", "Ancho_cm", "Largo_o_Cara_cm"])
            for corte in cortes:
                writer.writerow(corte)
        print(f"\n[+] Matriz de paneles exportada exitosamente a '{archivo_csv_paneles}'")
    except Exception as e:
        print(f"\n[!] Error al exportar CSV de paneles: {e}")

    # --- Impresión en Consola ---
    print("\n--- Dimensiones Internas Físicas ---")
    print(f"Ancho (W):       {w_int:.1f} cm")
    print(f"Profundidad (D): {d_int:.1f} cm")
    print(f"Alto (H):        {h_int:.1f} cm")

    print("\n--- Lista de Cortes MDF ---")
    for corte in cortes:
        print(f"{corte[0]:<30} | {corte[1]:.1f} cm x {corte[2]:.2f} cm")
    print(f"\n[i] {estado_puerto}")

if __name__ == "__main__":
    calcular_cortes_caja()