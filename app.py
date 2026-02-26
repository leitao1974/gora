import streamlit as st
import google.generativeai as genai
import pandas as pd
import sys
from io import StringIO
import uuid
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image

# --- 1. Configuração da Página ---
st.set_page_config(page_title="GORA Workspace", layout="wide", initial_sidebar_state="expanded")

# --- 2. CSS Neo-Brutalismo Soft & Glassmorphism Claro ---
st.markdown("""
    <style>
    /* Fundo Geral Claro e Leve */
    .stApp {
        background-color: #F0F2F6;
        color: #1E1E1E;
        font-family: 'Inter', sans-serif;
    }
    
    /* Barra Lateral Moderna e Clara */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 2px solid #E0E0E0;
        box-shadow: 4px 0px 10px rgba(0,0,0,0.03);
    }
    
    /* Títulos Principais GORA (Verde Esmeralda) */
    h1, h2, h3 {
        color: #2E7D32 !important; /* Verde GORA Sólido */
        font-weight: 800 !important;
        letter-spacing: -1px;
    }

    /* Cartões de Chat Estilo 'Neo-Brutalismo Soft' */
    .stChatMessage {
        background-color: #FFFFFF !important;
        border: 2px solid #E0E0E0 !important;
        border-radius: 10px !important;
        box-shadow: 5px 5px 0px rgba(46, 125, 50, 0.1) !important; /* Sombra sólida suave */
        margin-bottom: 15px;
        padding: 15px !important;
    }

    /* Botões Modernos e Vibrantes */
    .stButton button {
        border-radius: 8px !important;
        border: 2px solid #2E7D32 !important;
        background-color: #FFFFFF !important;
        color: #2E7D32 !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.2s ease;
        box-shadow: 3px 3px 0px rgba(46, 125, 50, 0.2);
    }
    .stButton button:hover {
        background-color: #2E7D32 !important;
        color: white !important;
        transform: translate(-2px, -2px);
        box-shadow: 5px 5px 0px rgba(46, 125, 50, 0.3);
    }
    .stButton button:active {
        transform: translate(2px, 2px);
        box-shadow: 1px 1px 0px rgba(46, 125, 50, 0.3);
    }

    /* Caixas de Input e Texto Modernas */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background-color: #FFFFFF !important;
        border: 2px solid #E0E0E0 !important;
        border-radius: 8px !important;
        color: #1E1E1E !important;
        padding: 10px !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #2E7D32 !important;
        box-shadow: 0 0 0 3px rgba(46, 125, 50, 0.1) !important;
    }
    
    /* Área de Upload Estilizada */
    [data-testid="stFileUploader"] {
        background-color: #FFFFFF;
        border: 2px dashed #2E7D32;
        border-radius: 10px;
        padding: 10px;
    }

    /* Customização do Editor de Código (Contraste Claro) */
    .stTextArea textarea {
        font-family: 'Fira Code', monospace;
        background-color: #F9F9F9 !important;
        color: #0056b3 !important; /* Azul Elétrico para Código */
        border: 2px solid #E0E0E0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Funções de Extração ---
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

# --- 4. Inicialização do Estado ---
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {}
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None
if "suggestions" not in st.session_state:
    st.session_state.suggestions = []

# --- 5. Barra Lateral GORA (Design Claro) ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=70) # Ícone Moderno Colorido
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
            selected_model = st.selectbox("Engine:", models)
        except: st.error("Erro de Conexão API")

# --- 6. GORA Chat ---
if menu_opcao == "💬 GORA Chat":
    st.markdown("## 💬 GORA Intelligence Chat")
    
    if not st.session_state.current_chat_id:
        st.info("Inicie um novo ciclo de inteligência no menu lateral.")
    elif selected_model:
        chat_data = st.session_state.all_chats[st.session_state.current_chat_id]
        
        # Histórico com Layout de Cartões Claros
        for message in chat_data["history"]:
            role = "assistant" if message["role"] == "model" else "user"
            with st.chat_message(role): st.markdown(message["parts"][0])

        # Sugestões Ativas (Botões Neon Soft)
        if st.session_state.suggestions:
            cols = st.columns(len(st.session_state.suggestions))
            for i, sug in enumerate(st.session_state.suggestions):
                if cols[i].button(f"✨ {sug}", key=f"sug_{i}", use_container_width=True):
                    st.session_state.prompt_input = sug
                    st.rerun()

        st.divider()
        files = st.file_uploader("Upload Multimodal (PDF, Word, CSV)", accept_multiple_files=True, label_visibility="collapsed")
        
        prompt = st.chat_input("Comande a GORA...")
        if "prompt_input" in st.session_state:
            prompt = st.session_state.pop("prompt_input")

        if prompt:
            with st.chat_message("user"): st.markdown(prompt)
            
            contexto = ""
            payload = [prompt]
            for f in files:
                if f.type.startswith('image/'): payload.append(Image.open(f))
                elif f.name.endswith('.pdf'): contexto += extrair_texto_pdf(f)
                elif f.name.endswith('.docx'): contexto += extrair_texto_word(f)
                elif f.name.endswith('.csv'): contexto += pd.read_csv(f).head().to_string()

            if contexto: payload.insert(0, f"CONTEXTO DO UTILIZADOR:\n{contexto}")

            model = genai.GenerativeModel(selected_model)
            chat_session = model.start_chat(history=chat_data["history"])
            
            with st.chat_message("assistant"):
                with st.spinner("GORA está a processar..."):
                    instruct = "\n\nIMPORTANTE: No final, escreva 'SUGESTÕES:' e 3 perguntas curtas para continuar, separadas por vírgula."
                    payload[-1] = payload[-1] + instruct
                    
                    response = chat_session.send_message(payload)
                    
                    parts = response.text.split("SUGESTÕES:")
                    resp_principal = parts[0]
                    novas_sug = parts[1].split(",") if len(parts) > 1 else []
                    
                    st.markdown(resp_principal)
                    st.session_state.suggestions = [s.strip() for s in novas_sug][:3]

            chat_data["history"].append({"role": "user", "parts": [prompt]})
            chat_data["history"].append({"role": "model", "parts": [resp_principal]})
            
            if chat_data["title"] == "Nova Inteligência":
                chat_data["title"] = prompt[:20] + "..."
            st.rerun()

# --- 7. GORA Lab ---
elif menu_opcao == "💻 GORA Lab":
    st.markdown("## 💻 GORA Python Lab")
    
    col_code, col_out = st.columns([1.2, 0.8], gap="medium")
    
    with col_code:
        st.write("🛠️ **Scripting**")
        code = st.text_area("Python Editor", height=450, value="# GORA Lab Engine\nimport pandas as pd\nimport numpy as np\n\nprint('GORA Lab Ativo.')")
        c1, c2 = st.columns(2)
        exec_btn = c1.button("⚡ Executar Código", use_container_width=True)
        c2.download_button("💾 Exportar .py", code, file_name="gora_script.py", use_container_width=True)

    with col_out:
        st.write("📊 **Terminal Output**")
        if exec_btn:
            old_stdout = sys.stdout
            sys.stdout = out = StringIO()
            try:
                exec(code, {'pd': pd, 'np': np, 'st': st})
                st.code(out.getvalue())
            except Exception as e: st.error(f"Erro Crítico: {e}")
            finally: sys.stdout = old_stdout
        else:
            st.info("Aguardando execução de comando...")
