import numpy as np
import os
import json
import sys

def calcular_ts(archivo_json):
    if not os.path.exists(archivo_json):
        print(f"Error: El archivo {archivo_json} no existe.")
        return

    with open(archivo_json, 'r', encoding='utf-8') as f:
        datos_raw = json.load(f)

    nombre_parlante = datos_raw["Parlante"]
    re_val = datos_raw["Re"]
    rs_val = datos_raw["Rs"]
    masa_val = datos_raw["Masa_Agregada"] / 1000.0  
    diametro_cm = datos_raw["Diametro"]
    temp_c = datos_raw["Temp"]
    altitud_m = datos_raw["Altitud"]
    v_total = datos_raw["V_total"]

    freqs = np.array([p["Frecuencia"] for p in datos_raw["Barrido"]])
    v_aire = np.array([p["V_Aire"] for p in datos_raw["Barrido"]])
    v_masa = np.array([p["V_Masa"] for p in datos_raw["Barrido"]])

    # Física Atmosférica
    p_presion = 101325 * (1 - (0.0065 * altitud_m) / 288.15)**5.255
    rho = (p_presion * 0.028964) / (8.314 * (temp_c + 273.15))
    c = 331.3 * np.sqrt(1 + temp_c / 273.15)
    sd_m2 = (np.pi * ((diametro_cm / 100.0) / 2)**2)

    # Convertir Voltajes a Impedancia (Z)
    z_aire = rs_val * (v_aire / (v_total - v_aire))
    z_masa = rs_val * (v_masa / (v_total - v_masa))

    idx_fs = np.argmax(z_aire)
    fs = freqs[idx_fs]
    z_max = z_aire[idx_fs]
    fsm = freqs[np.argmax(z_masa)]

    r0 = z_max / re_val
    z_target = re_val * np.sqrt(r0)

    f1 = np.interp(z_target, z_aire[:idx_fs+1], freqs[:idx_fs+1])
    f2 = np.interp(z_target, z_aire[idx_fs:][::-1], freqs[idx_fs:][::-1])

    qms = (fs * np.sqrt(r0)) / (f2 - f1)
    qes = qms / (r0 - 1)
    qts = (qms * qes) / (qms + qes)

    mms = masa_val / ((fs / fsm)**2 - 1)
    cms = 1 / ((2 * np.pi * fs)**2 * mms)
    vas_litros = (rho * (c**2) * (sd_m2**2) * cms) * 1000

    base_name = os.path.basename(archivo_json).replace("_thiele_small_data.json", "")
    
    ts_export = {
        "Parlante": nombre_parlante,
        "PrefijoArchivo": base_name,
        "Fs": round(float(fs), 2),
        "Qts": round(float(qts), 3),
        "Vas": round(float(vas_litros), 2),
        "Sd": round(float(sd_m2 * 10000), 2)  
    }

    filepath_out = os.path.join("data", f"{base_name}_thiele_small_processed.json")
    with open(filepath_out, 'w', encoding='utf-8') as f:
        json.dump(ts_export, f, indent=4)
        
    print(f"\n[+] Parámetros procesados y exportados a '{filepath_out}'")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        calcular_ts(sys.argv[1])
    else:
        print("[!] Ruta del JSON de datos no proporcionada.")