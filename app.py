import streamlit as st
import json
import math
from datetime import datetime, timedelta, date
import pandas as pd

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
    # Calcula el saldo actual basado en las cuotas que faltan (Valor Presente)
    if tasa_mensual <= 0: return cuota * meses_restantes
    r = tasa_mensual / 100
    return cuota * (1 - (1 + r)**-meses_restantes) / r

def parse_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").date()

def calcular_interes_diario(saldo, tasa_mensual, dias):
    tasa_diaria = (tasa_mensual / 100) / 30
    return saldo * tasa_diaria * dias

# -----------------------------------------
# INICIALIZAR MEMORIA
# -----------------------------------------
if 'creditos' not in st.session_state:
    st.session_state.creditos = {}
if 'mensaje_reciente' not in st.session_state:
    st.session_state.mensaje_reciente = None

# -----------------------------------------
# BARRA LATERAL
# -----------------------------------------
st.sidebar.title("Navegación 🧭")
menu = st.sidebar.radio("¿Qué deseas hacer hoy?", 
                        ["📝 1. Crear o Cargar Préstamos", 
                         "💼 2. Cobrar / Gestionar Préstamos"])

st.sidebar.markdown("---")
st.sidebar.markdown("<p class='big-font'>💾 Guardar mis cambios</p>", unsafe_allow_html=True)

json_data = json.dumps(st.session_state.creditos, indent=4)
st.sidebar.download_button(
    label="⬇️ GUARDAR / DESCARGAR",
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
            st.success("¡Libreta cargada! Ya puedes ir a 'Gestionar Préstamos'.")
            
    st.markdown("---")
    st.markdown("### ➕ Paso 2: Registrar un préstamo")
    
    with st.form("nuevo_prestamo"):
        col1, col2 = st.columns(2)
        cedula = col1.text_input("💳 Cédula del deudor:")
        nombre = col2.text_input("👤 Nombre de la persona:")
        
        descripcion = st.text_input("📝 Descripción (Ej: Préstamo para remodelación):")
        
        monto = st.number_input("💵 Monto ORIGINAL prestado ($):", min_value=0.0, step=50000.0)
        tasa = st.number_input("📈 Interés mensual (%):", min_value=0.0, step=0.5, value=1.0)
        plazo = st.number_input("📅 Plazo TOTAL acordado (en meses):", min_value=1, step=1, value=12)
        
        st.markdown("---")
        st.markdown("#### 🔄 Si el préstamo ya está en curso, llena esto:")
        cuotas_pagadas = st.number_input("✅ ¿Cuántas cuotas ya te ha pagado? (Deja en 0 si es un préstamo nuevo):", min_value=0, step=1, value=0)
        fecha_referencia = st.date_input("🗓️ Fecha del desembolso (si es nuevo) o del ÚLTIMO pago (si ya está en curso):", datetime.today())
        
        crear = st.form_submit_button("✅ Guardar Préstamo")
        
        if crear:
            if not cedula or not nombre:
                st.error("Cédula y Nombre son obligatorios.")
            elif monto <= 0:
                st.error("El monto debe ser mayor a cero.")
            elif cuotas_pagadas >= plazo:
                st.error("Las cuotas pagadas deben ser menores al plazo total.")
            else:
                # 1. Calcular cuota original fija
                cuota_fija = calcular_cuota(monto, tasa, plazo)
                meses_restantes = plazo - cuotas_pagadas
                
                # 2. Calcular saldo actual basado en si ya pagó cuotas
                if cuotas_pagadas == 0:
                    saldo_actual = monto
                else:
                    saldo_actual = calcular_saldo_restante(cuota_fija, tasa, meses_restantes)
                
                id_credito = f"{cedula}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                fecha_vencimiento = fecha_referencia + timedelta(days=30)
                
                st.session_state.creditos[id_credito] = {
                    "cedula": cedula,
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
                    st.info(f"El sistema calculó que el saldo actual exacto es de **${saldo_actual:,.0f}**, restando **{meses_restantes} cuotas** de **${cuota_fija:,.0f}**.")

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
            opciones = [f"[{v['cedula']}] {v['nombre']} - {v['descripcion']} (Saldo: ${v['saldo_actual']:,.0f})" for k, v in activos.items()]
            id_keys = list(activos.keys())
            
            seleccion = st.selectbox("👇 Selecciona el crédito a pagar:", opciones)
            idx = opciones.index(seleccion)
            id_credito = id_keys[idx]
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
