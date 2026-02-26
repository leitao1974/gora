import streamlit as st
import google.generativeai as genai
import pandas as pd
import numpy as np
import sys
import matplotlib.pyplot as plt
import plotly.express as px
from io import StringIO
import uuid
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image

# --- 1. Configuração da Página ---
st.set_page_config(page_title="GORA Workspace", layout="wide", initial_sidebar_state="expanded")

# --- 2. CSS Neo-Brutalismo Moderno ---
st.markdown("""
    <style>
    .stApp { background-color: #F0F2F6; color: #1E1E1E; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 2px solid #E0E0E0; }
    h1, h2, h3 { color: #2E7D32 !important; font-weight: 800 !important; }
    .stChatMessage {
        background-color: #FFFFFF !important;
        border: 2px solid #E0E0E0 !important;
        border-radius: 10px !important;
        box-shadow: 5px 5px 0px rgba(46, 125, 50, 0.1) !important;
        margin-bottom: 15px;
    }
    .stButton button {
        border-radius: 8px !important;
        border: 2px solid #2E7D32 !important;
        font-weight: 700 !important;
        transition: all 0.2s ease;
        box-shadow: 3px 3px 0px rgba(46, 125, 50, 0.2);
    }
    .stButton button:hover { transform: translate(-2px, -2px); box-shadow: 5px 5px 0px rgba(46, 125, 50, 0.3); }
    .stTextArea textarea { font-family: 'Fira Code', monospace; background-color: #F9F9F9 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Funções Auxiliares ---
def extrair_texto_pdf(file):
    try:
        reader = PdfReader(file)
        return "".join([p.extract_text() for p in reader.pages])
    except: return ""

def extrair_texto_word(file):
    try:
        doc = Document(file)
        return "\n".join([p.text for p in doc.paragraphs])
    except: return ""

# --- 4. Inicialização de Estado ---
if "all_chats" not in st.session_state: st.session_state.all_chats = {}
if "current_chat_id" not in st.session_state: st.session_state.current_chat_id = None
if "suggestions" not in st.session_state: st.session_state.suggestions = []
if "code_to_lab" not in st.session_state: st.session_state.code_to_lab = ""
if "lab_globals" not in st.session_state:
    st.session_state.lab_globals = {'pd': pd, 'np': np, 'plt': plt, 'px': px, 'st': st}

# --- 5. Barra Lateral ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=60)
    st.title("GORA Workspace")
    menu_opcao = st.radio("Módulos", ["💬 GORA Chat", "💻 GORA Lab"], label_visibility="collapsed")
    
    st.divider()
    if st.button("➕ Novo Ciclo", use_container_width=True):
        nid = str(uuid.uuid4())
        st.session_state.all_chats[nid] = {"title": "Nova Inteligência", "history": []}
        st.session_state.current_chat_id = nid
        st.rerun()
    
    for cid, data in list(st.session_state.all_chats.items()):
        col1, col2 = st.columns([0.8, 0.2])
        if col1.button(data["title"], key=cid, use_container_width=True):
            st.session_state.current_chat_id = cid
            st.rerun()
        if col2.button("×", key=f"del_{cid}"):
            del st.session_state.all_chats[cid]
            st.rerun()

    st.divider()
    api_key = st.secrets.get("GOOGLE_API_KEY", st.text_input("Gemini API Key", type="password"))
    selected_model = None
    if api_key:
        genai.configure(api_key=api_key)
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            selected_model = st.selectbox("Engine:", models)
        except: st.error("Erro API")

# --- 6. GORA Chat ---
if menu_opcao == "💬 GORA Chat":
    st.markdown("## 💬 GORA Intelligence Chat")
    
    if not st.session_state.current_chat_id:
        st.info("Inicie um ciclo na barra lateral.")
    elif selected_model:
        chat_data = st.session_state.all_chats[st.session_state.current_chat_id]
        
        for message in chat_data["history"]:
            with st.chat_message("assistant" if message["role"] == "model" else "user"):
                st.markdown(message["parts"][0])

        if st.session_state.suggestions:
            cols = st.columns(len(st.session_state.suggestions))
            for i, sug in enumerate(st.session_state.suggestions):
                if cols[i].button(f"✨ {sug}", key=f"sug_{i}"):
                    st.session_state.prompt_input = sug
                    st.rerun()

        files = st.file_uploader("Arquivos", accept_multiple_files=True, label_visibility="collapsed")
        prompt = st.chat_input("Comande a GORA...")
        
        if "prompt_input" in st.session_state: prompt = st.session_state.pop("prompt_input")

        if prompt:
            with st.chat_message("user"): st.markdown(prompt)
            contexto = ""
            payload = [prompt]
            for f in files:
                if f.type.startswith('image/'): payload.append(Image.open(f))
                elif f.name.endswith('.pdf'): contexto += extrair_texto_pdf(f)
                elif f.name.endswith('.csv'): contexto += pd.read_csv(f).head().to_string()

            if contexto: payload.insert(0, f"CONTEXTO:\n{contexto}")

            model = genai.GenerativeModel(selected_model)
            chat_session = model.start_chat(history=chat_data["history"])
            
            with st.chat_message("assistant"):
                with st.spinner("GORA a processar..."):
                    instruct = "\n\nIMPORTANTE: No final, se geraste código Python, escreva 'CÓDIGO:' seguido apenas do código. Depois, escreva 'SUGESTÕES:' e 3 perguntas."
                    payload[-1] += instruct
                    response = chat_session.send_message(payload)
                    
                    # Lógica de extração de código para o Lab
                    full_text = response.text
                    main_resp = full_text.split("CÓDIGO:")[0].split("SUGESTÕES:")[0]
                    
                    if "CÓDIGO:" in full_text:
                        code_part = full_text.split("CÓDIGO:")[1].split("SUGESTÕES:")[0].strip()
                        st.session_state.code_to_lab = code_part
                        st.info("💻 Código detetado! Podes enviá-lo para o GORA Lab.")
                        if st.button("🚀 Enviar para o Lab"):
                            st.toast("Código transferido!")
                    
                    st.markdown(main_resp)
                    
                    if "SUGESTÕES:" in full_text:
                        sugs = full_text.split("SUGESTÕES:")[1].split(",")
                        st.session_state.suggestions = [s.strip() for s in sugs][:3]

            chat_data["history"].append({"role": "user", "parts": [prompt]})
            chat_data["history"].append({"role": "model", "parts": [main_resp]})
            if chat_data["title"] == "Nova Inteligência":
                chat_data["title"] = prompt[:20] + "..."
            st.rerun()

# --- 7. GORA Lab ---
elif menu_opcao == "💻 GORA Lab":
    st.markdown("## 💻 GORA Python Lab")
    
    # Se viemos do chat com código, preenchemos o editor
    initial_code = st.session_state.code_to_lab if st.session_state.code_to_lab else "# GORA Lab\nprint('Pronto para o teste!')"
    
    col_code, col_out = st.columns([1.2, 0.8], gap="medium")
    
    with col_code:
        code = st.text_area("Editor (Estilo Colab)", height=400, value=initial_code)
        c1, c2, c3 = st.columns(3)
        if c1.button("⚡ Executar", use_container_width=True):
            st.session_state.exec_trigger = True
        if c2.button("🧹 Limpar", use_container_width=True):
            st.session_state.code_to_lab = ""
            st.rerun()
        c3.download_button("💾 Exportar", code, file_name="gora.py", use_container_width=True)

    with col_out:
        st.write("📊 **Resultado**")
        if st.session_state.get("exec_trigger", False):
            old_stdout = sys.stdout
            sys.stdout = out = StringIO()
            try:
                # Execução com persistência de variáveis
                exec(code, st.session_state.lab_globals)
                st.code(out.getvalue() if out.getvalue() else "Executado (Sem output de texto).")
                st.success("Célula processada.")
            except Exception as e: st.error(f"Erro: {e}")
            finally:
                sys.stdout = old_stdout
                st.session_state.exec_trigger = False
