import streamlit as st
import google.generativeai as genai
import pandas as pd
import sys
from io import StringIO
import uuid
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image

# --- 1. Configuração Inicial da Página ---
st.set_page_config(
    page_title="Gemini AI Lab", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- 2. CSS para Fixar Abas (Sticky) e Permitir Scroll ---
st.markdown("""
    <style>
    /* Fixar a lista de abas no topo (Sticky) */
    div[data-testid="stTabs"] > div:first-child {
        position: -webkit-sticky !important;
        position: sticky !important;
        top: 2.85rem !important; /* Logo abaixo da barra de sistema do Streamlit */
        background-color: white !important;
        z-index: 999 !important;
        width: 100% !important;
        border-bottom: 2px solid #4CAF50 !important;
        padding-top: 5px !important;
        margin-bottom: 20px !important;
    }

    /* Ajuste para o Tema Escuro (Dark Mode) */
    @media (prefers-color-scheme: dark) {
        div[data-testid="stTabs"] > div:first-child {
            background-color: #0e1117 !important;
        }
    }

    /* Garantir que o container principal permite scroll fluido */
    .main .block-container {
        padding-top: 1rem !important;
        overflow-y: auto !important;
    }

    /* Estética dos botões */
    .stButton button {
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Funções de Extração de Documentos ---
def extrair_texto_pdf(file):
    try:
        reader = PdfReader(file)
        return "".join([p.extract_text() for p in reader.pages])
    except: return "Erro ao processar PDF."

def extrair_texto_word(file):
    try:
        doc = Document(file)
        return "\n".join([p.text for p in doc.paragraphs])
    except: return "Erro ao processar Word."

# --- 4. Gestão de Estado (Sessões de Conversa) ---
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {}
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

# --- 5. Barra Lateral (Histórico e API) ---
with st.sidebar:
    st.title("📂 Conversas")
    if st.button("➕ Nova Conversa", use_container_width=True):
        nid = str(uuid.uuid4())
        st.session_state.all_chats[nid] = {"title": "Nova Conversa", "messages": []}
        st.session_state.current_chat_id = nid
        st.rerun()
    
    st.divider()
    
    # Listar Histórico de Chats
    for cid, data in list(st.session_state.all_chats.items()):
        col1, col2 = st.columns([0.8, 0.2])
        if col1.button(data["title"], key=cid, use_container_width=True):
            st.session_state.current_chat_id = cid
            st.rerun()
        if col2.button("🗑️", key=f"del_{cid}"):
            del st.session_state.all_chats[cid]
            if st.session_state.current_chat_id == cid: st.session_state.current_chat_id = None
            st.rerun()

    st.divider()
    
    # Configuração da API Key
    api_key = st.secrets.get("GOOGLE_API_KEY", "")
    if not api_key:
        api_key = st.text_input("Introduza a Google API Key:", type="password")

    selected_model = None
    if api_key:
        genai.configure(api_key=api_key)
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            selected_model = st.selectbox("Modelo Gemini:", models)
        except: st.error("Chave API ou Conexão falhou.")

# --- 6. Interface de Abas Principal ---
tab1, tab2 = st.tabs(["💬 Chat Multimodal", "💻 Python Lab"])

# --- ABA 1: Chat Dinâmico com suporte a Ficheiros ---
with tab1:
    if not st.session_state.current_chat_id:
        st.info("Crie ou selecione uma conversa na barra lateral.")
    elif not selected_model:
        st.warning("Aguardando configuração da API Key...")
    else:
        chat_data = st.session_state.all_chats[st.session_state.current_chat_id]
        
        # Mostrar mensagens existentes
        for msg in chat_data["messages"]:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])

        # Upload de Ficheiros (PDF, Word, Imagem, CSV)
        files = st.file_uploader("Upload: PDF, Word, Imagem, CSV", accept_multiple_files=True)

        if prompt := st.chat_input("Diga algo ao Gemini..."):
            chat_data["messages"].append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("🤖 Analisando..."):
                    try:
                        model = genai.GenerativeModel(selected_model)
                        payload = [prompt]
                        contexto = ""
                        
                        for f in files:
                            if f.type.startswith('image/'):
                                payload.append(Image.open(f))
                            elif f.name.endswith('.pdf'):
                                contexto += f"\n[PDF: {f.name}]\n{extrair_texto_pdf(f)}"
                            elif f.name.endswith('.docx'):
                                contexto += f"\n[Word: {f.name}]\n{extrair_texto_word(f)}"
                            elif f.name.endswith('.csv'):
                                df = pd.read_csv(f)
                                contexto += f"\n[CSV: {f.name}]\n{df.head().to_string()}"
                        
                        if contexto: 
                            payload.insert(0, f"Contexto Extraído:\n{contexto}")
                        
                        resp = model.generate_content(payload)
                        st.markdown(resp.text)
                        chat_data["messages"].append({"role": "assistant", "content": resp.text})
                        
                        # Nomear o chat se for o início
                        if chat_data["title"] == "Nova Conversa":
                            chat_data["title"] = prompt[:20] + "..."
                            st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")

# --- ABA 2: Python Lab com Download de Scripts ---
with tab2:
    st.header("Python Lab")
    st.write("Execute código e exporte os seus scripts.")
    
    editor_code = st.text_area("Editor Python:", height=300, 
                              value="# Teste aqui o seu código\nimport pandas as pd\nprint('Ambiente ativo!')")
    
    col_run, col_dl = st.columns(2)
    with col_run:
        btn_run = st.button("▶ Executar Código", use_container_width=True)
    with col_dl:
        st.download_button(
            label="📥 Descarregar Script (.py)",
            data=editor_code,
            file_name="script_gerado.py",
            mime="text/x-python",
            use_container_width=True
        )

    if btn_run:
        old_stdout = sys.stdout
        sys.stdout = out = StringIO()
        try:
            # Executar código com bibliotecas essenciais injetadas
            exec(editor_code, {'pd': pd, 'st': st, 'genai': genai, 'plt': None})
            st.subheader("Output da Consola:")
            st.code(out.getvalue() if out.getvalue() else "Executado sem erros (sem output).")
        except Exception as e:
            st.error(f"Erro de Execução: {e}")
        finally:
            sys.stdout = old_stdout

