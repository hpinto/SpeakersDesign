import math
import json
import os

def calcular_cortes_caja():
    print("=== Calculadora de Cortes MDF (Slotted Port Iterativo a 1mm) ===\n")
    
    archivo_json = "parametros_ts.json"
    
    # 1. Carga automatizada de parámetros TS
    if not os.path.exists(archivo_json):
        print(f"[!] Error crítico: No se encontró el archivo '{archivo_json}'.")
        return

    try:
        with open(archivo_json, 'r') as f:
            ts_data = json.load(f)
            vas = float(ts_data['Vas'])
            qts = float(ts_data['Qts'])
            fs = float(ts_data['Fs'])
            print(f"[+] Parámetros importados: Vas={vas}L, Qts={qts}, Fs={fs}Hz\n")
    except Exception as e:
        print(f"[!] Error al leer JSON: {e}")
        return

    # 2. Entrada de variables de diseño
    try:
        espesor_mdf_mm = float(input("Espesor del MDF (mm): "))
        vol_crossover = float(input("Volumen del crossover (Litros): "))
        vol_driver = float(input("Volumen desplazado por el imán/cono (Litros): "))
        ganancia_napa = float(input("% de ganancia de volumen aparente por napa (ej. 15): "))
        
        print("\n--- Datos del Laberinto Acústico (Slotted Port) ---")
        print("[i] Asume puerto tipo repisa en la base. El ancho se auto-ajustará al interior de la caja.")
        h_puerto_cm = float(input("Alto interno de la ranura del puerto (cm): "))
        l_puerto_cm = float(input("Longitud física total del laberinto (cm): "))
    except ValueError:
        print("Error: Ingresa únicamente valores numéricos.")
        return

    espesor_cm = round(espesor_mdf_mm / 10.0, 1)
    
    # 3. Cálculo del Volumen Acústico Neto (Vb)
    vb_neto_litros = 15.0 * (qts ** 2.87) * vas
    print(f"\n[+] Volumen Acústico Neto Objetivo: {vb_neto_litros:.2f} Litros")
    
    # 4. Bucle Iterativo para convergencia del volumen y proporción áurea
    phi = 1.61803398875
    root_phi = math.sqrt(phi)
    factor_napa = 1.0 + (ganancia_napa / 100.0)
    
    vol_bruto_base = vb_neto_litros + vol_crossover + vol_driver
    w_int = 0.0
    vol_puerto_total_litros = 0.0
    
    for _ in range(15):
        vb_fisico_litros = (vol_bruto_base + vol_puerto_total_litros) / factor_napa
        vol_cm3 = vb_fisico_litros * 1000.0
        
        w_int = (vol_cm3 / (phi ** 1.5)) ** (1.0 / 3.0)
        
        vol_aire_puerto_cm3 = w_int * h_puerto_cm * l_puerto_cm
        vol_madera_puerto_cm3 = w_int * espesor_cm * l_puerto_cm
        vol_puerto_total_litros = (vol_aire_puerto_cm3 + vol_madera_puerto_cm3) / 1000.0

    # 5. Redondeo metrológico para ensamble exacto
    w_int = round(w_int, 1)
    d_int = round(w_int * root_phi, 1)
    h_int = round(w_int * phi, 1)
    
    vol_real_litros = (w_int * d_int * h_int) / 1000.0
    
    print("\n--- Dimensiones Internas Físicas (Redondeo a 1mm) ---")
    print(f"Ancho (W):       {w_int:.1f} cm")
    print(f"Profundidad (D): {d_int:.1f} cm")
    print(f"Alto (H):        {h_int:.1f} cm")
    print(f"[+] Volumen puerto desplazado (aire + MDF): {vol_puerto_total_litros:.2f} L")
    print(f"[i] Volumen interno real tras cortes:       {vol_real_litros:.2f} L")
    
    # 6. Cálculo de Paneles (Chasis Exterior)
    h_ext = round(h_int + (2 * espesor_cm), 1)
    d_ext = round(d_int + (2 * espesor_cm), 1)
    
    print("\n--- Lista de Cortes MDF (Caja Principal) ---")
    print(f"2x Laterales:          {h_ext:.1f} cm x {d_ext:.1f} cm")
    print(f"2x Superior/Inferior:  {w_int:.1f} cm x {d_ext:.1f} cm")
    print(f"2x Frontal/Trasero:    {h_int:.1f} cm x {w_int:.1f} cm")
    
    # 7. Cálculo de Panel del Slotted Port
    l_panel_puerto = round(l_puerto_cm - espesor_cm, 1)
    if l_panel_puerto < 0: l_panel_puerto = l_puerto_cm
    
    print("\n--- Lista de Cortes MDF (Laberinto interno) ---")
    print(f"1x Techo de Ranura:    {w_int:.1f} cm x {l_panel_puerto:.1f} cm")
    print("[!] Nota: Se restó el espesor del panel frontal a la longitud del corte del laberinto para mantener la afinación.")

if __name__ == "__main__":
    calcular_cortes_caja()