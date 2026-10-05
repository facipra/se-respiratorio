"""
SE para orientacion rapida en Infecciones Respiratorias Agudas (IRA)
Especialidad: Neumologia / Medicina general - Curso Inteligencia Artificial 2 (UNT)
Metodologia: guia para construir un Sistema Experto
  variables -> diagrama de dependencias -> tablas de decision -> reglas IF-THEN
Ejecutar:  streamlit run app.py
AVISO: herramienta academica; NO reemplaza una evaluacion medica.
"""
import streamlit as st

# ----------------------------------------------------------------------
# BASE DE CONOCIMIENTO (reglas IF-THEN en encadenamiento hacia adelante)
# Cada regla: (nombre, condicion(hechos)->bool, variable, valor, explicacion)
# ----------------------------------------------------------------------
REGLAS = [
    # --- Nivel 1: signos de alarma (triangulo 1) ---
    ("R1", lambda h: h["disnea"] == "en reposo", "alarma", "si",
     "Dificultad para respirar en reposo"),
    ("R2", lambda h: h["dolor_toracico"] == "si", "alarma", "si",
     "Dolor en el pecho"),
    ("R3", lambda h: h["cianosis_confusion"] == "si", "alarma", "si",
     "Labios azulados o confusion"),
    ("R4", lambda h: h["disnea"] != "en reposo" and h["dolor_toracico"] == "no"
     and h["cianosis_confusion"] == "no", "alarma", "no",
     "Sin signos de alarma"),

    # --- Nivel 2: perfil sintomatico (triangulo 2) ---
    ("R5", lambda h: h["fiebre"] == "alta (>= 38.5)" and h["malestar"] == "intenso"
     and h["inicio"] == "brusco", "perfil", "sistemico",
     "Fiebre alta + malestar intenso + inicio brusco"),
    ("R6", lambda h: h["perdida_olfato"] == "si", "perfil", "anosmia",
     "Perdida de olfato o gusto"),
    ("R7", lambda h: h["garganta"] == "intenso" and h["tos"] == "no"
     and h["congestion"] == "no" and h["fiebre"] != "no", "perfil", "faringeo",
     "Dolor de garganta intenso con fiebre, sin tos ni congestion"),
    ("R8", lambda h: h["tos"] == "con flema" and h["fiebre"] != "no"
     and h["disnea"] != "no", "perfil", "bajo",
     "Tos con flema + fiebre + falta de aire"),
    ("R9", lambda h: h["congestion"] == "si" and h["fiebre"] in ("no", "leve (37.5-38.4)"),
     "perfil", "alto",
     "Congestion nasal con fiebre ausente o leve"),

    # --- Nivel 3: riesgo (triangulo 3) ---
    ("R10", lambda h: h["edad"] in ("< 5 anios", ">= 65 anios") or h["comorbilidad"] == "si",
     "riesgo", "alto", "Grupo de edad o comorbilidad de riesgo"),
    ("R11", lambda h: h["edad"] == "5 a 64 anios" and h["comorbilidad"] == "no",
     "riesgo", "bajo", "Sin factores de riesgo"),

    # --- Nivel 4: diagnostico orientativo (triangulo final) ---
    ("R12", lambda h: h.get("alarma") == "si", "dx", "Urgencia respiratoria",
     "Hay al menos un signo de alarma"),
    ("R13", lambda h: h.get("alarma") == "no" and h.get("perfil") == "bajo",
     "dx", "Sospecha de neumonia", "Perfil de vias respiratorias bajas"),
    ("R14", lambda h: h.get("alarma") == "no" and h.get("perfil") == "sistemico",
     "dx", "Sindrome gripal (influenza probable)", "Perfil sistemico agudo"),
    ("R15", lambda h: h.get("alarma") == "no" and h.get("perfil") == "anosmia",
     "dx", "COVID-19 posible", "Anosmia/ageusia"),
    ("R16", lambda h: h.get("alarma") == "no" and h.get("perfil") == "faringeo",
     "dx", "Faringitis probable (descartar origen bacteriano)", "Perfil faringeo"),
    ("R17", lambda h: h.get("alarma") == "no" and h.get("perfil") == "alto",
     "dx", "Resfriado comun", "Perfil de vias respiratorias altas"),
    ("R18", lambda h: h.get("alarma") == "no" and "perfil" not in h,
     "dx", "Cuadro inespecifico", "Ningun perfil clinico coincide"),

    # --- Nivel 5: recomendacion (combina dx + riesgo) ---
    ("R19", lambda h: h.get("dx") == "Urgencia respiratoria", "atencion", "Nivel 1: EMERGENCIA",
     "Urgencia respiratoria"),
    ("R20", lambda h: h.get("dx") == "Sospecha de neumonia", "atencion",
     "Nivel 1: EMERGENCIA", "Sospecha de neumonia"),
    ("R21", lambda h: h.get("dx") in ("Sindrome gripal (influenza probable)",
                                        "COVID-19 posible") and h.get("riesgo") == "alto",
     "atencion", "Nivel 2: consulta medica en 24 h", "Cuadro viral + riesgo alto"),
    ("R22", lambda h: h.get("dx") in ("Sindrome gripal (influenza probable)",
                                        "COVID-19 posible",
                                        "Faringitis probable (descartar origen bacteriano)")
     and h.get("riesgo") == "bajo",
     "atencion", "Nivel 3: consulta ambulatoria / prueba", "Cuadro leve + riesgo bajo"),
    ("R23", lambda h: h.get("dx") in ("Resfriado comun", "Cuadro inespecifico")
     and h.get("riesgo") == "alto",
     "atencion", "Nivel 2: consulta medica en 24 h", "Sintomas leves pero riesgo alto"),
    ("R24", lambda h: h.get("dx") in ("Resfriado comun", "Cuadro inespecifico")
     and h.get("riesgo") == "bajo",
     "atencion", "Nivel 4: manejo en casa y vigilancia", "Sintomas leves + riesgo bajo"),
    ("R25", lambda h: h.get("dx") == "Faringitis probable (descartar origen bacteriano)"
     and h.get("riesgo") == "alto",
     "atencion", "Nivel 2: consulta medica en 24 h", "Faringitis + riesgo alto"),
]

CONSEJOS = {
    "Nivel 1": "Acuda de inmediato a un servicio de emergencia.",
    "Nivel 2": "Programe consulta medica dentro de las proximas 24 horas.",
    "Nivel 3": "Consulte en un centro de salud; puede requerir prueba diagnostica.",
    "Nivel 4": "Reposo, hidratacion y vigilancia. Consulte si empeora o dura mas de 7 dias.",
}


def inferir(hechos):
    """Encadenamiento hacia adelante hasta que no se dispare ninguna regla nueva."""
    h = dict(hechos)
    disparadas = []
    cambio = True
    while cambio:
        cambio = False
        for nombre, cond, var, val, why in REGLAS:
            if var in h:
                continue
            if cond(h):
                h[var] = val
                disparadas.append((nombre, var, val, why))
                cambio = True
    return h, disparadas


# ----------------------------------------------------------------------
# INTERFAZ DE USUARIO
# ----------------------------------------------------------------------
st.set_page_config(page_title="SE Infecciones Respiratorias", page_icon="🫁")
st.title("🫁 Sistema Experto: orientacion en Infecciones Respiratorias Agudas")
st.caption("Especialidad: Neumologia / Medicina general · Herramienta academica, "
           "no sustituye la evaluacion de un profesional de salud.")

with st.form("consulta"):
    st.subheader("Datos del paciente")
    c1, c2 = st.columns(2)
    edad = c1.selectbox("Grupo de edad", ["< 5 anios", "5 a 64 anios", ">= 65 anios"], index=1)
    comorbilidad = c2.radio("¿Asma, EPOC, diabetes, cardiopatia o inmunosupresion?",
                            ["no", "si"], horizontal=True)

    st.subheader("Sintomas")
    c3, c4 = st.columns(2)
    fiebre = c3.selectbox("Fiebre", ["no", "leve (37.5-38.4)", "alta (>= 38.5)"])
    inicio = c4.selectbox("Inicio del cuadro", ["gradual", "brusco"])
    tos = c3.selectbox("Tos", ["no", "seca", "con flema"])
    garganta = c4.selectbox("Dolor de garganta", ["no", "leve", "intenso"])
    congestion = c3.radio("Congestion o secrecion nasal", ["no", "si"], horizontal=True)
    malestar = c4.selectbox("Malestar general / dolor muscular", ["leve", "intenso"])
    perdida_olfato = c3.radio("Perdida de olfato o gusto", ["no", "si"], horizontal=True)

    st.subheader("Signos de alarma")
    disnea = st.selectbox("Dificultad para respirar", ["no", "al esfuerzo", "en reposo"])
    c5, c6 = st.columns(2)
    dolor_toracico = c5.radio("Dolor en el pecho", ["no", "si"], horizontal=True)
    cianosis_confusion = c6.radio("Labios azulados o confusion", ["no", "si"], horizontal=True)

    enviado = st.form_submit_button("Evaluar", type="primary")

if enviado:
    hechos = dict(edad=edad, comorbilidad=comorbilidad, fiebre=fiebre, inicio=inicio,
                  tos=tos, garganta=garganta, congestion=congestion, malestar=malestar,
                  perdida_olfato=perdida_olfato, disnea=disnea,
                  dolor_toracico=dolor_toracico, cianosis_confusion=cianosis_confusion)
    h, disparadas = inferir(hechos)

    atencion = h.get("atencion", "Nivel 2: consulta medica en 24 h")
    nivel = atencion.split(":")[0]
    st.divider()
    st.subheader("Resultado")
    st.metric("Orientacion diagnostica", h.get("dx", "Sin conclusion"))
    msg = f"**Atencion recomendada: {atencion}**  \n{CONSEJOS.get(nivel, '')}"
    {"Nivel 1": st.error, "Nivel 2": st.warning,
     "Nivel 3": st.info, "Nivel 4": st.success}.get(nivel, st.info)(msg)

    with st.expander("¿Por que? (reglas disparadas)"):
        for nombre, var, val, why in disparadas:
            st.write(f"**{nombre}** → `{var} = {val}` — {why}")
else:
    st.info("Complete el formulario y presione **Evaluar**.")
