import math
import re
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

def renderizar_planos_2d(base_name, d_int, w_int, h_int, espesor, h_puerto, l_mdf_recto, l_falso_piso, l_falso_respaldo, l_falso_techo, tipo_puerto, offset_cm):
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
    ax.set_title("Corte Lateral (Mecánica de Fluidos EBS Dinámico)", fontsize=12, fontweight='bold', pad=15)
    
    # Chasis Exterior
    agregar_panel(ax, 0, 0, d_ext, espesor) 
    agregar_panel(ax, 0, h_ext - espesor, d_ext, espesor) 
    agregar_panel(ax, 0, espesor + h_puerto, espesor, h_int - h_puerto) 
    agregar_panel(ax, d_ext - espesor, espesor, espesor, h_int) 
    
    # Laberinto Dinámico
    if "Recta" in tipo_puerto:
        agregar_panel(ax, espesor, espesor + h_puerto, l_mdf_recto, espesor)
    else:
        agregar_panel(ax, espesor, espesor + h_puerto, l_falso_piso, espesor) 
        x_respaldo = espesor + l_falso_piso
        y_respaldo = espesor + h_puerto
        agregar_panel(ax, x_respaldo, y_respaldo, espesor, l_falso_respaldo) 
        if "2 Codos" in tipo_puerto:
            x_techo = x_respaldo - l_falso_techo
            y_techo = y_respaldo + l_falso_respaldo
            agregar_panel(ax, x_techo, y_techo, l_falso_techo, espesor) 
            
    plt.tight_layout()
    ruta_lat = os.path.join("data", f"{base_name}_lateral.png")
    plt.savefig(ruta_lat, dpi=300, bbox_inches='tight')
    plt.close()
    
    # --- 2. VISTA FRONTAL ESPEJADA (Baffle y Ranura L/R) ---
    fig2, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(10, 7))
    
    def dibujar_frontal(ax_obj, x_shift, titulo):
        ax_obj.set_xlim(-2, w_ext + 4)
        ax_obj.set_ylim(-2, h_ext + 2)
        ax_obj.set_aspect('equal')
        ax_obj.axis('off')
        ax_obj.set_title(titulo, fontsize=12, fontweight='bold', pad=15)
        
        # Chasis
        agregar_panel(ax_obj, 0, 0, espesor, h_ext)
        agregar_panel(ax_obj, w_ext - espesor, 0, espesor, h_ext)
        agregar_panel(ax_obj, espesor, 0, w_int, espesor)
        agregar_panel(ax_obj, espesor, h_ext - espesor, w_int, espesor)
        
        # Baffle Frontal
        h_frontal = h_int - h_puerto
        y_base_baffle = espesor + h_puerto
        agregar_panel(ax_obj, espesor, y_base_baffle, w_int, h_frontal)
        
        # Coordenadas Transductores
        centro_x = (w_ext / 2) + x_shift
        centro_y_woofer = y_base_baffle + (h_frontal * 0.35)
        centro_y_tweeter = y_base_baffle + (h_frontal * 0.75)
        
        radio_w = w_int * 0.35
        radio_t = w_int * 0.15
        
        # Woofer
        ax_obj.add_patch(patches.Circle((centro_x, centro_y_woofer), radio_w, linewidth=1.5, edgecolor='#333333', facecolor='#4A4A4A', zorder=4))
        ax_obj.add_patch(patches.Circle((centro_x, centro_y_woofer), radio_w * 0.75, linewidth=1, edgecolor='#222222', facecolor='#2F2F2F', zorder=5))
        
        # Tweeter
        ax_obj.add_patch(patches.Circle((centro_x, centro_y_tweeter), radio_t, linewidth=1.5, edgecolor='#333333', facecolor='#1A1A1A', zorder=4))
        ax_obj.add_patch(patches.Circle((centro_x, centro_y_tweeter), radio_t * 0.6, linewidth=1, edgecolor='#222222', facecolor='#2F2F2F', zorder=5))
        
        ax_obj.text(w_ext / 2, espesor + (h_puerto / 2), f"Reflex: {h_puerto} cm", color='black', ha='center', va='center', fontsize=9, zorder=6)

    dibujar_frontal(ax_l, -offset_cm, "Caja Izquierda (L)")
    dibujar_frontal(ax_r, offset_cm, "Caja Derecha (R)")
    
    plt.tight_layout()
    ruta_front = os.path.join("data", f"{base_name}_frontales.png")
    plt.savefig(ruta_front, dpi=300, bbox_inches='tight')
    plt.close()
    
    return ruta_lat, ruta_front

def calcular_cortes_caja(archivo_txt):
    if not os.path.exists(archivo_txt): 
        print(f"[!] Archivo no encontrado: {archivo_txt}")
        return

    fs = sd = vas = qts = 0.0
    
    with open(archivo_txt, 'r', encoding='utf-8') as f:
        contenido = f.read()
        
        match_fs = re.search(r'Fs\s*=\s*([\d\.]+)', contenido, re.IGNORECASE)
        match_sd = re.search(r'Sd\s*=\s*([\d\.]+)', contenido, re.IGNORECASE)
        match_vas = re.search(r'Vas\s*=\s*([\d\.]+)', contenido, re.IGNORECASE)
        match_qts = re.search(r'Qts?\s*=\s*([\d\.]+)', contenido, re.IGNORECASE)
        
        if match_fs: fs = float(match_fs.group(1))
        if match_sd: sd = float(match_sd.group(1))
        if match_vas: vas = float(match_vas.group(1))
        if match_qts: qts = float(match_qts.group(1))
        
    if not all([fs, sd, vas, qts]):
        print("[!] Error: No se encontraron todos los parámetros requeridos en el archivo TXT.")
        return
        
    nombre_parlante = os.path.basename(archivo_txt).replace(".txt", "").replace("_", " ")

    try:
        espesor_mdf_mm = float(input("Espesor del MDF (mm): "))
        diametro_str = input("Diámetro del transductor mayor (pulgadas) [Por defecto: 5.25]: ")
        diametro_pulgadas = float(diametro_str) if diametro_str.strip() else 5.25
    except ValueError:
        print("[!] Error en el ingreso de datos.")
        return

    espesor_cm = round(espesor_mdf_mm / 10.0, 1)
    
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    root_phi = math.sqrt(phi)
    
    # 1. Cálculo del Volumen Neto óptimo EBS
    vb_neto = (2.0 - (1.0 / phi)) * 15.0 * vas * (math.pow(qts, 2.87))
    
    # 2. Cálculo Dinámico de Alfa (alfa = Vas / Vb) y del factor h
    alfa = vas / vb_neto
    h_dinamico = max(0.5, min(0.9, 0.9 * qts / math.sqrt(alfa)))
    fb = round(h_dinamico * fs, 2)
    
    area_puerto = sd * (root_phi - 1.0)
    
    # Longitud de puerto con factor de corrección de extremos (End Corr = 2.2)
    l_puerto_cm = round((28068.0 * area_puerto) / (vb_neto * (fb ** 2)) - (2.2 * math.sqrt(area_puerto)), 1)
    
    w_int_neto = round(((vb_neto * 1000.0) / (phi ** 1.5)) ** (1.0 / 3.0), 1)
    vol_aire_puerto = (area_puerto * l_puerto_cm) / 1000.0
    vol_mdf_puerto = (w_int_neto * l_puerto_cm * espesor_cm) / 1000.0
    vb_bruto = vb_neto + vol_aire_puerto + vol_mdf_puerto
    
    w_int = round(((vb_bruto * 1000.0) / (phi ** 1.5)) ** (1.0 / 3.0), 1)
    d_int = round(w_int * root_phi, 1)
    h_int = round(w_int * phi, 1)
    h_puerto_cm = round(area_puerto / w_int, 1)
    
    w_ext = round(w_int + (2 * espesor_cm), 1)
    h_ext = round(h_int + (2 * espesor_cm), 1)
    d_ext = round(d_int + (2 * espesor_cm), 1)
    h_frontal = round(h_int - h_puerto_cm, 1)

    # --- CÁLCULO DEL NODO ÁUREO Y AUDITORÍA DE COLISIÓN ---
    x_ideal_ext = w_ext / phi
    offset_ideal = abs(x_ideal_ext - (w_ext / 2.0))
    
    radio_jaula_cm = (diametro_pulgadas * 2.54) / 2.0
    margen_ruteo_cm = 1.0 
    offset_maximo = (w_int / 2.0) - (radio_jaula_cm + margen_ruteo_cm)
    
    alerta_colision_offset = False
    if offset_maximo < 0:
        print("\n[!] RIESGO CRÍTICO: El transductor es demasiado grande para el ancho interno.")
        offset_cm = 0.0
    elif offset_ideal > offset_maximo:
        offset_cm = round(offset_maximo, 2)
        alerta_colision_offset = True
    else:
        offset_cm = round(offset_ideal, 2)
    
    cortes = [
        ["2x Laterales Caja", h_ext, d_ext],
        ["2x Superior/Inferior Caja", w_int, d_ext],
        ["1x Panel Trasero Caja", h_int, w_int],
        ["1x Panel Frontal Caja", h_frontal, w_int],
    ]
    
    l_falso_piso = round(d_int - h_puerto_cm - espesor_cm, 1)
    l_req_interna = round(l_puerto_cm - espesor_cm, 1)
    
    l_falso_respaldo = 0
    l_falso_techo = 0
    l_mdf_recto = 0
    alerta_colision_techo = False
    
    if l_req_interna <= l_falso_piso:
        tipo_puerto = "Línea Recta Interna (I)"
        l_mdf_recto = l_req_interna
        cortes.append(["1x Falso Piso Puerto (Recto)", w_int, l_mdf_recto])
    else:
        l_restante = round(l_req_interna - l_falso_piso, 1)
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
                alerta_colision_techo = True

    base_name = os.path.basename(archivo_txt).replace(".txt", "")
    
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Planos Acústicos EBS y Deflector Asimétrico", ln=True, align='C')
    pdf.cell(0, 10, f"{nombre_parlante}", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"Parámetros Thiele-Small y Matriz EBS Dinámica (h = {h_dinamico:.2f}):", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 6, f"Frecuencia Fs: {fs} Hz | Vol Vas: {vas} L | Area Sd: {sd} cm2", ln=True)
    pdf.cell(0, 6, f"Factor Qts: {qts} | Alfa (Vas/Vb): {alfa:.3f} | Sintonía (Fb): {fb} Hz", ln=True)
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
    pdf.cell(0, 6, f"Área Transversal Estática: {area_puerto:.1f} cm2 | End Corr: 2.2", ln=True)
    if alerta_colision_techo:
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 6, "[!] RIESGO: El falso techo excede la profundidad interna.", ln=True)
        pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"Coordenadas de Ruteo (Desplazamiento Dinámico Áureo):", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, "Medidas desde la esquina inferior izquierda del Panel Frontal (0,0)", ln=True)
    
    pdf.cell(0, 6, f"Offset Áureo Ideal: {offset_ideal*10:.1f} mm | Tolerancia Mecánica Max: {max(0, offset_maximo)*10:.1f} mm", ln=True)
    
    if alerta_colision_offset:
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 6, f"[!] COLISIÓN EVITADA: Offset truncado a {offset_cm*10:.1f} mm para proteger jaula de {diametro_pulgadas}\".", ln=True)
        pdf.set_text_color(0, 0, 0)
    else:
        pdf.cell(0, 6, f"[+] SEGURIDAD MECÁNICA: El offset áureo de {offset_cm*10:.1f} mm no colisiona.", ln=True)
        
    centro_x_base = w_int / 2
    centro_y_woofer = h_frontal * 0.35
    centro_y_tweeter = h_frontal * 0.75
    x_izq = centro_x_base - offset_cm
    x_der = centro_x_base + offset_cm

    pdf.cell(0, 6, f"> Caja L (Izquierda): Eje X = {x_izq:.1f} cm | Y Woofer = {centro_y_woofer:.1f} cm | Y Tweeter = {centro_y_tweeter:.1f} cm", ln=True)
    pdf.cell(0, 6, f"> Caja R (Derecha)  : Eje X = {x_der:.1f} cm | Y Woofer = {centro_y_woofer:.1f} cm | Y Tweeter = {centro_y_tweeter:.1f} cm", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"Despiece MDF {espesor_mdf_mm:.0f} mm:", ln=True)
    pdf.set_font("Courier", '', 10)
    
    for corte in cortes:
        pdf.cell(0, 6, f"{corte[0]:<35} | {corte[1]:>5.1f} cm x {corte[2]:>5.2f} cm", ln=True)

    if GRAFICOS_DISPONIBLES:
        ruta_lat, ruta_front = renderizar_planos_2d(
            base_name, d_int, w_int, h_int, espesor_cm, h_puerto_cm, l_mdf_recto, 
            l_falso_piso, l_falso_respaldo, l_falso_techo, tipo_puerto, offset_cm
        )
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Esquemática de Ensamblaje y Deflectores Espejados", ln=True, align='C')
        pdf.image(ruta_lat, x=60, y=25, w=90)
        pdf.image(ruta_front, x=10, y=140, w=190)

    pdf_filename = os.path.join("data", f"{base_name}_panels.pdf")
    pdf.output(pdf_filename)
    print(f"\n[+] PDF generado: '{pdf_filename}'")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        calcular_cortes_caja(sys.argv[1])
    else:
        print("[!] Ruta del archivo TXT exportado por REW no proporcionada.")