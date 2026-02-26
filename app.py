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
import time

# --- 1. Configuração da Página ---
st.set_page_config(page_title="GORA Workspace", layout="wide", initial_sidebar_state="expanded")

# --- 2. Design GORA Neo-Brutalista Claro ---
st.markdown("""
    <style>
    .stApp { background-color: #F0F2F6; color: #1E1E1E; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 2px solid #E0E0E0; box-shadow: 4px 0px 10px rgba(0,0,0,0.03); }
    h1, h2, h3 { color: #2E7D32 !important; font-weight: 800 !important; letter-spacing: -1px; }
    
    .stChatMessage {
        background-color: #FFFFFF !important;
        border: 2px solid #E0E0E0 !important;
        border-radius: 10px !important;
        box-shadow: 5px 5px 0px rgba(46, 125, 50, 0.1) !important;
        margin-bottom: 15px;
        padding: 15px !important;
    }
    
    .stButton button {
        border-radius: 8px !important;
        border: 2px solid #2E7D32 !important;
        background-color: #FFFFFF !important;
        color: #2E7D32 !important;
        font-weight: 700 !important;
        box-shadow: 3px 3px 0px rgba(46, 125, 50, 0.2);
        transition: all 0.2s ease;
    }
    .stButton button:hover { transform: translate(-2px, -2px); box-shadow: 5px 5px 0px rgba(46, 125, 50, 0.3); }
    
    .stTextArea textarea { font-family: 'Fira Code', monospace; background-color: #F9F9F9 !important; border: 2px solid #E0E0E0 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Funções de Extração Otimizadas ---
def extrair_texto_pdf(file):
    try:
        reader = PdfReader(file)
        texto = ""
        # Limita a 15 páginas para poupar quota no tier gratuito
        for i, page in enumerate(reader.pages[:15]):
            texto += page.extract_text()
        return texto
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
        st.session_state.suggestions = []
        st.rerun()
    
    st.write("### Histórico")
    for cid, data in list(st.session_state.all_chats.items()):
        col1, col2 = st.columns([0.82, 0.18])
        if col1.button(data["title"], key=cid, use_container_width=True):
            st.session_state.current_chat_id = cid
            st.rerun()
        if col2.button("×", key=f"del_{cid}"):
            del st.session_state.all_chats[cid]
            if st.session_state.current_chat_id == cid: st.session_state.current_chat_id = None
            st.rerun()

    st.divider()
    api_key = st.secrets.get("GOOGLE_API_KEY", st.text_input("Gemini API Key", type="password"))
    
    selected_model = None
    if api_key:
        genai.configure(api_key=api_key)
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            # Sugere-se o 1.5-flash para evitar erros de quota
            selected_model = st.selectbox("Engine:", models, index=0)
        except: st.error("Erro na API Key.")

# --- 6. GORA Chat ---
if menu_opcao == "💬 GORA Chat":
    st.markdown("## 💬 GORA Intelligence")
    
    if not st.session_state.current_chat_id:
        st.info("Inicie um ciclo na barra lateral.")
    elif selected_model:
        chat_data = st.session_state.all_chats[st.session_state.current_chat_id]
        
        for message in chat_data["history"]:
            with st.chat_message("assistant" if message["role"] == "model" else "user"):
                st.markdown(message["parts"][0])

        if st.session_state.suggestions:
            st.write("💡 *Sugestões:*")
            cols = st.columns(len(st.session_state.suggestions))
            for i, sug in enumerate(st.session_state.suggestions):
                if cols[i].button(f"✨ {sug}", key=f"sug_{i}"):
                    st.session_state.prompt_input = sug
                    st.rerun()

        files = st.file_uploader("Documentos/Imagens", accept_multiple_files=True, label_visibility="collapsed")
        prompt = st.chat_input("Comande a GORA...")
        
        if "prompt_input" in st.session_state: prompt = st.session_state.pop("prompt_input")

        if prompt:
            with st.chat_message("user"): st.markdown(prompt)
            
            contexto = ""
            payload = [prompt]
            for f in files:
                if f.type.startswith('image/'): payload.append(Image.open(f))
                elif f.name.endswith('.pdf'): contexto += f"\n[Doc: {f.name}] {extrair_texto_pdf(f)}"
                elif f.name.endswith('.docx'): contexto += f"\n[Doc: {f.name}] {extrair_texto_word(f)}"
                elif f.name.endswith('.csv'): contexto += f"\n[CSV: {f.name}] {pd.read_csv(f).head().to_string()}"

            if contexto: payload.insert(0, f"CONTEXTO:\n{contexto}")

            model = genai.GenerativeModel(selected_model)
            chat_session = model.start_chat(history=chat_data["history"])
            
            with st.chat_message("assistant"):
                with st.spinner("GORA a analisar..."):
                    try:
                        instruct = "\n\nResponde e, se incluíres código Python, termina com 'CÓDIGO:' e o bloco. Por fim, termina SEMPRE com 'SUGESTÕES:' e 3 perguntas curtas."
                        payload[-1] += instruct
                        
                        response = chat_session.send_message(payload)
                        full_text = response.text
                        
                        # Parsing da resposta
                        main_resp = full_text.split("CÓDIGO:")[0].split("SUGESTÕES:")[0].strip()
                        
                        if "CÓDIGO:" in full_text:
                            code_part = full_text.split("CÓDIGO:")[1].split("SUGESTÕES:")[0].strip()
                            st.session_state.code_to_lab = code_part.replace('```python', '').replace('```', '')
                            st.success("💻 Código transferível para o Lab detetado!")
                            if st.button("🚀 Enviar para o GORA Lab"):
                                st.toast("Código pronto no Lab!")

                        st.markdown(main_resp)
                        
                        if "SUGESTÕES:" in full_text:
                            sugs = full_text.split("SUGESTÕES:")[1].split(",")
                            st.session_state.suggestions = [s.strip() for s in sugs][:3]

                        chat_data["history"].append({"role": "user", "parts": [prompt]})
                        chat_data["history"].append({"role": "model", "parts": [main_resp]})
                        
                        if chat_data["title"] == "Nova Inteligência":
                            chat_data["title"] = prompt[:20] + "..."
                        st.rerun()

                    except Exception as e:
                        if "429" in str(e):
                            st.error("⚠️ Quota Excedida. Aguarda 60s.")
                        else:
                            st.error(f"Erro: {e}")

# --- 7. GORA Lab ---
elif menu_opcao == "💻 GORA Lab":
    st.markdown("## 💻 GORA Python Lab")
    
    current_code = st.session_state.code_to_lab if st.session_state.code_to_lab else "# GORA Lab\nprint('Aguardando código...')"
    
    col_code, col_out = st.columns([1.2, 0.8], gap="medium")
    
    with col_code:
        st.write("🛠️ **Editor**")
        code = st.text_area("Célula de Código", height=450, value=current_code)
        c1, c2, c3 = st.columns(3)
        exec_btn = c1.button("⚡ Executar", use_container_width=True)
        if c2.button("🧹 Limpar", use_container_width=True):
            st.session_state.code_to_lab = ""
            st.rerun()
        c3.download_button("💾 Exportar", code, file_name="gora_script.py", use_container_width=True)

    with col_out:
        st.write("📊 **Output**")
        if exec_btn:
            old_stdout = sys.stdout
            sys.stdout = out = StringIO()
            try:
                # Execução com persistência de variáveis (Estilo Colab)
                exec(code, st.session_state.lab_globals)
                st.code(out.getvalue() if out.getvalue() else "Sucesso (sem output de texto).")
            except Exception as e: st.error(f"Erro: {e}")
            finally: sys.stdout = old_stdout
        else:
            st.info("O resultado aparecerá aqui.")

