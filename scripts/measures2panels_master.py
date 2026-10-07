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
    print("[!] Librería 'matplotlib' no encontrada. Instálala con 'pip install matplotlib' para generar los planos.")

# --- BASE DE DATOS PVC CHILE ---
PVC_MERCADO = [
    {"nom": "40 mm", "int": 3.6},
    {"nom": "50 mm", "int": 4.6},
    {"nom": "75 mm", "int": 7.1},
    {"nom": "110 mm", "int": 10.4}
]

# --- SOLUCIONADOR NUMÉRICO ---
def solucionador_numerico_thiele_small(qts, vas, fs, ql=7.0):
    vb_semilla = 15.0 * vas * (math.pow(qts, 2.87))
    fb_semilla = fs * 0.42 * (math.pow(qts, -0.9))
    vb_min, vb_max = vb_semilla * 0.7, vb_semilla * 1.3
    fb_min, fb_max = fb_semilla * 0.7, fb_semilla * 1.3
    mejor_vb, mejor_fb = vb_semilla, fb_semilla
    menor_f3 = fs * 5.0
    pasos = 50
    step_vb = (vb_max - vb_min) / pasos
    step_fb = (fb_max - fb_min) / pasos
    for i in range(pasos):
        vb_test = vb_min + (i * step_vb)
        alpha_test = vas / vb_test
        for j in range(pasos):
            fb_test = fb_min + (j * step_fb)
            h_test = fb_test / fs
            peak_db = 0.0
            f3_test = 0.0
            encontro_f3 = False
            for k in range(10, 300, 2):
                x = (fs * (k / 100.0)) / fs
                t1 = (x**4) - (x**2) * (1.0 + h_test**2 + alpha_test + (h_test / (ql * qts))) + (h_test**2)
                t2 = (x**3) * ((1.0 / qts) + (h_test / ql)) - x * ((h_test**2 / qts) + (h_test / ql))
                den = math.sqrt(t1**2 + t2**2)
                if den > 0:
                    db = 20 * math.log10(((x**4) / den) + 1e-12)
                    if db > peak_db: peak_db = db
                    if db >= -3.0 and not encontro_f3:
                        f3_test = fs * x
                        encontro_f3 = True
            if peak_db < 0.1 and encontro_f3:
                if f3_test < menor_f3:
                    menor_f3 = f3_test
                    mejor_vb = vb_test
                    mejor_fb = fb_test
    return round(mejor_vb, 2), round(mejor_fb, 2)

def graficar_spl(fs, qts, vas, vb, fb, qtc_target, es_caja_cerrada, base_name):
    freqs = list(range(10, 501))
    dbs = []
    
    for f in freqs:
        if es_caja_cerrada:
            fc = fs * (qtc_target / qts)
            x = f / fc
            den = math.sqrt((1 - x**2)**2 + (x / qtc_target)**2)
            mag = (x**2) / den if den > 0 else 1e-12
        else:
            x = f / fs
            h = fb / fs
            alpha = vas / vb
            ql = 7.0
            t1 = (x**4) - (x**2)*(1.0 + h**2 + alpha + (h/(ql*qts))) + (h**2)
            t2 = (x**3)*((1.0/qts) + (h/ql)) - x*((h**2/qts) + (h/ql))
            den = math.sqrt(t1**2 + t2**2)
            mag = (x**4) / den if den > 0 else 1e-12
        db = 20 * math.log10(mag + 1e-12)
        dbs.append(max(db, -30)) 
        
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.set_facecolor('#f8f9fa')
    
    # Relleno y línea principal
    ax.plot(freqs, dbs, color='#00529b', linewidth=2.5, zorder=3)
    ax.fill_between(freqs, -30, dbs, color='#00529b', alpha=0.15, zorder=2)
    
    # Líneas de referencia
    ax.axhline(0, color='#333333', linestyle='-', linewidth=1.2, zorder=1)
    ax.axhline(-3, color='#d62728', linestyle='--', linewidth=1.5, zorder=1, label='-3 dB')
    
    # Encontrar y anotar F3
    f3_hz = None
    for f, db in zip(freqs, dbs):
        if db >= -3.0:
            f3_hz = f
            break
            
    if f3_hz:
        ax.plot(f3_hz, -3, 'ro', markersize=6, zorder=4)
        ax.annotate(f'F3 ≈ {f3_hz} Hz', xy=(f3_hz, -3), xytext=(f3_hz * 1.5, -8),
                     arrowprops=dict(facecolor='#d62728', shrink=0.05, width=1.5, headwidth=6),
                     fontsize=10, fontweight='bold', bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#d62728", lw=1), zorder=5)

    ax.set_xscale('log')
    ax.set_xlim(10, 500)
    ax.set_ylim(-20, 5)
    
    # Estilizar grilla logarítmica
    ax.grid(True, which="major", ls="-", color="#dddddd", linewidth=1)
    ax.grid(True, which="minor", ls=":", color="#eeeeee", linewidth=0.8)
    
    ax.set_title(f"Respuesta de Frecuencia Simulada - {'Sellada/Aperiódica' if es_caja_cerrada else 'Bass Reflex'}", pad=15, fontweight='bold', color="#00529b")
    ax.set_xlabel("Frecuencia (Hz)", fontweight='bold')
    ax.set_ylabel("Amplitud Relativa (dB)", fontweight='bold')
    
    plt.tight_layout()
    ruta = os.path.join("data", f"{base_name}_spl.png")
    plt.savefig(ruta, dpi=300)
    plt.close()
    return ruta

def calcular_offset(w_ext, w_int, diam_pulg):
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    x_ideal_ext = round(w_ext / phi, 1)
    offset_ideal = round(abs(x_ideal_ext - (w_ext / 2.0)), 1)
    radio_jaula_cm = round((diam_pulg * 2.54) / 2.0, 1)
    offset_maximo = round((w_int / 2.0) - (radio_jaula_cm + 1.0), 1)
    
    alerta = False
    if offset_maximo < 0:
        offset_final = 0.0
        alerta = True
    elif offset_ideal > offset_maximo:
        offset_final = offset_maximo
        alerta = True
    else:
        offset_final = offset_ideal
        
    return offset_final, offset_ideal, offset_maximo, alerta

def renderizar_esquemas(base_name, variante, d_int, w_int, h_int, espesor, offset_cm, es_caja_cerrada, param_puerto, es_sandwich=False):
    d_ext = round(d_int + (2 * espesor), 1)
    h_ext = round(h_int + (2 * espesor), 1)
    w_ext = round(w_int + (2 * espesor), 1)
    
    color_mdf = '#F4E3C5' # Más suave, tipo CAD
    borde_mdf = '#A67D3D'
    
    def agregar_panel(ax, x, y, ancho, alto):
        # Efecto de panel con textura simulada ligera
        panel = patches.Rectangle((x, y), ancho, alto, linewidth=1.5, edgecolor=borde_mdf, facecolor=color_mdf, zorder=3)
        ax.add_patch(panel)

    def cota(ax, x1, y1, x2, y2, text, rot=0, offset_text_x=0, offset_text_y=0):
        # Dibuja línea de cota estilo CAD
        ax.annotate('', xy=(x1, y1), xytext=(x2, y2), 
                    arrowprops=dict(arrowstyle='<|-|>', color='#00529b', lw=1.2, shrinkA=0, shrinkB=0))
        mx, my = (x1+x2)/2 + offset_text_x, (y1+y2)/2 + offset_text_y
        ax.text(mx, my, text, color='#00529b', ha='center', va='center', rotation=rot,
                fontsize=9, fontweight='bold', bbox=dict(facecolor='white', edgecolor='none', pad=1))

    # --- 1. LATERAL ---
    fig, ax = plt.subplots(figsize=(5, 7))
    ax.set_xlim(-3, d_ext + 3); ax.set_ylim(-3, h_ext + 3); ax.set_aspect('equal'); ax.axis('off')
    ax.set_title(f"Corte Lateral - {variante}", fontsize=12, fontweight='bold', color="#333333", pad=15)
    
    if es_sandwich:
        agregar_panel(ax, 0, 0, espesor, h_ext) # Frontal completo
        agregar_panel(ax, d_ext - espesor, 0, espesor, h_ext) # Trasero completo
        agregar_panel(ax, espesor, h_ext - espesor, d_int, espesor) # Techo empotrado
        agregar_panel(ax, espesor, 0, d_int, espesor) # Piso empotrado
        
        if param_puerto.get('es_aperiodica', False):
            diam_ap = param_puerto.get('diam_ap', 5.0)
            y_centro_vent = round(espesor + (h_int * 0.35), 1)
            y_vent_inf = y_centro_vent - (diam_ap / 2.0)
            ax.add_patch(patches.Rectangle((d_ext - espesor, y_vent_inf), espesor, diam_ap, color='white', zorder=4))
            ax.add_patch(patches.Rectangle((d_ext - espesor, y_vent_inf), espesor, diam_ap, fill=False, hatch='///', edgecolor='red', zorder=5))
            ax.text(d_ext + 0.5, y_centro_vent, "Variovent", color='red', fontsize=8, va='center', rotation=270, zorder=6)
        elif not es_caja_cerrada and variante == "PVC":
            l_pvc = param_puerto['l_puerto']
            d_pvc = param_puerto['d_pvc']
            y_centro_tubo = round(espesor + (h_int * 0.25), 1)
            y_tubo_inf = y_centro_tubo - (d_pvc / 2.0)
            tubo = patches.Rectangle((d_ext - espesor - l_pvc, y_tubo_inf), l_pvc, d_pvc, linewidth=1.5, edgecolor='#555555', facecolor='#D3D3D3', alpha=0.7, zorder=2)
            ax.add_patch(tubo)
            ax.text(d_ext - espesor - (l_pvc/2), y_centro_tubo, f"PVC {l_pvc}cm", color='black', ha='center', va='center', fontsize=8, rotation=0, zorder=4)
    else:
        # Lógica original para MDF Ranurado
        agregar_panel(ax, 0, 0, d_ext, espesor) 
        agregar_panel(ax, 0, h_ext - espesor, d_ext, espesor) 
        
        if es_caja_cerrada:
            agregar_panel(ax, 0, espesor, espesor, h_int) 
            agregar_panel(ax, d_ext - espesor, espesor, espesor, h_int)
        else:
            if variante == "MDF":
                h_p = param_puerto['h_puerto']
                l_p = param_puerto['l_puerto']
                tipo = param_puerto['tipo']
                
                agregar_panel(ax, 0, espesor + h_p, espesor, h_int - h_p) 
                agregar_panel(ax, d_ext - espesor, espesor, espesor, h_int) 
                
                if "Recta" in tipo:
                    agregar_panel(ax, espesor, espesor + h_p, l_p - espesor, espesor)
                else:
                    l_falso_piso = param_puerto.get('l_falso_piso', 0.0)
                    l_falso_respaldo = param_puerto.get('l_falso_respaldo', 0.0)
                    l_falso_techo = param_puerto.get('l_falso_techo', 0.0)
                    
                    agregar_panel(ax, espesor, espesor + h_p, l_falso_piso, espesor) 
                    x_respaldo = round(espesor + l_falso_piso - espesor, 1)
                    y_respaldo = round(espesor + h_p + espesor, 1)
                    agregar_panel(ax, x_respaldo, y_respaldo, espesor, l_falso_respaldo) 
                    if "2 Codos" in tipo:
                        x_techo = round(x_respaldo - l_falso_techo, 1)
                        y_techo = round(y_respaldo + l_falso_respaldo, 1)
                        agregar_panel(ax, x_techo, y_techo, l_falso_techo, espesor)

    # Cotas Laterales
    cota(ax, -1.5, 0, -1.5, h_ext, f"{h_ext} cm", rot=90)
    cota(ax, 0, -1.5, d_ext, -1.5, f"{d_ext} cm")

    plt.tight_layout()
    ruta_lat = os.path.join("data", f"{base_name}_lat_{variante}.png")
    plt.savefig(ruta_lat, dpi=300, bbox_inches='tight')
    plt.close()
    
    # --- 2. FRONTALES ---
    fig2, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(10, 7))
    def dibujar_frontal(ax_obj, x_shift, titulo):
        ax_obj.set_xlim(-3, w_ext + 3); ax_obj.set_ylim(-3, h_ext + 3); ax_obj.set_aspect('equal'); ax_obj.axis('off')
        ax_obj.set_title(titulo, fontsize=12, fontweight='bold', color="#333333", pad=15)
        
        if es_sandwich:
            agregar_panel(ax_obj, 0, 0, w_ext, h_ext)
            ax_obj.add_patch(patches.Rectangle((espesor, espesor), w_int, h_int, linewidth=1, edgecolor='#888888', fill=False, linestyle='--', zorder=4))
            y_base_baffle = espesor
            h_frontal = h_int
        else:
            agregar_panel(ax_obj, 0, 0, espesor, h_ext)
            agregar_panel(ax_obj, w_ext - espesor, 0, espesor, h_ext)
            agregar_panel(ax_obj, espesor, 0, w_int, espesor)
            agregar_panel(ax_obj, espesor, h_ext - espesor, w_int, espesor)
            
            h_frontal = round(h_int - param_puerto.get('h_puerto', 0.0) if variante == "MDF" and not es_caja_cerrada else h_int, 1)
            y_base_baffle = round(espesor + param_puerto.get('h_puerto', 0.0) if variante == "MDF" and not es_caja_cerrada else espesor, 1)
            agregar_panel(ax_obj, espesor, y_base_baffle, w_int, h_frontal)
        
        centro_x = round((w_ext / 2) + x_shift, 1)
        centro_y_woofer = round(y_base_baffle + (h_frontal * 0.35), 1)
        centro_y_tweeter = round(y_base_baffle + (h_frontal * 0.75), 1)
        
        radio_w = w_int * 0.35
        radio_t = w_int * 0.15
        
        # Renderizado más detallado del Woofer
        ax_obj.add_patch(patches.Circle((centro_x, centro_y_woofer), radio_w, linewidth=1.5, edgecolor='#111', facecolor='#2c2c2c', zorder=4)) # Marco exterior
        ax_obj.add_patch(patches.Circle((centro_x, centro_y_woofer), radio_w * 0.88, linewidth=0.5, edgecolor='#000', facecolor='#3d3d3d', zorder=5)) # Suspensión
        ax_obj.add_patch(patches.Circle((centro_x, centro_y_woofer), radio_w * 0.75, linewidth=0.5, edgecolor='#333', facecolor='#525252', zorder=6)) # Cono
        ax_obj.add_patch(patches.Circle((centro_x, centro_y_woofer), radio_w * 0.25, linewidth=0.5, edgecolor='#222', facecolor='#222222', zorder=7)) # Dust cap
        
        # Renderizado más detallado del Tweeter
        ax_obj.add_patch(patches.Circle((centro_x, centro_y_tweeter), radio_t, linewidth=1.5, edgecolor='#111', facecolor='#1a1a1a', zorder=4))
        ax_obj.add_patch(patches.Circle((centro_x, centro_y_tweeter), radio_t * 0.5, linewidth=0.5, edgecolor='#000', facecolor='#333333', zorder=5)) # Domo tweeter
        
        if not es_caja_cerrada:
            if variante == "MDF" and not es_sandwich:
                h_p = param_puerto['h_puerto']
                ax_obj.text(w_ext / 2, espesor + (h_p / 2), f"Puerto: {h_p:.1f} cm", color='black', ha='center', va='center', fontsize=9, fontweight='bold', zorder=6)
            elif variante == "PVC":
                d_pvc = param_puerto['d_pvc']
                centro_y_puerto = round(espesor + (h_int * 0.25), 1)
                ax_obj.add_patch(patches.Circle((w_ext / 2, centro_y_puerto), d_pvc / 2, linewidth=1.5, edgecolor='#444444', facecolor='#111111', alpha=0.5, zorder=3, linestyle='--'))
                ax_obj.text(w_ext / 2, centro_y_puerto, f"PVC Atrás", color='white', ha='center', va='center', fontsize=8, fontweight='bold', zorder=6)
        elif param_puerto.get('es_aperiodica', False):
            diam_ap = param_puerto.get('diam_ap', 5.0)
            centro_y_vent = centro_y_woofer
            ax_obj.add_patch(patches.Circle((w_ext / 2, centro_y_vent), diam_ap / 2, linewidth=1.5, edgecolor='#d62728', facecolor='#222222', alpha=0.3, zorder=3, linestyle='--'))
            ax_obj.text(w_ext / 2, centro_y_vent, f"Aperiódica\n{diam_ap}cm (Atrás)", color='#d62728', ha='center', va='center', fontsize=8, fontweight='bold', zorder=6)

        # Cotas Frontales
        cota(ax_obj, -1.5, 0, -1.5, h_ext, f"{h_ext} cm", rot=90)
        cota(ax_obj, 0, -1.5, w_ext, -1.5, f"{w_ext} cm")

    dibujar_frontal(ax_l, offset_cm, "Caja Izquierda (L)")
    dibujar_frontal(ax_r, -offset_cm, "Caja Derecha (R)")
    
    plt.tight_layout()
    ruta_front = os.path.join("data", f"{base_name}_front_{variante}.png")
    plt.savefig(ruta_front, dpi=300, bbox_inches='tight')
    plt.close()
    
    return ruta_lat, ruta_front

def extraer_parametros(archivo):
    p = {'fs': 0.0, 'sd': 0.0, 'vas': 0.0, 'qts': 0.0}
    with open(archivo, 'r', encoding='utf-8') as f:
        cont = f.read()
        for param in p.keys():
            m = re.search(fr'{param}s?\s*(?:=)?\s*([\d\.]+)', cont, re.IGNORECASE)
            if m: p[param] = float(m.group(1))
    if not all(p.values()):
        print(f"[!] Error: Faltan parámetros en {archivo}")
        sys.exit(1)
    return p

def main():
    archivos = sys.argv[1:]
    if len(archivos) == 0:
        print("[!] Proporciona 1 o 2 archivos TXT como argumentos.")
        return
        
    os.makedirs("data", exist_ok=True)
    graficos_gen = []
    
    if len(archivos) == 2:
        print(f"[>] Promediando transductores...")
        p1, p2 = extraer_parametros(archivos[0]), extraer_parametros(archivos[1])
        fs = round((p1['fs'] + p2['fs']) / 2, 2)
        sd = round((p1['sd'] + p2['sd']) / 2, 2)
        vas = round((p1['vas'] + p2['vas']) / 2, 2)
        qts = round((p1['qts'] + p2['qts']) / 2, 3)
        n1 = os.path.basename(archivos[0]).replace(".txt", "")
        n2 = os.path.basename(archivos[1]).replace(".txt", "")
        base_name = os.path.commonprefix([n1, n2]).strip(" -_")
        if not base_name: base_name = "Master_Promediado"
    else:
        print(f"[>] Procesando transductor: {archivos[0]}")
        p = extraer_parametros(archivos[0])
        fs, sd, vas, qts = p['fs'], p['sd'], p['vas'], p['qts']
        base_name = os.path.basename(archivos[0]).replace(".txt", "")

    try:
        espesor_cm = float(input("\nEspesor del MDF (mm): ")) / 10.0
        diam_pulg = float(input("Diámetro transductor mayor (pulg) [Ej: 5.25]: ") or "5.25")
    except ValueError:
        print("[!] Entrada inválida.")
        return

    phi = (1.0 + math.sqrt(5.0)) / 2.0
    root_phi = math.sqrt(phi)
    
    es_aperiodica = qts > 0.80
    es_sellada = qts >= 0.55 and not es_aperiodica
    es_caja_cerrada = es_sellada or es_aperiodica
    diam_ap = 0.0

    if es_aperiodica:
        modo_alineamiento = "Topología Aperiódica (Variovent)"
        alfa = 1.5
        vb_neto = round(vas / alfa, 1)
        fb = 0.0
        qtc_target = 0.707 
        area_ap = round(sd * 0.25, 1) 
        diam_ap = round(math.sqrt((4 * area_ap) / math.pi), 1)
    elif es_sellada:
        qtc_target = max(0.90, qts * 1.15)
        alfa = round((qtc_target / qts)**2 - 1.0, 3)
        vb_neto = round(vas / alfa, 1)
        fb = 0.0
        modo_alineamiento = "Suspensión Acústica (Sellada)"
    else:
        qtc_target = 0.0
        if qts >= 0.42:
            modo_alineamiento = "EBS Dinámico"
            vb_neto = round((2.0 - (1.0 / phi)) * 15.0 * vas * (math.pow(qts, 2.87)), 1)
            alfa = round(vas / vb_neto, 2)
            fb = round(round(max(0.5, min(0.9, 0.9 * qts / math.sqrt(alfa))), 2) * fs, 1)
        else:
            modo_alineamiento = "QB3 (Numérico)"
            vb_neto, fb_raw = solucionador_numerico_thiele_small(qts, vas, fs)
            vb_neto, fb = round(vb_neto, 1), round(fb_raw, 1)

    # --- GEOMETRÍA A: MDF SLOTTED ---
    h_pmdf = l_pmdf = v_mdf_p = v_aire_mdf = a_pmdf = 0.0
    estado_mdf = "N/A"
    tipo_pmdf = "Caja Sellada"
    l_mdf_recto = l_falso_piso = l_falso_respaldo = l_falso_techo = 0.0
    
    if not es_caja_cerrada:
        w_int_est = round(((vb_neto * 1000.0) / (phi ** 1.5)) ** (1.0 / 3.0), 1)
        d_int_est = round(w_int_est * root_phi, 1)
        
        a_pmdf = round(sd * (phi - 1.0) / phi, 1) 
        a_q, b_q, c_q = 1.0 + ((28068.0 * w_int_est)/(vb_neto*(fb**2))), -2.2 * math.sqrt(w_int_est), -(espesor_cm + d_int_est)
        disc = (b_q**2) - (4*a_q*c_q)
        if disc > 0:
            h_calc = round(((-b_q + math.sqrt(disc)) / (2*a_q))**2, 1)
            if (h_calc * w_int_est) >= 0.2 * sd:
                a_pmdf, h_pmdf = round(h_calc * w_int_est, 1), h_calc
        
        if h_pmdf == 0.0:
            h_pmdf = round(a_pmdf / w_int_est, 1)
            estado_mdf = "Ranura Forzada (Laberinto)"
        else: estado_mdf = "Ranura Exacta"
            
        l_pmdf = round((28068.0 * a_pmdf)/(vb_neto*(fb**2)) - (2.2*math.sqrt(a_pmdf)), 1)
        v_aire_mdf = round((a_pmdf * l_pmdf)/1000.0, 1)
        v_mdf_p = round((w_int_est * l_pmdf * espesor_cm)/1000.0, 1)

    vb_b_mdf = round(vb_neto + v_aire_mdf + v_mdf_p, 1)
    w_mdf = round(((vb_b_mdf * 1000.0)/(phi**1.5))**(1.0/3.0), 1)
    d_mdf = round(w_mdf * root_phi, 1)
    h_mdf = round(w_mdf * phi, 1)
    
    if es_caja_cerrada:
        cortes_mdf = [["4x Panel Frontal/Trasero", round(h_mdf+(2*espesor_cm),1), round(w_mdf+(2*espesor_cm),1)],
                      ["4x Sup/Inf (Techo/Piso)", round(w_mdf+(2*espesor_cm),1), d_mdf],
                      ["4x Laterales", h_mdf, d_mdf]]
    else:
        cortes_mdf = [["4x Laterales", round(h_mdf+(2*espesor_cm),1), round(d_mdf+(2*espesor_cm),1)],
                      ["4x Sup/Inf", w_mdf, round(d_mdf+(2*espesor_cm),1)],
                      ["2x Panel Trasero", h_mdf, w_mdf],
                      ["2x Panel Frontal", round(h_mdf - h_pmdf,1), w_mdf]]
        l_falso_piso = round(d_mdf - h_pmdf, 1)
        l_req_int = round(l_pmdf - espesor_cm, 1)
        if l_req_int <= l_falso_piso + 0.1:
            tipo_pmdf = "Recta"
            l_mdf_recto = l_req_int
            cortes_mdf.append(["2x Falso Piso (Recto)", w_mdf, l_mdf_recto])
        else:
            l_rest = round(l_req_int - l_falso_piso, 1)
            l_resp_max = round(h_mdf - (2*h_pmdf) - (2*espesor_cm), 1)
            if l_rest <= l_resp_max:
                tipo_pmdf = "Laberinto 1 Codo"
                l_falso_respaldo = l_rest
                cortes_mdf.extend([["2x Falso Piso", w_mdf, l_falso_piso], ["2x Respaldo (Sube)", w_mdf, l_falso_respaldo]])
            else:
                tipo_pmdf = "Laberinto 2 Codos"
                l_falso_respaldo = l_resp_max
                l_falso_techo = round(l_rest - l_resp_max, 1)
                cortes_mdf.extend([["2x Falso Piso", w_mdf, l_falso_piso], ["2x Respaldo", w_mdf, l_falso_respaldo], ["2x Techo (Vuelve)", w_mdf, l_falso_techo]])

    off_m_val, _, _, off_m_alert = calcular_offset(round(w_mdf+(2*espesor_cm),1), w_mdf, diam_pulg)

    # --- GEOMETRÍA B: PVC ---
    tubo_pvc = None
    l_pvc = v_pvc_despl = d_pvc = 0.0
    estado_pvc = "N/A"
    
    if not es_caja_cerrada:
        tubo_pvc = next((t for t in PVC_MERCADO if math.pi*((t["int"]/2.0)**2) >= 0.2*sd), PVC_MERCADO[-1])
        d_pvc = tubo_pvc["int"]
        a_real = math.pi * ((d_pvc / 2.0)**2)
        l_pvc = round((28068.0 * a_real) / (vb_neto * (fb**2)) - (2.2 * math.sqrt(a_real)), 1)
        v_pvc_despl = round((math.pi * ((d_pvc/2.0 + 0.2)**2) * l_pvc) / 1000.0, 2)
        estado_pvc = f"{tubo_pvc['nom']} (L={l_pvc}cm)"

    vb_b_pvc = round(vb_neto + v_pvc_despl, 1)
    w_pvc = round(((vb_b_pvc * 1000.0)/(phi**1.5))**(1.0/3.0), 1)
    d_pvc_dim = round(w_pvc * root_phi, 1)
    h_pvc = round(w_pvc * phi, 1)
    
    cortes_pvc = [["4x Panel Frontal/Trasero", round(h_pvc+(2*espesor_cm),1), round(w_pvc+(2*espesor_cm),1)],
                  ["4x Sup/Inf (Techo/Piso)", round(w_pvc+(2*espesor_cm),1), d_pvc_dim],
                  ["4x Laterales", h_pvc, d_pvc_dim]]

    off_p_val, _, _, off_p_alert = calcular_offset(round(w_pvc+(2*espesor_cm),1), w_pvc, diam_pulg)

    # --- RENDERIZADO Y PDF ---
    if GRAFICOS_DISPONIBLES:
        ruta_spl = graficar_spl(fs, qts, vas, vb_neto, fb, qtc_target, es_caja_cerrada, base_name)
        graficos_gen.append(ruta_spl)
        
        r_mdf_lat, r_mdf_front = renderizar_esquemas(base_name, "MDF", d_mdf, w_mdf, h_mdf, espesor_cm, off_m_val, es_caja_cerrada, 
                                                     {'h_puerto':h_pmdf, 'l_puerto':l_pmdf, 'tipo':tipo_pmdf, 'l_falso_piso':l_falso_piso, 'l_falso_respaldo':l_falso_respaldo, 'l_falso_techo':l_falso_techo, 'es_aperiodica': es_aperiodica, 'diam_ap': diam_ap},
                                                     es_sandwich=es_caja_cerrada)
        graficos_gen.extend([r_mdf_lat, r_mdf_front])
        
        r_pvc_lat, r_pvc_front = renderizar_esquemas(base_name, "PVC", d_pvc_dim, w_pvc, h_pvc, espesor_cm, off_p_val, es_caja_cerrada, 
                                                     {'h_puerto':0.0, 'l_puerto':l_pvc, 'd_pvc':d_pvc, 'es_aperiodica': es_aperiodica, 'diam_ap': diam_ap},
                                                     es_sandwich=True)
        graficos_gen.extend([r_pvc_lat, r_pvc_front])

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # FORMATO HELPER
    def draw_section_title(pdf_obj, title):
        pdf_obj.set_font("Arial", 'B', 14)
        pdf_obj.set_text_color(255, 255, 255)
        pdf_obj.set_fill_color(0, 82, 155)
        pdf_obj.cell(0, 10, f"  {title}", ln=True, fill=True)
        pdf_obj.set_text_color(0, 0, 0)
        pdf_obj.ln(3)

    # PÁGINA 1: SPL y Matriz
    pdf.add_page()
    pdf.set_font("Arial", 'B', 18)
    pdf.set_text_color(0, 82, 155)
    pdf.cell(0, 12, f"Diseño Acústico: {base_name}", ln=True, align='C')
    pdf.set_draw_color(0, 82, 155)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    draw_section_title(pdf, f"Matriz Termodinámica ({modo_alineamiento})")
    
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 6, f"  •  Fs: {fs} Hz     •  Vas: {vas} L     •  Qts: {qts}     •  Sd: {sd} cm²", ln=True)
    if es_aperiodica:
        pdf.cell(0, 6, f"  •  Vb Neto Ideal: {vb_neto} L     •  Válvula Resistiva: {diam_ap} cm", ln=True)
    else:
        pdf.cell(0, 6, f"  •  Vb Neto Ideal: {vb_neto} L     •  Sintonía (Fb): {fb} Hz", ln=True)
    pdf.ln(2)
        
    if GRAFICOS_DISPONIBLES:
        y_spl = pdf.get_y() + 5
        pdf.image(ruta_spl, x=15, y=y_spl, w=180)
    
    if es_caja_cerrada:
        pdf.add_page()
        titulo = "Arquitectura Aperiódica (Variovent)" if es_aperiodica else "Arquitectura Sellada Única"
        draw_section_title(pdf, f"{titulo} - Topología Sándwich")
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 6, f"  Dimensiones Internas: {w_mdf} x {d_mdf} x {h_mdf} cm", ln=True)
        pdf.cell(0, 6, f"  Offset Áureo (Mitigación Difracción): {off_m_val*10} mm", ln=True)
        if es_aperiodica:
            pdf.ln(2)
            pdf.set_text_color(200,0,0)
            pdf.cell(0, 6, f"  [!] Válvula Resistiva: Perforación en panel trasero de {diam_ap} cm de diámetro.", ln=True)
            pdf.cell(0, 6, "      Rellenar el orificio comprimiendo densamente lana mineral o fibra acústica.", ln=True)
            pdf.set_text_color(0,0,0)
            
        pdf.ln(5); pdf.set_font("Courier", 'B', 10)
        pdf.cell(0, 6, "  TABLA DE CORTES:", ln=True)
        pdf.set_font("Courier", '', 10)
        for c in cortes_mdf: pdf.cell(0, 6, f"  - {c[0]:<25} | {c[1]:>5.1f} cm x {c[2]:>5.1f} cm", ln=True)
        
        if GRAFICOS_DISPONIBLES:
            y_img = pdf.get_y() + 5
            pdf.image(r_mdf_lat, x=10, y=y_img, w=65)
            pdf.image(r_mdf_front, x=80, y=y_img, w=115)
    else:
        # PÁGINA 2: MDF Slotted
        pdf.add_page()
        draw_section_title(pdf, "Opción A: Gabinete con Puerto Ranurado (MDF)")
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 6, f"  Volumen Bruto (por madera interna): {vb_b_mdf} L", ln=True)
        pdf.cell(0, 6, f"  Internas: {w_mdf} x {d_mdf} x {h_mdf} cm   |   Puerto: Alto {h_pmdf} x Largo {l_pmdf} cm", ln=True)
        pdf.cell(0, 6, f"  Offset Áureo (Mitigación Difracción): {off_m_val*10} mm", ln=True)
        if off_m_alert: pdf.set_text_color(255,0,0); pdf.cell(0, 6, "  [!] Offset modificado por límite de chasis frontal.", ln=True); pdf.set_text_color(0,0,0)
        
        pdf.ln(5); pdf.set_font("Courier", 'B', 10)
        pdf.cell(0, 6, "  TABLA DE CORTES:", ln=True)
        pdf.set_font("Courier", '', 10)
        for c in cortes_mdf: pdf.cell(0, 6, f"  - {c[0]:<25} | {c[1]:>5.1f} cm x {c[2]:>5.1f} cm", ln=True)
        
        if GRAFICOS_DISPONIBLES:
            y_img = pdf.get_y() + 5
            pdf.image(r_mdf_lat, x=10, y=y_img, w=65)
            pdf.image(r_mdf_front, x=80, y=y_img, w=115)

        # PÁGINA 3: PVC
        pdf.add_page()
        draw_section_title(pdf, "Opción B: Gabinete con Tubo Cilíndrico (PVC)")
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 6, f"  Volumen Bruto (optimizado): {vb_b_pvc} L", ln=True)
        pdf.cell(0, 6, f"  Internas: {w_pvc} x {d_pvc_dim} x {h_pvc} cm   |   PVC: {estado_pvc}", ln=True)
        pdf.cell(0, 6, f"  Offset Áureo (Mitigación Difracción): {off_p_val*10} mm", ln=True)
        if l_pvc > (d_pvc_dim - 2.0): pdf.set_text_color(255,0,0); pdf.cell(0, 6, "  [!] RIESGO MECÁNICO: Tubo requiere Codo 90°.", ln=True); pdf.set_text_color(0,0,0)
        
        pdf.ln(5); pdf.set_font("Courier", 'B', 10)
        pdf.cell(0, 6, "  TABLA DE CORTES:", ln=True)
        pdf.set_font("Courier", '', 10)
        for c in cortes_pvc: pdf.cell(0, 6, f"  - {c[0]:<25} | {c[1]:>5.1f} cm x {c[2]:>5.1f} cm", ln=True)
        
        if GRAFICOS_DISPONIBLES:
            y_img = pdf.get_y() + 5
            pdf.image(r_pvc_lat, x=10, y=y_img, w=65)
            pdf.image(r_pvc_front, x=80, y=y_img, w=115)

    pdf_filename = os.path.join("data", f"{base_name}.pdf")
    pdf.output(pdf_filename)
    print(f"\n[+] PDF generado exitosamente: '{pdf_filename}'")
    
    # Recolección de Basura Estricta
    for f in graficos_gen:
        try: os.remove(f)
        except OSError: pass
    print("[+] Limpieza de gráficos temporales completada. Directorio despejado.")

if __name__ == "__main__":
    main()