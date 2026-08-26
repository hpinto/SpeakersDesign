import asyncio
import os
from bleak import BleakScanner, BleakClient

START_FREQ = 20.0
END_FREQ = 200.0
POINTS_PER_OCTAVE = 12

TONE_DURATION = 3.0  
SETTLE_TIME = 2.5    
SAMPLE_RATE = 44100
AMPLITUDE = 0.5

ultimo_voltaje = 0.0

async def notification_handler(sender, data: bytearray):
    global ultimo_voltaje
    try:
        if len(data) >= 6:
            # Matemática sin signo obligatoria para RMS AC
            raw_val16 = data[4] + (data[5] * 256)
            byte_estado = data[0]
            
            divisores = {
                89: 10000.0,
                99: 1000.0,
                98: 100.0,
                97: 10.0,
                96: 1.0
            }
            
            divisor = divisores.get(byte_estado, 1000.0)
            ultimo_voltaje = raw_val16 / divisor
    except Exception as e:
        print(f"\n[Error de lectura BLE] No se pudo parsear el paquete: {e}")

async def main():
    global ultimo_voltaje
    
    target_device = None
    
    while True:
        print("Escaneando dispositivos Bluetooth cercanos (4 segundos)...")
        try:
            devices = await BleakScanner.discover(timeout=4.0)
        except Exception as e:
            print(f"Error en el escaneo de Windows: {e}")
            return

        print("\nDispositivos encontrados:")
        print("  [0] *** Volver a escanear ***")
        
        if not devices:
            print("  (Ningún otro dispositivo detectado)")
        else:
            for idx, d in enumerate(devices, start=1):
                nombre = d.name if d.name else "Desconocido"
                print(f"  [{idx}] Nombre: {nombre} | MAC/ID: {d.address}")

        try:
            seleccion = input("\nSelecciona el número correspondiente al BDM (o 0 para rescanear): ").strip()
            idx_elegido = int(seleccion)
            
            if idx_elegido == 0:
                print("\nReiniciando escaneo...\n")
                continue
            elif 1 <= idx_elegido <= len(devices):
                target_device = devices[idx_elegido - 1]
                break
            else:
                print("\nNúmero fuera de rango. Intenta de nuevo.\n")
        except ValueError:
            print("\nEntrada inválida. Ingresa un número.\n")

    print(f"\nConectando a {target_device.name or 'BDM'} ({target_device.address})...")

    async with BleakClient(target_device.address) as client:
        print("¡Conectado! Suscribiendo al canal de datos...")
        
        for service in client.services:
            for char in service.characteristics:
                if "notify" in char.properties:
                    try:
                        await client.start_notify(char.uuid, notification_handler)
                    except Exception:
                        pass

        import numpy as np
        import sounddevice as sd

        def generar_tono(freq, duracion, fs=SAMPLE_RATE):
            t = np.linspace(0, duracion, int(fs * duracion), endpoint=False)
            audio = AMPLITUDE * np.sin(2 * np.pi * freq * t)
            return np.column_stack((audio, audio)).astype(np.float32)

        octavas = np.log2(END_FREQ / START_FREQ)
        total_puntos = int(octavas * POINTS_PER_OCTAVE)
        frecuencias = np.logspace(np.log10(START_FREQ), np.log10(END_FREQ), total_puntos)

        async def ejecutar_barrido(frecuencias, nombre_fase):
            print(f"\nIniciando fase: {nombre_fase} ({len(frecuencias)} puntos)...")
            resultados = []
            for freq in frecuencias:
                tono = generar_tono(freq, TONE_DURATION)
                
                sd.play(tono, SAMPLE_RATE)
                await asyncio.sleep(SETTLE_TIME)
                
                voltaje_actual = ultimo_voltaje
                print(f"[{nombre_fase}] Freq: {freq:6.2f} Hz | Voltaje Medido: {voltaje_actual:.4f} V")
                resultados.append(voltaje_actual)
                
                await asyncio.sleep(TONE_DURATION - SETTLE_TIME)
                sd.stop()
                
            return resultados

        # --- FASE 1 ---
        v_aire = await ejecutar_barrido(frecuencias, "Aire Libre (Fs)")
        
        # --- PAUSA ---
        input("\n[PAUSA] Adhiere la masa al cono del parlante. Presiona ENTER para continuar...")
        
        # --- FASE 2 ---
        v_masa = await ejecutar_barrido(frecuencias, "Masa Agregada (Fs_mass)")

        # --- PARÁMETROS FINALES ---
        print("\n--- Parámetros del Parlante ---")
        nombre_parlante = input("Nombre del parlante: ").strip()
        re_val = input("Resistencia DC (Re) [Ohms]: ").strip()
        rs_val = input("Resistencia de sensado (Rs) [Ohms]: ").strip()
        masa_val = input("Masa agregada [gramos]: ").strip()

        # --- RESOLUCIÓN DE RUTA ABSOLUTA ---
        script_dir = os.path.dirname(os.path.abspath(__file__))
        filename = f"thiele_small_{nombre_parlante.replace(' ', '_')}.csv"
        filepath = os.path.join(script_dir, filename)
        
        # --- GUARDAR CSV ---
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# Parlante: {nombre_parlante}\n")
            f.write(f"# Re: {re_val} Ohms\n")
            f.write(f"# Rs: {rs_val} Ohms\n")
            f.write(f"# Masa Agregada: {masa_val} g\n")
            f.write("Frecuencia_Hz,V_AireLibre,V_MasaAgregada\n")
            
            for f_hz, v_a, v_m in zip(frecuencias, v_aire, v_masa):
                f.write(f"{f_hz:.4f},{v_a:.4f},{v_m:.4f}\n")

        print(f"\nMatriz de datos Thiele-Small generada con éxito en '{filepath}'.")

if __name__ == "__main__":
    asyncio.run(main())