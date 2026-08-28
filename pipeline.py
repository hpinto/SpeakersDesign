import subprocess
import os
import sys
import glob

def ejecutar_script(nombre_script, args=None):
    print(f"\n{'='*50}\n[+] Iniciando etapa: {nombre_script}\n{'='*50}")
    if not os.path.exists(nombre_script):
        print(f"[!] Error crítico: No se encuentra '{nombre_script}'.")
        return False
    try:
        cmd = [sys.executable, nombre_script]
        if args:
            cmd.extend(args)
        resultado = subprocess.run(cmd, check=True)
        return resultado.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"[!] Error en {nombre_script} (Código: {e.returncode})")
        return False

def main():
    print("=== Pipeline Maestro de Ingeniería Acústica EnduraLab ===")
    os.makedirs("data", exist_ok=True)
    
    # Etapa 1: Adquisición BLE
    if not ejecutar_script(os.path.join("scripts", "get_measures.py")): return
    
    archivos_data = glob.glob(os.path.join("data", "*_thiele_small_data.json"))
    if not archivos_data: return
    latest_data = max(archivos_data, key=os.path.getmtime)
    
    # Etapa 2: Procesamiento TS
    if not ejecutar_script(os.path.join("scripts", "process_measures.py"), args=[latest_data]): return
    
    archivos_proc = glob.glob(os.path.join("data", "*_thiele_small_processed.json"))
    if not archivos_proc: return
    latest_proc = max(archivos_proc, key=os.path.getmtime)
    
    # Etapa 3: Cálculo y PDF
    if not ejecutar_script(os.path.join("scripts", "measures2panels.py"), args=[latest_proc]): return
    
    print("\n" + "="*50 + "\n[+] ¡Pipeline ejecutado de extremo a extremo con éxito!\n" + "="*50)

if __name__ == "__main__":
    main()