import streamlit as st
import json
import math
from datetime import datetime
import pandas as pd

# -----------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# -----------------------------------------
st.set_page_config(page_title="Gestor de Préstamos", page_icon="💰", layout="centered")

# Estilo para hacer botones y textos más grandes (Amigable para persona mayor)
st.markdown("""
    <style>
    .big-font { font-size:20px !important; font-weight: bold; }
    .stButton>button { width: 100%; height: 60px; font-size: 20px; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# -----------------------------------------
# FUNCIONES MATEMÁTICAS DEL CRÉDITO
# -----------------------------------------
def calcular_cuota(capital, tasa_mensual, meses):
    if tasa_mensual == 0:
        return capital / meses
    r = tasa_mensual / 100
    return capital * (r * (1 + r)**meses) / ((1 + r)**meses - 1)

def calcular_meses(capital, tasa_mensual, cuota):
    if tasa_mensual == 0:
        return capital / cuota
    r = tasa_mensual / 100
    if cuota <= r * capital:
        return 999 # Plazo infinito si la cuota no cubre ni los intereses
    return -math.log(1 - (r * capital) / cuota) / math.log(1 + r)

# -----------------------------------------
# INICIALIZAR MEMORIA (SESSION STATE)
# -----------------------------------------
if 'creditos' not in st.session_state:
    st.session_state.creditos = {}

# -----------------------------------------
# BARRA LATERAL: MENÚ Y GUARDADO
# -----------------------------------------
st.sidebar.title("Navegación 🧭")
menu = st.sidebar.radio("¿Qué deseas hacer hoy?", 
                        ["📝 1. Crear o Cargar Préstamos", 
                         "💼 2. Cobrar / Gestionar Préstamos"])

st.sidebar.markdown("---")
st.sidebar.markdown("<p class='big-font'>💾 Guardar mis cambios</p>", unsafe_allow_html=True)
st.sidebar.info("Cuando termines de anotar los pagos, haz clic abajo para guardar. **Recuerda reemplazar el archivo anterior.**")

# Botón de descarga del estado actual
json_data = json.dumps(st.session_state.creditos, indent=4)
st.sidebar.download_button(
    label="⬇️ GUARDAR Y DESCARGAR ARCHIVO",
    data=json_data,
    file_name="mis_prestamos.json",
    mime="application/json"
)

# -----------------------------------------
# MÓDULO 1: CREAR O CARGAR
# -----------------------------------------
if menu == "📝 1. Crear o Cargar Préstamos":
    st.title("📝 Registro de Préstamos")
    
    st.markdown("### 📂 Paso 1: Cargar mi libreta de préstamos")
    archivo_subido = st.file_uploader("Si ya tienes un archivo guardado, súbelo aquí:", type=['json'])
    
    if archivo_subido is not None:
        if st.button("📥 Leer archivo subido"):
            st.session_state.creditos = json.load(archivo_subido)
            st.success("¡Libreta cargada con éxito! Ya puedes ir a 'Gestionar Préstamos'.")
            
    st.markdown("---")
    st.markdown("### ➕ Paso 2: Registrar un préstamo NUEVO")
    
    with st.form("nuevo_prestamo"):
        nombre = st.text_input("👤 Nombre de la persona a la que le prestas:")
        monto = st.number_input("💵 ¿Cuánto dinero le vas a prestar? ($)", min_value=0.0, step=50000.0)
        tasa = st.number_input("📈 Interés mensual (%):", min_value=0.0, step=0.5, value=1.0)
        plazo = st.number_input("📅 ¿En cuántos meses te va a pagar?:", min_value=1, step=1, value=12)
        
        crear = st.form_submit_button("✅ Guardar Nuevo Préstamo")
        
        if crear:
            if nombre.strip() == "":
                st.error("Por favor, escribe el nombre de la persona.")
            elif monto <= 0:
                st.error("El monto debe ser mayor a cero.")
            else:
                cuota_inicial = calcular_cuota(monto, tasa, plazo)
                id_credito = f"{nombre}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                st.session_state.creditos[id_credito] = {
                    "nombre": nombre,
                    "monto_inicial": monto,
                    "saldo_actual": monto,
                    "tasa_mensual": tasa,
                    "cuota_actual": cuota_inicial,
                    "meses_restantes": plazo,
                    "historial": []
                }
                st.success(f"¡Préstamo de {nombre} creado! La cuota mensual será de aprox. ${cuota_inicial:,.0f}")

# -----------------------------------------
# MÓDULO 2: GESTIONAR
# -----------------------------------------
elif menu == "💼 2. Cobrar / Gestionar Préstamos":
    st.title("💼 Gestión y Cobro")
    
    if not st.session_state.creditos:
        st.warning("No tienes préstamos registrados. Ve a la primera pestaña para crear uno o cargar tu archivo.")
    else:
        # Lista de préstamos activos (Saldo > 0)
        opciones = [f"{v['nombre']} (Saldo: ${v['saldo_actual']:,.0f})" for k, v in st.session_state.creditos.items() if v['saldo_actual'] > 0]
        id_keys = [k for k, v in st.session_state.creditos.items() if v['saldo_actual'] > 0]
        
        if not opciones:
            st.success("¡Excelente! Todos los préstamos están pagados en su totalidad.")
        else:
            seleccion = st.selectbox("👇 Selecciona a la persona que va a pagar hoy:", opciones)
            idx = opciones.index(seleccion)
            id_credito = id_keys[idx]
            cred = st.session_state.creditos[id_credito]
            
            st.markdown("---")
            # Tarjeta de información actual
            col1, col2, col3 = st.columns(3)
            col1.info(f"**Deuda Actual:**\n\n${cred['saldo_actual']:,.0f}")
            col2.warning(f"**Cuota a Pagar:**\n\n${cred['cuota_actual']:,.0f}")
            col3.error(f"**Meses faltantes:**\n\n{math.ceil(cred['meses_restantes'])} meses")
            
            st.markdown("### ✍️ Registrar un Pago")
            
            tipo_pago = st.radio("¿Qué tipo de pago te están haciendo?", 
                                 ["✅ Pago normal de la cuota mensual", 
                                  "🔥 Abono EXTRA para terminar en menos tiempo", 
                                  "🔽 Abono EXTRA para que la cuota quede más barata"])
            
            with st.form("form_pago"):
                monto_pago = st.number_input("Monto que te está entregando hoy ($):", min_value=0.0, value=float(cred['cuota_actual']), step=10000.0)
                fecha_pago = st.date_input("Fecha del pago:", datetime.today())
                btn_pagar = st.form_submit_button("💰 Registrar Pago y Actualizar Cuenta")
                
                if btn_pagar:
                    if monto_pago <= 0:
                        st.error("El monto debe ser mayor a cero.")
                    else:
                        interes_del_mes = cred['saldo_actual'] * (cred['tasa_mensual'] / 100)
                        
                        if "Pago normal" in tipo_pago:
                            abono_capital = monto_pago - interes_del_mes
                            if abono_capital < 0:
                                st.error("El pago no alcanza ni para cubrir los intereses.")
                            else:
                                cred['saldo_actual'] -= abono_capital
                                cred['meses_restantes'] -= 1
                                
                        elif "menos tiempo" in tipo_pago:
                            # Se abona todo al capital (asumiendo que ya pagó los intereses o los cubrirá)
                            cred['saldo_actual'] -= monto_pago
                            # Se recalculan los meses faltantes, manteniendo la cuota
                            cred['meses_restantes'] = calcular_meses(cred['saldo_actual'], cred['tasa_mensual'], cred['cuota_actual'])
                            
                        elif "más barata" in tipo_pago:
                            cred['saldo_actual'] -= monto_pago
                            # Se recalcula la cuota, manteniendo los meses restantes
                            if cred['meses_restantes'] > 0:
                                cred['cuota_actual'] = calcular_cuota(cred['saldo_actual'], cred['tasa_mensual'], cred['meses_restantes'])
                        
                        # Evitar saldos negativos
                        if cred['saldo_actual'] < 0:
                            cred['saldo_actual'] = 0
                            cred['meses_restantes'] = 0
                            cred['cuota_actual'] = 0
                            
                        # Guardar en historial
                        cred['historial'].append({
                            "fecha": str(fecha_pago),
                            "tipo": tipo_pago.split()[1], # Normal o EXTRA
                            "monto_pagado": monto_pago,
                            "nuevo_saldo": cred['saldo_actual']
                        })
                        
                        st.session_state.creditos[id_credito] = cred
                        st.success("¡Pago registrado! Revisa arriba los nuevos valores.")
                        st.balloons()
            
            # Mostrar historial
            if cred['historial']:
                st.markdown("### 📜 Historial de pagos de esta persona")
                df = pd.DataFrame(cred['historial'])
                # Formatear el DataFrame para que sea más legible
                df.columns = ["Fecha", "Tipo de Pago", "Monto Entregado", "Saldo Restante"]
                df["Monto Entregado"] = df["Monto Entregado"].apply(lambda x: f"${x:,.0f}")
                df["Saldo Restante"] = df["Saldo Restante"].apply(lambda x: f"${x:,.0f}")
                st.dataframe(df, use_container_width=True)

