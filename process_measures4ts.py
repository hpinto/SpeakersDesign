import numpy as np
import os
import json
import sys

def calcular_ts(archivo_csv):
    if not os.path.exists(archivo_csv):
        print(f"Error: El archivo {archivo_csv} no existe.")
        return

    # Extraer metadatos completos del CSV automáticamente
    re_val, rs_val, masa_val = 0.0, 0.0, 0.0
    diametro_cm, temp_c, altitud_m, v_total = 0.0, 20.0, 0.0, 1.0
    
    with open(archivo_csv, 'r', encoding='utf-8') as f:
        for linea in f:
            if linea.startswith("# Re:"):
                re_val = float(linea.split(":")[1].replace("Ohms", "").strip())
            elif linea.startswith("# Rs:"):
                rs_val = float(linea.split(":")[1].replace("Ohms", "").strip())
            elif linea.startswith("# Masa Agregada:"):
                masa_val = float(linea.split(":")[1].replace("g", "").strip()) / 1000.0  # Pasar a kg
            elif linea.startswith("# Diametro:"):
                diametro_cm = float(linea.split(":")[1].replace("cm", "").strip())
            elif linea.startswith("# Temp:"):
                temp_c = float(linea.split(":")[1].replace("C", "").strip())
            elif linea.startswith("# Altitud:"):
                altitud_m = float(linea.split(":")[1].replace("m", "").strip())
            elif linea.startswith("# V_total:"):
                v_total = float(linea.split(":")[1].replace("V", "").strip())

    # Cargar datos de la matriz. Numpy ignorará automáticamente todas las líneas con '#'
    datos = np.loadtxt(archivo_csv, delimiter=',', comments='#')
    freqs = datos[:, 0]
    v_aire = datos[:, 1]
    v_masa = datos[:, 2]

    # Física Atmosférica
    p_presion = 101325 * (1 - (0.0065 * altitud_m) / 288.15)**5.255
    rho = (p_presion * 0.028964) / (8.314 * (temp_c + 273.15))
    c = 331.3 * np.sqrt(1 + temp_c / 273.15)
    
    sd_m2 = (np.pi * ((diametro_cm / 100.0) / 2)**2)

    # Convertir Voltajes a Impedancia (Z)
    z_aire = rs_val * (v_aire / (v_total - v_aire))
    z_masa = rs_val * (v_masa / (v_total - v_masa))

    # Identificar Fs
    idx_fs = np.argmax(z_aire)
    fs = freqs[idx_fs]
    z_max = z_aire[idx_fs]

    # Identificar Fsm
    idx_fsm = np.argmax(z_masa)
    fsm = freqs[idx_fsm]

    r0 = z_max / re_val
    z_target = re_val * np.sqrt(r0)

    freqs_left = freqs[:idx_fs+1]
    z_left = z_aire[:idx_fs+1]
    freqs_right = freqs[idx_fs:]
    z_right = z_aire[idx_fs:]

    f1 = np.interp(z_target, z_left, freqs_left)
    f2 = np.interp(z_target, z_right[::-1], freqs_right[::-1])

    # Cálculos Thiele-Small
    qms = (fs * np.sqrt(r0)) / (f2 - f1)
    qes = qms / (r0 - 1)
    qts = (qms * qes) / (qms + qes)

    mms = masa_val / ((fs / fsm)**2 - 1)
    cms = 1 / ((2 * np.pi * fs)**2 * mms)
    vas = rho * (c**2) * (sd_m2**2) * cms
    vas_litros = vas * 1000

    bl = np.sqrt((2 * np.pi * fs * mms * re_val) / qes)

    print("\n" + "="*40)
    print("      PARÁMETROS THIELE-SMALL")
    print("="*40)
    print(f"Entorno        : {temp_c}°C | {altitud_m}m | ρ={rho:.3f} kg/m³ | c={c:.1f} m/s")
    print(f"Area Efectiva  : {sd_m2:.5f} m²")
    print("-" * 40)
    print(f"Fs  (Resonancia) : {fs:.2f} Hz")
    print(f"Fsm (Masa Agreg.): {fsm:.2f} Hz")
    print(f"Zmax             : {z_max:.2f} Ohms")
    print(f"R0               : {r0:.2f}")
    print("-" * 40)
    print(f"Qms (Mecánico)   : {qms:.3f}")
    print(f"Qes (Eléctrico)  : {qes:.3f}")
    print(f"Qts (Total)      : {qts:.3f}")
    print("-" * 40)
    print(f"Mms (Masa Móvil) : {mms*1000:.2f} g")
    print(f"Cms (Compliancia): {cms*1000:.3f} mm/N")
    print(f"Vas (Vol. Equiv) : {vas_litros:.2f} Litros")
    print(f"B·l (Fuerza Motor): {bl:.2f} T·m")
    print("="*40)

    # Exportación JSON para integration con measures2panels.py
    ts_export = {
        "Fs": round(float(fs), 2),
        "Qts": round(float(qts), 3),
        "Vas": round(float(vas_litros), 2),
        "Qms": round(float(qms), 3),
        "Qes": round(float(qes), 3),
        "Re": round(float(re_val), 2),
        "Sd": round(float(sd_m2 * 10000), 2)  
    }

    try:
        with open('parametros_ts.json', 'w', encoding='utf-8') as json_file:
            json.dump(ts_export, json_file, indent=4)
        print("\n[+] Parámetros exportados exitosamente a 'parametros_ts.json'")
    except IOError as e:
        print(f"\n[!] Error crítico al escribir el archivo JSON: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        archivo = sys.argv[1]
    else:
        archivo = input("Ingresa el nombre del archivo CSV generado: ").strip()
    calcular_ts(archivo)