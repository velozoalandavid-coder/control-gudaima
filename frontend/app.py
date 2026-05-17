import streamlit as st
import requests
import pandas as pd
import os
import re

API_URL = os.getenv("API_URL", "http://backend:8000")

st.set_page_config(
    page_title="GUDAIMA | Control de Stock",
    page_icon="https://gudaima.com.ar/wp-content/uploads/2025/05/cropped-logo-32x32.png",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: #f6f4f1;
}

section[data-testid="stSidebar"] {
    background: #10131f;
}

section[data-testid="stSidebar"] * {
    color: white !important;
}

h1, h2, h3 {
    color: #1c1c1c !important;
    font-weight: 800 !important;
}

.stButton > button {
    background: #d4145a !important;
    color: white !important;
    border-radius: 12px !important;
    border: none !important;
    padding: 10px 22px !important;
    font-weight: 700 !important;
}

.stTextInput input,
.stTextArea textarea,
.stNumberInput input {
    background: white !important;
    color: #111 !important;
    border: 1px solid #d8d8d8 !important;
    border-radius: 10px !important;
}

div[data-baseweb="select"] > div {
    background: white !important;
    color: #111 !important;
    border: 1px solid #d8d8d8 !important;
    border-radius: 10px !important;
}

label, p, span, div {
    color: #111;
}
</style>
""", unsafe_allow_html=True)
logo_ruta = "static/logo.png"
if os.path.exists(logo_ruta):
    st.sidebar.image(logo_ruta, width=220)
    st.sidebar.markdown("<div style='text-align: center; font-size: 0.9rem; font-weight: 500; letter-spacing: 1.5px; color: #e91e63; margin-top: 2px; margin-bottom: 15px; text-transform: uppercase;'>MAYORISTA</div>", unsafe_allow_html=True)
else:
    st.sidebar.title("GUDAIMA")
    st.sidebar.markdown("### MAYORISTA")
st.sidebar.markdown("---")

st.title("Control de Stock Textil")

def fetch_json(endpoint):
    try:
        r = requests.get(f"{API_URL}{endpoint}")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error conectando a la API: {e}")
        return None

def post_json(endpoint, data):
    try:
        r = requests.post(f"{API_URL}{endpoint}", json=data)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        st.error(f"Error: {e.response.json().get('detail', str(e))}")
        return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None

menu = st.sidebar.radio("Navegación", 
    ["📦 Stock Actual", "➕ Agregar Rollo", "✂️ Registrar Corte", 
     "📋 Ver Rollos", "📋 Ver Cortes", "➕ Agregar Tela", "🗑️ Eliminar Tela"])

if menu == "📦 Stock Actual":
    st.subheader("📦 Stock Actual de Telas")

    # acceso admin
    admin = st.sidebar.checkbox("🔒 Modo Admin")
    autorizado=False

    if admin:
        clave = st.sidebar.text_input(
            "Contraseña",
            type="password"
        )
        if clave == "Alan2026":
            autorizado=True
            st.sidebar.success("Modo admin activo")

    stock = fetch_json("/stock")

    if stock:
        df = pd.DataFrame(stock)

        # limpiar NaN
        df=df.fillna("-")

        # buscador
        buscar = st.text_input(
            "🔎 Buscar tela, color o código"
        )

        if buscar:
            buscar=buscar.lower()

            df=df[
                df.astype(str)
                .apply(
                    lambda x:
                    x.str.lower()
                    .str.contains(buscar)
                )
                .any(axis=1)
            ]

        # semáforo lindo
        estado_color={
            "OK":"🟢 OK",
            "COMPRAR":"🟡 COMPRAR",
            "SIN STOCK":"🔴 SIN STOCK"
        }

        df["estado"]=df["estado"].replace(
            estado_color
        )

        # ocultar precios
        if not autorizado:
            df=df.drop(
                columns=[
                    "precio_kg",
                    "valor_stock"
                ],
                errors="ignore"
            )

        st.dataframe(
            df,
            use_container_width=True
        )

        col1,col2,col3=st.columns(3)

        col1.metric(
            "KG Totales",
            f"{df['stock_actual_kg'].sum():.1f}"
        )

        col2.metric(
            "Comprar",
            (df["estado"]
            .str.contains("COMPRAR"))
            .sum()
        )

        col3.metric(
            "Sin stock",
            (df["estado"]
            .str.contains("SIN"))
            .sum()
        )

        if autorizado:
            st.metric(
                "💰 Valor total",
                f"${stock and pd.DataFrame(stock)['valor_stock'].sum():,.0f}"
            )

elif menu == "➕ Agregar Rollo":
    st.subheader("Agregar Rollos (ingresá los pesos de cada rollo)")

    # Mostrar mensaje de éxito diferido (si existe)
    if "mensaje_rollo" in st.session_state and st.session_state.mensaje_rollo:
        st.success(st.session_state.mensaje_rollo)
        st.balloons()
        # Limpiar el mensaje para que no se repita
        st.session_state.mensaje_rollo = ""

    telas = fetch_json("/telas")
    if telas:
        opciones = [f"{t['codigo_tela']} - {t['tipo']} - {t['color']}" for t in telas]
        if opciones:
            seleccion = st.selectbox("Seleccionar Tela", opciones)
            if seleccion:
                partes = seleccion.split(' - ')
                codigo = float(partes[0])
                tipo = partes[1]
                color = partes[2]

            # Contador para renovar campos
            if "rollo_key" not in st.session_state:
                st.session_state.rollo_key = 0

            key_suf = st.session_state.rollo_key

            pesos_str = st.text_area(
                "Pesos de los rollos (separados por comas o uno por línea)",
                placeholder="22.5, 20.8, 22.7, 20",
                key=f"pesos_agregar_{key_suf}"
            )
            obs = st.text_input("Observación (opcional)", key=f"obs_agregar_{key_suf}")

            if st.button("Agregar Rollos"):
                pesos = re.split(r'[,\n]+', pesos_str)
                limpios = []
                for p in pesos:
                    p = p.strip()
                    if p:
                        try:
                            kg = float(p)
                            if kg <= 0:
                                st.error(f"Peso inválido: {p}")
                                st.stop()
                            limpios.append(kg)
                        except ValueError:
                            st.error(f"'{p}' no es un número válido.")
                            st.stop()
                if not limpios:
                    st.error("Debe ingresar al menos un peso.")
                else:
                    resp = post_json("/rollos/lote", {
                        "codigo_tela": codigo,
                        "tipo": tipo,
                        "color": color,
                        "pesos": limpios,
                        "observacion": obs if obs else None
                    })
                    if resp:
                        # Incrementar clave para que los campos se vacíen
                        st.session_state.rollo_key += 1
                        # Guardar mensaje de éxito para la próxima ejecución
                        st.session_state.mensaje_rollo = f"✅ ¡Agregados {resp['cantidad']} rollos correctamente! IDs: {resp['ids']}"
                        st.rerun()
        else:
            st.warning("No hay telas en el catálogo. Agregue una usando 'Agregar Tela'.")
elif menu == "✂️ Registrar Corte":
    st.subheader("Registrar Corte – Detalle por Rollo")
    telas = fetch_json("/telas")
    if telas:
        tipos_unicos = list(set([f"{t['codigo_tela']} - {t['tipo']}" for t in telas]))
        if tipos_unicos:
            tipo_seleccionado = st.selectbox("Seleccionar Artículo", tipos_unicos)
            codigo_str, tipo = tipo_seleccionado.split(' - ')
            codigo = float(codigo_str)
            colores_disponibles = [t['color'] for t in telas if t['codigo_tela'] == codigo and t['tipo'] == tipo]
            if not colores_disponibles:
                st.warning("No hay colores cargados para este artículo.")
                st.stop()

            if "rollos_corte" not in st.session_state:
                st.session_state.rollos_corte = [{"color": colores_disponibles[0], "kg": 0.0}]

            st.markdown("**Agregue los rollos con su color y kilos:**")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➕ Agregar rollo"):
                    st.session_state.rollos_corte.append({"color": colores_disponibles[0], "kg": 0.0})
                    st.rerun()
            with col2:
                if st.button("🧹 Limpiar todo"):
                    st.session_state.rollos_corte = [{"color": colores_disponibles[0], "kg": 0.0}]
                    st.rerun()

            for i, rollo in enumerate(st.session_state.rollos_corte):
                cols = st.columns([2, 1])
                with cols[0]:
                    color_actual = rollo["color"]
                    if color_actual not in colores_disponibles:
                        color_actual = colores_disponibles[0]
                    color_idx = colores_disponibles.index(color_actual)
                    nuevo_color = st.selectbox(f"Color rollo {i+1}", colores_disponibles, index=color_idx, key=f"color_{i}")
                with cols[1]:
                    nuevo_kg = st.number_input(f"Kg rollo {i+1}", min_value=0.0, step=0.1, value=rollo["kg"], key=f"kg_{i}")
                st.session_state.rollos_corte[i]["color"] = nuevo_color
                st.session_state.rollos_corte[i]["kg"] = nuevo_kg

            pesos_validos = [r["kg"] for r in st.session_state.rollos_corte if r["kg"] > 0]
            total_kg = sum(pesos_validos)
            total_rollos = len(pesos_validos)

            if total_rollos > 0:
                st.write(f"**Total kg usados:** {total_kg:.2f} | **Rollos utilizados:** {total_rollos}")

            obs = st.text_input("Observación")
            if st.button("Registrar Corte"):
                if total_kg <= 0:
                    st.error("Debe ingresar al menos un rollo con kg mayor a 0.")
                else:
                    detalles = []
                    for r in st.session_state.rollos_corte:
                        if r["kg"] > 0:
                            detalles.append({
                                "codigo_tela": codigo,
                                "tipo": tipo,
                                "color": r["color"],
                                "kg_usados": r["kg"],
                                "rollos_usados": 1
                            })
                    resp = post_json("/cortes/lote", {
                        "detalles": detalles,
                        "observacion": obs
                    })
                    if resp:
                        st.success(f"{resp['mensaje']} (IDs: {resp['numeros_corte']})")
                        st.session_state.rollos_corte = [{"color": colores_disponibles[0], "kg": 0.0}]
                        st.rerun()
        else:
            st.warning("No hay telas en el catálogo.")
    else:
        st.warning("No hay telas en el catálogo.")

elif menu == "📋 Ver Rollos":
    st.subheader("Listado de Rollos")
    rollos = fetch_json("/rollos")
    if rollos:
        df = pd.DataFrame(rollos)
        st.dataframe(df, use_container_width=True)
        
        st.subheader("Eliminar un rollo por ID")
        id_a_eliminar = st.number_input("ID del rollo a eliminar", min_value=1, step=1)
        if st.button("🗑️ Eliminar Rollo"):
            try:
                r = requests.delete(f"{API_URL}/rollos/{int(id_a_eliminar)}")
                if r.status_code == 200:
                    st.success(r.json()["mensaje"])
                    st.rerun()
                else:
                    st.error(r.json().get("detail", "Error al eliminar"))
            except Exception as e:
                st.error(f"Error: {e}")
elif menu == "📋 Ver Cortes":

    st.subheader("✂️ Historial de Cortes")

    cortes = fetch_json("/cortes")

    if cortes:

        buscar = st.text_input(
            "🔎 Buscar corte, tela o color"
        )

        df = pd.DataFrame(cortes)

        df = df.fillna("-")

        if buscar:
            buscar = buscar.lower()

            df = df[
                df.astype(str)
                .apply(
                    lambda x:
                    x.str.lower()
                    .str.contains(buscar)
                )
                .any(axis=1)
            ]
        grupos = df.groupby("observacion")

        for observacion, grupo in grupos:

            try:
                fecha_linda = pd.to_datetime(
                    grupo.iloc[0]["fecha"]
                ).strftime("%d/%m/%Y %H:%M")
            except:
                fecha_linda = grupo.iloc[0]["fecha"]

            total_kg = grupo["kg_usados"].sum()
            total_rollos = grupo["rollos_usados"].sum()

            filas_html = ""

            for _, fila in grupo.iterrows():
                filas_html += f"""
<p>
🎨 <b>Color:</b> {fila['color']}
&nbsp;&nbsp; ⚖️ <b>KG:</b> {fila['kg_usados']}
&nbsp;&nbsp; 📦 <b>Rollos:</b> {fila['rollos_usados']}
</p>
"""

            st.markdown(f"""
<div style="
background:#ffffff;
color:#111111;
padding:22px;
border-radius:18px;
margin-bottom:18px;
box-shadow:0 4px 18px rgba(0,0,0,0.08);
border-left:7px solid #e91e63;
font-size:18px;
line-height:1.8;
">

<h3 style="font-size:30px;font-weight:800;">
✂️ {observacion}
</h3>

<p><b>📅 Fecha:</b> {fecha_linda}</p>
<p><b>🧵 Tela:</b> {grupo.iloc[0]['tipo']}</p>

<hr>

{filas_html}

<hr>

<p><b>⚖️ Total KG:</b> {total_kg}</p>
<p><b>📦 Total rollos:</b> {total_rollos}</p>

</div>
""", unsafe_allow_html=True)

        st.subheader(
            "🗑️ Eliminar Corte"
        )

        nro=st.number_input(
            "Número",
            min_value=1,
            step=1
        )

        if st.button(
            "Eliminar Corte"
        ):

            r=requests.delete(
                f"{API_URL}/cortes/{int(nro)}"
            )

            if r.status_code==200:
                st.success("Eliminado")
                st.rerun()


elif menu == "➕ Agregar Tela":
    st.subheader("Agregar Nueva Tela al Catálogo")
    with st.form("form_tela"):
        col1, col2 = st.columns(2)
        with col1:
            codigo = st.number_input("Código de Tela", min_value=0.0, step=1.0, value=3.0)
            tipo = st.text_input("Tipo de Tela (artículo)", placeholder="Ej: DARLON POLAR")
            color = st.text_input("Color", placeholder="Ej: AMARILLO")
        with col2:
            precio = st.number_input("Precio por KG", min_value=0.0, step=100.0, value=10000.0)
            minimo = st.number_input("Stock Mínimo (KG)", min_value=0.0, step=1.0, value=30.0)
        if st.form_submit_button("✅ Agregar Tela"):
            if not tipo or not color:
                st.error("Tipo y Color son obligatorios")
            else:
                resp = post_json("/telas", {
                    "codigo_tela": codigo,
                    "tipo": tipo.upper().strip(),
                    "color": color.upper().strip(),
                    "precio_kg": precio,
                    "minimo_kg": minimo
                })
                if resp:
                    st.success(f"Tela agregada: {resp['codigo_tela']} - {resp['tipo']} - {resp['color']}")
                    st.rerun()

elif menu == "🗑️ Eliminar Tela":
    st.subheader("Eliminar una Tela del Catálogo")
    telas = fetch_json("/telas")
    if telas:
        opciones = [f"{t['codigo_tela']} - {t['tipo']} - {t['color']}" for t in telas]
        if opciones:
            seleccion = st.selectbox("Seleccionar Tela a eliminar", opciones)
            if seleccion:
                partes = seleccion.split(' - ')
                codigo = float(partes[0])
                tipo = partes[1]
                color = partes[2]
            if st.button("🗑️ Eliminar Tela"):
                try:
                    r = requests.delete(f"{API_URL}/telas/{codigo}/{tipo}/{color}")
                    if r.status_code == 200:
                        st.success(r.json()["mensaje"])
                        st.rerun()
                    else:
                        st.error(r.json().get("detail", "Error al eliminar"))
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.info("No hay telas para eliminar.")
