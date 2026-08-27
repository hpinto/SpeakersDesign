import subprocess
import os
import sys
import glob

def ejecutar_script(nombre_script, args=None):
    print(f"\n" + "="*50)
    print(f"[+] Iniciando etapa: {nombre_script}")
    print("="*50)
    
    if not os.path.exists(nombre_script):
        print(f"[!] Error crítico: No se encuentra el archivo '{nombre_script}' en el directorio actual.")
        return False
        
    try:
        cmd = [sys.executable, nombre_script]
        if args:
            cmd.extend(args)
        resultado = subprocess.run(cmd, check=True)
        return resultado.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"[!] Error en la ejecución de {nombre_script} (Código de salida: {e.returncode})")
        return False
    except Exception as e:
        print(f"[!] Excepción no controlada al ejecutar {nombre_script}: {e}")
        return False

def verificar_archivo(ruta_archivo):
    if os.path.exists(ruta_archivo):
        print(f"[i] Verificación exitosa: Archivo intermedio '{ruta_archivo}' generado correctamente.")
        return True
    else:
        print(f"[!] Alerta de integridad: No se detectó el archivo esperado '{ruta_archivo}'.")
        return False

def main():
    print("=== Pipeline Maestro de Ingeniería Acústica EnduraLab ===")
    print("Secuencia: Adquisición -> Procesamiento TS -> Cálculo de Paneles (Slotted Port)\n")
    
    # Etapa 1: Adquisición de datos
    script_1 = "get_measures4ts.py"
    if not ejecutar_script(script_1):
        print("\n[X] Pipeline abortado en la Etapa 1 (Adquisición de Medidas).")
        return
        
    # Buscar el CSV recién generado
    archivos_csv = glob.glob("thiele_small_*.csv")
    if not archivos_csv:
        print("\n[X] Pipeline abortado: No se detectó la matriz CSV exportada en el directorio.")
        return
        
    latest_csv = max(archivos_csv, key=os.path.getmtime)
    print(f"[i] Matriz detectada: {latest_csv}")
    
    # Etapa 2: Procesamiento matemático de Thiele-Small
    script_2 = "process_measures4ts.py"
    if not ejecutar_script(script_2, args=[latest_csv]):
        print("\n[X] Pipeline abortado en la Etapa 2 (Procesamiento de Parámetros TS).")
        return
        
    if not verificar_archivo("parametros_ts.json"):
        print("\n[X] Pipeline abortado: El archivo 'parametros_ts.json' no existe o está corrupto.")
        return

    # Etapa 3: Cálculo de cortes y laberinto en L
    script_3 = "measures2panels.py"
    if not ejecutar_script(script_3):
        print("\n[X] Pipeline abortado en la Etapa 3 (Cálculo de Paneles MDF).")
        return
        
    print("\n" + "="*50)
    print("[+] ¡Pipeline ejecutado de extremo a extremo con éxito!")
    print("[+] Lista de cortes y especificaciones de laberinto generadas listas para taller.")
    print("="*50)

if __name__ == "__main__":
    main()