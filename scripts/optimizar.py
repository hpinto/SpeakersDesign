import sys
import re
import os

try:
    from pypdf import PdfReader
except ImportError:
    print("[!] Falta dependencia. Instala: pip install pypdf")
    sys.exit(1)

def main():
    archivos = sys.argv[1:]
    if not archivos:
        print("Uso: python optimizar.py caja1.pdf caja2.pdf ...")
        return
        
    print("\n===========================================")
    print("   EXTRACTOR DE CORTES (EXPORTAR A CSV)    ")
    print("===========================================\n")

    # Patrón para leer el PDF generado por el script de diseño
    patron = r"-\s+(\d+)x\s+([^|]+)\|\s*([\d\.]+)\s*cm\s*x\s*([\d\.]+)\s*cm"
    lineas_exportar = []
    
    # Cabecera del archivo CSV
    lineas_exportar.append("Nombre Parlante;Nombre Corte;Cantidad;Alto (mm);Ancho (mm)")

    total_piezas = 0

    for archivo in archivos:
        print(f"[*] Extrayendo datos de: {archivo} ...", end=" ")
        try:
            reader = PdfReader(archivo)
            texto_completo = ""
            for page in reader.pages:
                texto_completo += page.extract_text() + "\n"
                
            matches = re.findall(patron, texto_completo)
            if not matches:
                print("No se encontraron cortes.")
                continue
                
            nombre_proyecto = os.path.basename(archivo).replace('.pdf', '')
            
            for match in matches:
                cantidad = match[0]
                etiqueta = match[1].strip()
                
                # Convertimos de cm a mm (Estándar obligatorio en aserraderos y software)
                alto_mm = int(float(match[2]) * 10)
                ancho_mm = int(float(match[3]) * 10)
                
                # Formato CSV: Proyecto, Pieza, Cantidad, Alto, Ancho
                linea = f"{nombre_proyecto};{etiqueta};{cantidad};{alto_mm};{ancho_mm}"
                lineas_exportar.append(linea)
                total_piezas += int(cantidad)
                
            print(f"¡{len(matches)} tipos extraídos!")
        except Exception as e:
            print(f"[!] Error: {e}")
            
    # Guardar el archivo de texto
    nombre_salida = ".\data\Lista_de_Cortes.csv"
    with open(nombre_salida, "w", encoding="utf-8") as f:
        for linea in lineas_exportar:
            f.write(linea + "\n")
            
    print(f"\n[+] ÉXITO: Se ha generado el archivo '{nombre_salida}' con {total_piezas} piezas en total.")
    print("    Puedes abrir este .txt en Excel, o copiar el contenido y pegarlo")
    print("    directamente en tu software web de optimización de cortes.")

if __name__ == '__main__':
    main()