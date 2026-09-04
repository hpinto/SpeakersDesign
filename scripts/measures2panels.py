import math
import json
import os
import sys
from fpdf import FPDF

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    GRAFICOS_DISPONIBLES = True
except ImportError:
    GRAFICOS_DISPONIBLES = False
    print("[!] Librería 'matplotlib' no encontrada. Instálala con 'pip install matplotlib' para generar los planos 2D.")

def renderizar_planos_2d(base_name, d_int, w_int, h_int, espesor, h_puerto, l_puerto_cm, l_falso_piso, l_falso_respaldo, l_falso_techo, tipo_puerto):
    d_ext = d_int + (2 * espesor)
    h_ext = h_int + (2 * espesor)
    w_ext = w_int + (2 * espesor)
    
    color_mdf = '#DEB887'
    borde_mdf = '#8B4513'
    
    def agregar_panel(ax, x, y, ancho, alto):
        panel = patches.Rectangle((x, y), ancho, alto, linewidth=1.2, edgecolor=borde_mdf, facecolor=color_mdf, zorder=3)
        ax.add_patch(panel)

    # --- 1. VISTA LATERAL (Perfil y Laberinto) ---
    fig, ax = plt.subplots(figsize=(5, 7))
    ax.set_xlim(-2, d_ext + 4)
    ax.set_ylim(-2, h_ext + 2)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title("Corte Lateral (Mecánica de Fluidos)", fontsize=12, fontweight='bold', pad=15)
    
    # Chasis Exterior
    agregar_panel(ax, 0, 0, d_ext, espesor) # Inferior
    agregar_panel(ax, 0, h_ext - espesor, d_ext, espesor) # Superior
    agregar_panel(ax, 0, espesor + h_puerto, espesor, h_int - h_puerto) # Frontal (suspendido)
    agregar_panel(ax, d_ext - espesor, espesor, espesor, h_int) # Trasero
    
    # Laberinto Dinámico
    if "Recta" in tipo_puerto:
        agregar_panel(ax, espesor, espesor + h_puerto, l_puerto_cm, espesor)
    else:
        agregar_panel(ax, espesor, espesor + h_puerto, l_falso_piso, espesor) # Base
        x_respaldo = espesor + l_falso_piso
        y_respaldo = espesor + h_puerto
        agregar_panel(ax, x_respaldo, y_respaldo, espesor, l_falso_respaldo) # Sube
        if "2 Codos" in tipo_puerto:
            x_techo = x_respaldo - l_falso_techo
            y_techo = y_respaldo + l_falso_respaldo
            agregar_panel(ax, x_techo, y_techo, l_falso_techo, espesor) # Vuelve
            
    plt.tight_layout()
    ruta_lat = os.path.join("data", f"{base_name}_lateral.png")
    plt.savefig(ruta_lat, dpi=300, bbox_inches='tight')
    plt.close()
    
    # --- 2. VISTA FRONTAL (Baffle y Ranura) ---
    fig2, ax2 = plt.subplots(figsize=(5, 7))
    ax2.set_xlim(-2, w_ext + 4)
    ax2.set_ylim(-2, h_ext + 2)
    ax2.set_aspect('equal')
    ax2.axis('off')
    ax2.set_title("Vista Frontal (Baffle)", fontsize=12, fontweight='bold', pad=15)
    
    # Chasis
    agregar_panel(ax2, 0, 0, w_ext, espesor) # Inferior
    agregar_panel(ax2, 0, h_ext - espesor, w_ext, espesor) # Superior
    agregar_panel(ax2, 0, espesor, espesor, h_int) # Lateral Izq
    agregar_panel(ax2, w_ext - espesor, espesor, espesor, h_int) # Lateral Der
    
    # Baffle Frontal
    agregar_panel(ax2, espesor, espesor + h_puerto, w_int, h_int - h_puerto)
    
    # Renderizado del Transductor (Círculo a escala geométrica)
    centro_x = w_ext / 2
    centro_y = (espesor + h_puerto + h_ext - espesor) / 2
    radio = w_int * 0.38
    parlante = patches.Circle((centro_x, centro_y), radio, linewidth=1.5, edgecolor='#333333', facecolor='#4A4A4A', zorder=4)
    cono = patches.Circle((centro_x, centro_y), radio * 0.75, linewidth=1, edgecolor='#222222', facecolor='#2F2F2F', zorder=5)
    ax2.add_patch(parlante)
    ax2.add_patch(cono)
    
    # Etiqueta de la ranura de admisión
    ax2.text(centro_x, espesor + (h_puerto / 2), f"Túnel Reflex: {h_puerto} cm", color='black', ha='center', va='center', fontsize=9, zorder=6)

    plt.tight_layout()
    ruta_front = os.path.join("data", f"{base_name}_frontal.png")
    plt.savefig(ruta_front, dpi=300, bbox_inches='tight')
    plt.close()
    
    return ruta_lat, ruta_front

def calcular_cortes_caja(archivo_json):
    if not os.path.exists(archivo_json): 
        print(f"[!] Archivo no encontrado: {archivo_json}")
        return

    with open(archivo_json, 'r') as f:
        ts_data = json.load(f)
        fs = float(ts_data['Fs'])
        sd = float(ts_data['Sd'])
        vas = float(ts_data['Vas'])
        qts = float(ts_data['Qts'])
        nombre_parlante = ts_data['Parlante']

    try:
        espesor_mdf_mm = float(input("Espesor del MDF (mm): "))
    except ValueError:
        return

    espesor_cm = round(espesor_mdf_mm / 10.0, 1)
    
    # Constantes Áureas
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    root_phi = math.sqrt(phi)
    
    # Alineación EBS y Termodinámica
    vb_neto = (2.0 - (1.0 / phi)) * 15.0 * vas * (math.pow(qts, 2.87))
    fb = fs
    area_puerto = sd * (root_phi - 1.0)
    l_puerto_cm = round((30000.0 * area_puerto) / (vb_neto * (fb ** 2)) - (0.823 * math.sqrt(area_puerto)), 1)
    
    w_int_neto = round(((vb_neto * 1000.0) / (phi ** 1.5)) ** (1.0 / 3.0), 1)
    vol_aire_puerto = (area_puerto * l_puerto_cm) / 1000.0
    vol_mdf_puerto = (w_int_neto * l_puerto_cm * espesor_cm) / 1000.0
    vb_bruto = vb_neto + vol_aire_puerto + vol_mdf_puerto
    
    w_int = round(((vb_bruto * 1000.0) / (phi ** 1.5)) ** (1.0 / 3.0), 1)
    d_int = round(w_int * root_phi, 1)
    h_int = round(w_int * phi, 1)
    h_puerto_cm = round(area_puerto / w_int, 1)
    
    h_ext = round(h_int + (2 * espesor_cm), 1)
    d_ext = round(d_int + (2 * espesor_cm), 1)
    h_frontal = round(h_int - h_puerto_cm, 1)
    
    cortes = [
        ["2x Laterales Caja", h_ext, d_ext],
        ["2x Superior/Inferior Caja", w_int, d_ext],
        ["1x Panel Trasero Caja", h_int, w_int],
        ["1x Panel Frontal Caja", h_frontal, w_int],
    ]
    
    l_falso_piso = round(d_int - h_puerto_cm - espesor_cm, 1)
    l_falso_respaldo = 0
    l_falso_techo = 0
    alerta_colision = False
    
    if l_puerto_cm <= l_falso_piso:
        tipo_puerto = "Línea Recta Interna (I)"
        cortes.append(["1x Falso Piso Puerto (Recto)", w_int, l_puerto_cm])
    else:
        l_restante = round(l_puerto_cm - l_falso_piso, 1)
        l_falso_respaldo_max = round(h_int - (2 * h_puerto_cm) - (2 * espesor_cm), 1)
        
        if l_restante <= l_falso_respaldo_max:
            tipo_puerto = "Laberinto Interno (1 Codo - L)"
            l_falso_respaldo = l_restante
            cortes.append(["1x Falso Piso Puerto (Base)", w_int, l_falso_piso])
            cortes.append(["1x Falso Respaldo Puerto (Sube)", w_int, l_falso_respaldo])
        else:
            tipo_puerto = "Laberinto Interno (2 Codos - U)"
            l_falso_respaldo = l_falso_respaldo_max
            l_falso_techo = round(l_restante - l_falso_respaldo_max, 1)
            cortes.append(["1x Falso Piso Puerto (Base)", w_int, l_falso_piso])
            cortes.append(["1x Falso Respaldo Puerto (Sube)", w_int, l_falso_respaldo])
            cortes.append(["1x Falso Techo Puerto (Vuelve)", w_int, l_falso_techo])
            
            espacio_disponible_techo = round(d_int - h_puerto_cm - espesor_cm, 1)
            if l_falso_techo > espacio_disponible_techo:
                alerta_colision = True

    base_name = os.path.basename(archivo_json).replace("_thiele_small_processed.json", "").replace(".json", "")
    
    # Generación de Documento PDF Principal
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Planos Acústicos EBS / Laberinto Interno - {nombre_parlante}", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Parámetros Thiele-Small y Matriz EBS:", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 6, f"Frecuencia (Fs): {fs} Hz | Vol (Vas): {vas} L | Area (Sd): {sd} cm2", ln=True)
    pdf.cell(0, 6, f"Factor (Qts): {qts} | Sintonía (Fb): {fb} Hz", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Cámara Principal (Proporción 1 : raiz(phi) : phi):", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 6, f"Volumen Neto: {vb_neto:.2f} L | Bruto (con puerto): {vb_bruto:.2f} L", ln=True)
    pdf.cell(0, 6, f"Espacio Interno: {w_int} x {d_int} x {h_int} cm", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"Resonador Termodinámico ({tipo_puerto}):", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 6, f"Ranura: {h_puerto_cm} cm | Ancho: {w_int} cm | Longitud Acústica: {l_puerto_cm} cm", ln=True)
    pdf.cell(0, 6, f"Área Transversal Estática: {area_puerto:.1f} cm2 (27.2% de Sd)", ln=True)
    if alerta_colision:
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 6, "[!] RIESGO: El falso techo excede la profundidad interna.", ln=True)
        pdf.set_text_color(0, 0, 0)
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"Despiece MDF {espesor_mdf_mm:.0f} mm:", ln=True)
    pdf.set_font("Courier", '', 10)
    
    for corte in cortes:
        pdf.cell(0, 6, f"{corte[0]:<35} | {corte[1]:>5.1f} cm x {corte[2]:>5.2f} cm", ln=True)

    # Inyección de Gráficos 2D
    if GRAFICOS_DISPONIBLES:
        ruta_lat, ruta_front = renderizar_planos_2d(
            base_name, d_int, w_int, h_int, espesor_cm, h_puerto_cm, l_puerto_cm, 
            l_falso_piso, l_falso_respaldo, l_falso_techo, tipo_puerto
        )
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Esquemática de Ensamblaje y Traslapes", ln=True, align='C')
        # Renderizado simétrico de ambas vistas
        pdf.image(ruta_lat, x=10, y=30, w=90)
        pdf.image(ruta_front, x=110, y=30, w=90)

    pdf_filename = os.path.join("data", f"{base_name}_panels_interno_graficos.pdf")
    pdf.output(pdf_filename)
    print(f"\n[+] PDF generado: '{pdf_filename}'")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        calcular_cortes_caja(sys.argv[1])
    else:
        print("[!] Ruta del JSON procesado no proporcionada.")