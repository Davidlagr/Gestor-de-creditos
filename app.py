import streamlit as st
import json
import math
from datetime import datetime, timedelta, date
import pandas as pd
import io
from fpdf import FPDF

# -----------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# -----------------------------------------
st.set_page_config(page_title="Gestor de Préstamos", page_icon="💰", layout="centered")

st.markdown("""
    <style>
    .big-font { font-size:20px !important; font-weight: bold; }
    .stButton>button { width: 100%; height: 60px; font-size: 20px; font-weight: bold; border-radius: 10px; }
    .ahorro-box { background-color: #d4edda; color: #155724; padding: 15px; border-radius: 10px; border: 1px solid #c3e6cb; margin-bottom: 20px;}
    .info-box { background-color: #e2e3e5; color: #383d41; padding: 15px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #6c757d;}
    </style>
    """, unsafe_allow_html=True)

# -----------------------------------------
# FUNCIONES MATEMÁTICAS (SECTOR FINANCIERO)
# -----------------------------------------
def calcular_cuota(capital, tasa_mensual, meses):
    if tasa_mensual <= 0 or meses <= 0: return capital / max(meses, 1)
    r = tasa_mensual / 100
    return capital * (r * (1 + r)**meses) / ((1 + r)**meses - 1)

def calcular_meses(capital, tasa_mensual, cuota):
    if tasa_mensual <= 0: return capital / max(cuota, 1)
    r = tasa_mensual / 100
    if cuota <= r * capital: return 999
    return -math.log(1 - (r * capital) / cuota) / math.log(1 + r)

def calcular_saldo_restante(cuota, tasa_mensual, meses_restantes):
    if tasa_mensual <= 0: return cuota * meses_restantes
    r = tasa_mensual / 100
    return cuota * (1 - (1 + r)**-meses_restantes) / r

def parse_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").date()

def calcular_interes_diario(saldo, tasa_mensual, dias):
    tasa_diaria = (tasa_mensual / 100) / 30
    return saldo * tasa_diaria * dias

# -----------------------------------------
# FUNCIONES DE EXPORTACIÓN (PDF Y EXCEL)
# -----------------------------------------
def generar_pdf(cred):
    pdf = FPDF()
    pdf.add_page()
    
    def limpiar_texto(texto):
        return str(texto).encode('latin-1', 'replace').decode('latin-1')

    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt="ESTADO DE CUENTA", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, txt=limpiar_texto(f"Cliente: {cred['nombre']}"), ln=True)
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 10, txt=limpiar_texto(f"Descripcion: {cred['descripcion']}"), ln=True)
    pdf.cell(200, 10, txt=f"Monto Inicial Prestado: ${cred['monto_inicial']:,.0f}", ln=True)
    pdf.cell(200, 10, txt=f"Saldo Actual Adeudado: ${cred['saldo_actual']:,.0f}", ln=True)
    pdf.cell(200, 10, txt=f"Valor de la Cuota: ${cred['cuota_actual']:,.0f}", ln=True)
    pdf.cell(200, 10, txt=f"Interes Mensual: {cred['tasa_mensual']}%", ln=True)
    pdf.cell(200, 10, txt=f"Proximo Vencimiento: {cred['fecha_proximo_vencimiento']}", ln=True)
    
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, txt="HISTORIAL DE PAGOS:", ln=True)
    
    pdf.set_font("Arial", "", 10)
    if cred['historial']:
        for pago in cred['historial']:
            texto = f"Fecha: {pago['Fecha']} | Abono Capital: {pago['Abono a Capital']} | Interes Pagado: {pago['Interés Cubierto']} | Saldo: {pago['Nuevo Saldo']}"
            pdf.cell(200, 8, txt=limpiar_texto(texto), ln=True)
    else:
        pdf.cell(200, 10, txt="No se han registrado pagos todavia.", ln=True)
        
    return pdf.output(dest="S").encode("latin-1")

def generar_excel(cred):
    df_resumen = pd.DataFrame([{
        "Cliente": cred['nombre'],
        "Descripción": cred['descripcion'],
        "Monto Inicial": cred['monto_inicial'],
        "Saldo Actual": cred['saldo_actual'],
        "Cuota Mensual": cred['cuota_actual'],
        "Tasa Mensual (%)": cred['tasa_mensual'],
        "Próximo Vencimiento": cred['fecha_proximo_vencimiento']
    }])
    
    if cred['historial']:
        df_historial = pd.DataFrame(cred['historial'])
    else:
        df_historial = pd.DataFrame({"Aviso": ["No hay pagos registrados aún"]})
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_resumen.to_excel(writer, index=False, sheet_name='Resumen')
        df_historial.to_excel(writer, index=False, sheet_name='Pagos')
    
    return output.getvalue()

# -----------------------------------------
# INICIALIZAR MEMORIA
# -----------------------------------------
if 'creditos' not in st.session_state:
    st.session_state.creditos = {}
if 'mensaje_reciente' not in st.session_state:
    st.session_state.mensaje_reciente = None
if 'credito_actual_id' not in st.session_state:
    st.session_state.credito_actual_id = None

# -----------------------------------------
# BARRA LATERAL
# -----------------------------------------
st.sidebar.title("Navegación 🧭")
menu = st.sidebar.radio("¿Qué deseas hacer hoy?", 
                        ["📝 1. Crear o Cargar Préstamos", 
                         "💼 2. Cobrar / Gestionar Préstamos",
                         "📄 3. Estados de Cuenta (PDF/Excel)"])

st.sidebar.markdown("---")
st.sidebar.markdown("<p class='big-font'>💾 Guardar mis cambios</p>", unsafe_allow_html=True)

json_data = json.dumps(st.session_state.creditos, indent=4)
st.sidebar.download_button(
    label="⬇️ GUARDAR / DESCARGAR ARCHIVO JSON",
    data=json_data,
    file_name="mis_prestamos.json",
    mime="application/json"
)

# -----------------------------------------
# MÓDULO 1: CREAR O CARGAR
# -----------------------------------------
if menu == "📝 1. Crear o Cargar Préstamos":
    st.title("📝 Registro de Préstamos")
    
    st.markdown("### 📂 Paso 1: Cargar mi archivo guardado")
    archivo_subido = st.file_uploader("Sube tu archivo de préstamos aquí:", type=['json'])
    
    if archivo_subido is not None:
        if st.button("📥 Leer archivo subido"):
            st.session_state.creditos = json.load(archivo_subido)
            st.success("¡Libreta cargada! Ya puedes navegar por el menú lateral.")
            
    st.markdown("---")
    st.markdown("### ➕ Paso 2: Registrar un préstamo")
    
    with st.form("nuevo_prestamo"):
        nombre = st.text_input("👤 Nombre de la persona:")
        descripcion = st.text_input("📝 Descripción (Ej: Préstamo para remodelación):")
        monto = st.number_input("💵 Monto ORIGINAL prestado ($):", min_value=0.0, step=50000.0)
        tasa = st.number_input("📈 Interés mensual (%):", min_value=0.0, step=0.5, value=1.0)
        plazo = st.number_input("📅 Plazo TOTAL acordado (en meses):", min_value=1, step=1, value=12)
        
        st.markdown("---")
        st.markdown("#### 🔄 Si el préstamo ya está en curso, llena esto:")
        cuotas_pagadas = st.number_input("✅ ¿Cuántas cuotas ya te ha pagado? (Deja en 0 si es un préstamo nuevo):", min_value=0, step=1, value=0)
        fecha_referencia = st.date_input("🗓️ Fecha del desembolso (o del ÚLTIMO pago si ya está en curso):", datetime.today())
        
        crear = st.form_submit_button("✅ Guardar Préstamo")
        
        if crear:
            if not nombre:
                st.error("El Nombre es obligatorio.")
            elif monto <= 0:
                st.error("El monto debe ser mayor a cero.")
            elif cuotas_pagadas >= plazo:
                st.error("Las cuotas pagadas deben ser menores al plazo total.")
            else:
                cuota_fija = calcular_cuota(monto, tasa, plazo)
                meses_restantes = plazo - cuotas_pagadas
                
                if cuotas_pagadas == 0:
                    saldo_actual = monto
                else:
                    saldo_actual = calcular_saldo_restante(cuota_fija, tasa, meses_restantes)
                
                id_credito = f"{nombre}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                fecha_vencimiento = fecha_referencia + timedelta(days=30)
                
                st.session_state.creditos[id_credito] = {
                    "nombre": nombre,
                    "descripcion": descripcion,
                    "monto_inicial": monto,
                    "saldo_actual": saldo_actual,
                    "tasa_mensual": tasa,
                    "cuota_actual": cuota_fija,
                    "meses_restantes": float(meses_restantes),
                    "fecha_ultimo_pago": str(fecha_referencia),
                    "fecha_proximo_vencimiento": str(fecha_vencimiento),
                    "historial": []
                }
                
                if cuotas_pagadas == 0:
                    st.success(f"¡Préstamo NUEVO guardado! Cuota mensual: ${cuota_fija:,.0f}")
                else:
                    st.success(f"¡Préstamo EN CURSO guardado!")
                    st.info(f"Saldo actual calculado: **${saldo_actual:,.0f}**, restando **{meses_restantes} cuotas** de **${cuota_fija:,.0f}**.")

# -----------------------------------------
# MÓDULO 2: GESTIONAR
# -----------------------------------------
elif menu == "💼 2. Cobrar / Gestionar Préstamos":
    st.title("💼 Gestión y Cobro")
    
    if not st.session_state.creditos:
        st.warning("No tienes préstamos registrados.")
    else:
        if st.session_state.mensaje_reciente:
            st.markdown(f"<div class='ahorro-box'>{st.session_state.mensaje_reciente}</div>", unsafe_allow_html=True)
            if st.button("✖️ Cerrar mensaje"):
                st.session_state.mensaje_reciente = None
                st.rerun()

        activos = {k: v for k, v in st.session_state.creditos.items() if v['saldo_actual'] > 0}
        
        if not activos:
            st.success("¡Excelente! Todos los préstamos están pagados.")
        else:
            opciones = [f"👤 {v['nombre']} - {v['descripcion']} (Saldo: ${v['saldo_actual']:,.0f})" for k, v in activos.items()]
            id_keys = list(activos.keys())
            
            # Recordar el crédito que estaba seleccionado antes del pago
            indice_por_defecto = 0
            if st.session_state.credito_actual_id in id_keys:
                indice_por_defecto = id_keys.index(st.session_state.credito_actual_id)
            
            seleccion = st.selectbox("👇 Selecciona el crédito a pagar:", opciones, index=indice_por_defecto)
            idx = opciones.index(seleccion)
            id_credito = id_keys[idx]
            
            # Guardar el ID seleccionado actual en la memoria de la sesión
            st.session_state.credito_actual_id = id_credito
            cred = st.session_state.creditos[id_credito]
            
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            col1.info(f"**💰 Saldo Actual:**\n\n${cred['saldo_actual']:,.0f}")
            col2.warning(f"**🏷️ Cuota Fija:**\n\n${cred['cuota_actual']:,.0f}")
            col3.error(f"**⏳ Faltan:**\n\n{math.ceil(cred['meses_restantes'])} cuotas")
            
            st.markdown(f"<div class='info-box'>🗓️ <b>Próximo Vencimiento Esperado:</b> {cred['fecha_proximo_vencimiento']}</div>", unsafe_allow_html=True)
            
            fecha_hoy = datetime.today().date()
            ultimo_pago = parse_date(cred['fecha_ultimo_pago'])
            dias_transcurridos = max((fecha_hoy - ultimo_pago).days, 0)
            interes_causado = calcular_interes_diario(cred['saldo_actual'], cred['tasa_mensual'], dias_transcurridos)
            
            st.markdown("### ✍️ Registrar un Pago")
            st.write(f"Han pasado **{dias_transcurridos} días** desde el último pago o registro.")
            st.write(f"Intereses generados a hoy: **${interes_causado:,.0f}**")
            
            tipo_pago = st.radio("¿Qué tipo de abono van a realizar?", 
                                 ["✅ Pago normal de la cuota mensual", 
                                  "🔥 Abono EXTRA (Reducir tiempo del crédito)", 
                                  "🔽 Abono EXTRA (Bajar el valor de la cuota)"])
            
            with st.form("form_pago"):
                monto_pago = st.number_input("Dinero que te entregan hoy ($):", min_value=0.0, value=float(cred['cuota_actual']), step=10000.0)
                btn_pagar = st.form_submit_button("💰 Registrar Pago y Actualizar")
                
                if btn_pagar:
                    if monto_pago < interes_causado:
                        st.error(f"El pago no cubre los intereses diarios. Debe ser mínimo de ${interes_causado:,.0f}")
                    else:
                        abono_capital = monto_pago - interes_causado
                        saldo_anterior = cred['saldo_actual']
                        meses_anteriores = cred['meses_restantes']
                        cuota_anterior = cred['cuota_actual']
                        
                        cred['saldo_actual'] -= abono_capital
                        if cred['saldo_actual'] < 0: cred['saldo_actual'] = 0
                        
                        ahorro_intereses = 0
                        meses_ahorrados = 0
                        
                        if "Pago normal" in tipo_pago:
                            cred['meses_restantes'] -= 1
                            vencimiento_actual = parse_date(cred['fecha_proximo_vencimiento'])
                            cred['fecha_proximo_vencimiento'] = str(vencimiento_actual + timedelta(days=30))
                            
                        elif "tiempo" in tipo_pago:
                            cred['meses_restantes'] = calcular_meses(cred['saldo_actual'], cred['tasa_mensual'], cred['cuota_actual'])
                            intereses_futuros_viejos = (cuota_anterior * meses_anteriores) - saldo_anterior
                            intereses_futuros_nuevos = (cred['cuota_actual'] * cred['meses_restantes']) - cred['saldo_actual']
                            ahorro_intereses = max(0, intereses_futuros_viejos - intereses_futuros_nuevos)
                            meses_ahorrados = max(0, meses_anteriores - cred['meses_restantes'])
                            
                        elif "Bajar" in tipo_pago:
                            if cred['meses_restantes'] > 0:
                                cred['cuota_actual'] = calcular_cuota(cred['saldo_actual'], cred['tasa_mensual'], cred['meses_restantes'])
                        
                        cred['fecha_ultimo_pago'] = str(fecha_hoy)
                        
                        cred['historial'].append({
                            "Fecha": str(fecha_hoy),
                            "Días Pagados": dias_transcurridos,
                            "Interés Cubierto": f"${interes_causado:,.0f}",
                            "Abono a Capital": f"${abono_capital:,.0f}",
                            "Nuevo Saldo": f"${cred['saldo_actual']:,.0f}"
                        })
                        
                        msg = f"<b>¡Pago Registrado Exitosamente!</b><br>"
                        msg += f"Aplicaste ${interes_causado:,.0f} a intereses y ${abono_capital:,.0f} directo al capital.<br>"
                        if ahorro_intereses > 0:
                            msg += f"<br>🎉 <b>¡Súper Abono!</b> Al aplicar esto a reducción de tiempo, el deudor se ahorró aprox. <b>${ahorro_intereses:,.0f}</b> en intereses futuros y se redujo la deuda en <b>{math.ceil(meses_ahorrados)} cuotas</b>."
                            
                        st.session_state.creditos[id_credito] = cred
                        st.session_state.mensaje_reciente = msg
                        st.rerun()
            
            if cred['historial']:
                st.markdown("### 📜 Detalle de Pagos Realizados")
                df = pd.DataFrame(cred['historial'])
                st.dataframe(df, use_container_width=True, hide_index=True)

# -----------------------------------------
# MÓDULO 3: ESTADOS DE CUENTA
# -----------------------------------------
elif menu == "📄 3. Estados de Cuenta (PDF/Excel)":
    st.title("📄 Emitir Estado de Cuenta")
    
    if not st.session_state.creditos:
        st.warning("No tienes préstamos registrados para generar estados de cuenta.")
    else:
        opciones = [f"👤 {v['nombre']} - {v['descripcion']}" for k, v in st.session_state.creditos.items()]
        id_keys = list(st.session_state.creditos.keys())
        
        seleccion = st.selectbox("👇 Selecciona el cliente para generar su estado de cuenta:", opciones)
        idx = opciones.index(seleccion)
        id_credito = id_keys[idx]
        cred = st.session_state.creditos[id_credito]
        
        st.markdown(f"### Generando reporte para: **{cred['nombre']}**")
        st.info("Haz clic en cualquiera de los botones inferiores para descargar el documento y enviarlo por WhatsApp o correo.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            pdf_bytes = generar_pdf(cred)
            st.download_button(
                label="📄 Descargar en PDF",
                data=pdf_bytes,
                file_name=f"Estado_Cuenta_{cred['nombre']}.pdf",
                mime="application/pdf"
            )
            
        with col2:
            excel_bytes = generar_excel(cred)
            st.download_button(
                label="📊 Descargar en Excel",
                data=excel_bytes,
                file_name=f"Estado_Cuenta_{cred['nombre']}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
