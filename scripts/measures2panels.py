import math
import json
import os
import sys
from fpdf import FPDF

def encontrar_vb_convergente(fs, sd, espesor_cm):
    area_puerto = sd * 0.30
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    root_phi = math.sqrt(phi)
    
    vb_min, vb_max, vb_target = 1.0, 150.0, 5.0
    
    for _ in range(100):
        vb = (vb_min + vb_max) / 2.0
        w_int = ((vb * 1000.0) / (phi ** 1.5)) ** (1.0 / 3.0)
        d_int = w_int * root_phi
        h_int = w_int * phi
        
        l_req = (30000.0 * area_puerto) / (vb * (fs ** 2)) - (0.823 * math.sqrt(area_puerto))
        l_disp = d_int + h_int - (2 * espesor_cm)
        
        if abs(l_req - l_disp) < 0.01:
            vb_target = vb
            break
        elif l_req > l_disp:
            vb_min = vb
        else:
            vb_max = vb
            vb_target = vb
    return vb_target

def calcular_cortes_caja(archivo_json):
    if not os.path.exists(archivo_json): return

    with open(archivo_json, 'r') as f:
        ts_data = json.load(f)
        fs = float(ts_data['Fs'])
        sd = float(ts_data['Sd'])
        nombre_parlante = ts_data['Parlante']

    try:
        espesor_mdf_mm = float(input("Espesor del MDF (mm): "))
    except ValueError:
        return

    espesor_cm = round(espesor_mdf_mm / 10.0, 1)
    vb_neto = encontrar_vb_convergente(fs, sd, espesor_cm)
    
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    w_int = round(((vb_neto * 1000.0) / (phi ** 1.5)) ** (1.0 / 3.0), 1)
    d_int = round(w_int * math.sqrt(phi), 1)
    h_int = round(w_int * phi, 1)
    
    h_puerto_cm = round((sd * 0.30) / w_int, 1)
    l_puerto_cm = round((30000.0 * (sd * 0.30)) / (vb_neto * (fs ** 2)) - (0.823 * math.sqrt((sd * 0.30))), 1)
    
    h_ext = round(h_int + (2 * espesor_cm), 1)
    d_ext = round(d_int + (2 * espesor_cm), 1)

    cortes = [
        ["2x Laterales Caja", h_ext, d_ext],
        ["2x Superior/Inferior Caja", w_int, d_ext],
        ["1x Panel Trasero Caja", h_int, w_int],
        ["1x Panel Frontal Caja", round(h_int - h_puerto_cm, 1), w_int],
        ["1x Falso Piso Puerto (Base)", w_int, d_int],
        ["1x Falso Respaldo Puerto (Sube)", w_int, round(l_puerto_cm - d_int, 1)],
        ["1x Deflector Codo 45 grados", w_int, round((h_puerto_cm * (1.0 - (math.sqrt(2.0) / 2.0))) * math.sqrt(2.0), 2)]
    ]

    # Generación del Documento PDF
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Planos de Construcción Acústica - {nombre_parlante}", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Parámetros Thiele-Small y Entorno:", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 6, f"Frecuencia de Resonancia (Fs): {fs} Hz", ln=True)
    pdf.cell(0, 6, f"Volumen Equivalente (Vas): {ts_data['Vas']} Litros", ln=True)
    pdf.cell(0, 6, f"Área Útil del Cono (Sd): {sd} cm2", ln=True)
    pdf.cell(0, 6, f"Factor de Calidad (Qts): {ts_data['Qts']}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Geometría de Convergencia (EBS Áureo):", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 6, f"Volumen Neto Estanco: {vb_neto:.2f} Litros", ln=True)
    pdf.cell(0, 6, f"Espacio Interno (Ancho x Prof. x Alto): {w_int} x {d_int} x {h_int} cm", ln=True)
    pdf.cell(0, 6, f"Conducto Reflex Externo: Ranura {h_puerto_cm} cm | Longitud {l_puerto_cm} cm", ln=True)
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Despiece de Paneles MDF:", ln=True)
    pdf.set_font("Courier", '', 10)
    
    for corte in cortes:
        pdf.cell(0, 6, f"{corte[0]:<35} | {corte[1]:>5.1f} cm x {corte[2]:>5.2f} cm", ln=True)

    base_name = os.path.basename(archivo_json).replace("_thiele_small_processed.json", "")
    pdf_filename = os.path.join("data", f"{base_name}_panels.pdf")
    
    pdf.output(pdf_filename)
    print(f"\n[+] PDF de corte generado y guardado en '{pdf_filename}'")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        calcular_cortes_caja(sys.argv[1])
    else:
        print("[!] Ruta del JSON procesado no proporcionada.")