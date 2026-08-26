import numpy as np
import os

def calcular_ts(archivo_csv):
    if not os.path.exists(archivo_csv):
        print(f"Error: El archivo {archivo_csv} no existe.")
        return

    # Extraer metadatos del CSV
    re_val, rs_val, masa_val = 0.0, 0.0, 0.0
    with open(archivo_csv, 'r', encoding='utf-8') as f:
        for linea in f:
            if linea.startswith("# Re:"):
                re_val = float(linea.split(":")[1].replace("Ohms", "").strip())
            elif linea.startswith("# Rs:"):
                rs_val = float(linea.split(":")[1].replace("Ohms", "").strip())
            elif linea.startswith("# Masa Agregada:"):
                masa_val = float(linea.split(":")[1].replace("g", "").strip()) / 1000.0  # Pasar a kg

    # Cargar datos de la matriz
    datos = np.loadtxt(archivo_csv, delimiter=',', comments='#', skiprows=1)
    freqs = datos[:, 0]
    v_aire = datos[:, 1]
    v_masa = datos[:, 2]

    print("\n--- Constantes Atmosféricas y del Entorno ---")
    try:
        v_total = float(input("Voltaje total del amplificador (V_total) [V]: ").strip())
        diametro_cm = float(input("Diámetro efectivo del cono (incl. mitad de suspensión) [cm]: ").strip())
        temp_c = float(input("Temperatura ambiente [°C]: ").strip())
        altitud_m = float(input("Altitud sobre el nivel del mar [m]: ").strip())
    except ValueError:
        print("Entrada inválida. Abortando.")
        return

    # Física Atmosférica
    p_presion = 101325 * (1 - (0.0065 * altitud_m) / 288.15)**5.255
    rho = (p_presion * 0.028964) / (8.314 * (temp_c + 273.15))
    c = 331.3 * np.sqrt(1 + temp_c / 273.15)
    
    sd_m2 = (np.pi * ((diametro_cm / 100.0) / 2)**2)

    # Convertir Voltajes a Impedancia (Z) midiendo en terminales
    # Z = Rs * (V_spk / (V_total - V_spk))
    z_aire = rs_val * (v_aire / (v_total - v_aire))
    z_masa = rs_val * (v_masa / (v_total - v_masa))

    # Identificar Fs (Pico de impedancia en aire libre)
    idx_fs = np.argmax(z_aire)
    fs = freqs[idx_fs]
    z_max = z_aire[idx_fs]

    # Identificar Fsm (Pico de impedancia con masa agregada)
    idx_fsm = np.argmax(z_masa)
    fsm = freqs[idx_fsm]

    # Cálculo de r0 y puntos a -3dB
    r0 = z_max / re_val
    z_target = re_val * np.sqrt(r0)

    # Dividir curva para interpolar F1 (izquierda de Fs) y F2 (derecha de Fs)
    freqs_left = freqs[:idx_fs+1]
    z_left = z_aire[:idx_fs+1]
    freqs_right = freqs[idx_fs:]
    z_right = z_aire[idx_fs:]

    f1 = np.interp(z_target, z_left, freqs_left)
    # Para la derecha, interp requiere arreglo monótonamente creciente, así que invertimos
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

if __name__ == "__main__":
    archivo = input("Ingresa el nombre del archivo CSV generado: ").strip()
    calcular_ts(archivo)