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

# --- 2. CSS Vanguardista (Dark Mode & Glassmorphism) ---
st.markdown("""
    <style>
    /* Fundo Geral e Fontes */
    .stApp {
        background-color: #0E1117;
        color: #E0E0E0;
    }
    
    /* Barra Lateral Estilizada */
    [data-testid="stSidebar"] {
        background-color: #161B22 !important;
        border-right: 1px solid #30363D;
    }
    
    /* Títulos e Headers */
    h1, h2, h3 {
        color: #4CAF50 !important;
        font-family: 'Inter', sans-serif;
        font-weight: 700;
    }

    /* Efeito Glassmorphism nos Cartões de Chat */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 15px !important;
        margin-bottom: 15px;
    }

    /* Botões de Sugestão Neon */
    .stButton button {
        border-radius: 30px !important;
        border: 1px solid #4CAF50 !important;
        background-color: transparent !important;
        color: #4CAF50 !important;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        box-shadow: 0 0 15px rgba(76, 175, 80, 0.4);
        background-color: #4CAF50 !important;
        color: white !important;
        transform: translateY(-2px);
    }

    /* Input de Chat */
    .stChatInputContainer {
        padding-bottom: 20px;
    }
    
    /* Customização do Editor de Código */
    .stTextArea textarea {
        background-color: #0D1117 !important;
        color: #79C0FF !important;
        border: 1px solid #30363D !important;
        font-family: 'Fira Code', monospace;
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

# --- 5. Barra Lateral GORA ---
with st.sidebar:
    st.image("https://img.icons8.com/neon/96/artificial-intelligence.png", width=80) # Ícone Vanguardista
    st.title("GORA Workspace")
    
    menu_opcao = st.radio("Módulos", ["💬 GORA Chat", "💻 GORA Lab"], label_visibility="collapsed")
    
    st.divider()
    if st.button("➕ Novo Briefing", use_container_width=True):
        nid = str(uuid.uuid4())
        st.session_state.all_chats[nid] = {"title": "Nova Conversa", "history": []}
        st.session_state.current_chat_id = nid
        st.session_state.suggestions = []
        st.rerun()
    
    st.write("### Histórico")
    for cid, data in list(st.session_state.all_chats.items()):
        col1, col2 = st.columns([0.85, 0.15])
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
        except: st.error("Erro de Conexão")

# --- 6. GORA Chat ---
if menu_opcao == "💬 GORA Chat":
    st.markdown("## 💬 GORA Intelligence")
    
    if not st.session_state.current_chat_id:
        st.info("Inicie um novo ciclo de inteligência no menu lateral.")
    elif selected_model:
        chat_data = st.session_state.all_chats[st.session_state.current_chat_id]
        
        # Histórico com Layout de Cartões
        for message in chat_data["history"]:
            role = "assistant" if message["role"] == "model" else "user"
            with st.chat_message(role): st.markdown(message["parts"][0])

        # Sugestões Ativas
        if st.session_state.suggestions:
            cols = st.columns(len(st.session_state.suggestions))
            for i, sug in enumerate(st.session_state.suggestions):
                if cols[i].button(f"✨ {sug}", key=f"sug_{i}", use_container_width=True):
                    st.session_state.prompt_input = sug
                    st.rerun()

        st.divider()
        files = st.file_uploader("Upload Multimodal", accept_multiple_files=True, label_visibility="collapsed")
        
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
            
            if chat_data["title"] == "Nova Conversa":
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
                # Injetamos o pandas e o streamlit no exec para facilitar
                exec(code, {'pd': pd, 'np': np, 'st': st})
                st.markdown('<div class="code-output">', unsafe_allow_html=True)
                st.code(out.getvalue())
                st.markdown('</div>', unsafe_allow_html=True)
            except Exception as e: st.error(f"Erro Crítico: {e}")
            finally: sys.stdout = old_stdout
        else:
            st.info("Aguardando execução de comando...")
