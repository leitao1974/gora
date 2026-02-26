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
st.set_page_config(page_title="Gemini AI Lab", layout="wide", initial_sidebar_state="expanded")

# --- 2. CSS Corrigido (Tabs Sticky + Scroll Ativo) ---
st.markdown("""
    <style>
    /* Faz a barra de abas ficar colada no topo sem bloquear o scroll do corpo */
    .stTabs [data-baseweb="tab-list"] {
        position: -webkit-sticky !important;
        position: sticky !important;
        top: 0px !important;
        background-color: white !important;
        z-index: 1000 !important;
        border-bottom: 2px solid #4CAF50 !important;
        padding-top: 10px !important;
        width: 100% !important;
    }

    /* Garante que o conteúdo tenha espaço e não fique por baixo da barra */
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 20px !important;
    }

    /* Estilo para os botões da barra lateral */
    .stButton button {
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Funções de Suporte para Documentos ---
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

# --- 4. Inicialização do Estado (Sessões) ---
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
    
    # Listar Histórico
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
    
    # Configuração da API
    api_key = st.secrets.get("GOOGLE_API_KEY", "")
    if not api_key:
        api_key = st.text_input("Introduza a Google API Key:", type="password")

    selected_model = None
    if api_key:
        genai.configure(api_key=api_key)
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            selected_model = st.selectbox("Modelo Gemini:", models)
        except: st.error("Erro na API Key ou conexão.")

# --- 6. Abas Principais ---
tab1, tab2 = st.tabs(["💬 Chat Dinâmico", "💻 Python Lab"])

with tab1:
    if not st.session_state.current_chat_id:
        st.info("Crie ou selecione uma conversa na barra lateral.")
    elif not selected_model:
        st.warning("Aguardando configuração da API Key...")
    else:
        chat_session = st.session_state.all_chats[st.session_state.current_chat_id]
        
        # Histórico de mensagens
        for msg in chat_session["messages"]:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])

        # Upload Multimodal
        files = st.file_uploader("Upload: PDF, Word, Imagem, CSV, TXT", accept_multiple_files=True)

        if prompt := st.chat_input("Como posso ajudar hoje?"):
            chat_session["messages"].append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("🤖 O Gemini está a analisar..."):
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
                        
                        if contexto: payload.insert(0, f"Contexto extraído:\n{contexto}")
                        
                        resp = model.generate_content(payload)
                        st.markdown(resp.text)
                        chat_session["messages"].append({"role": "assistant", "content": resp.text})
                        
                        # Atualizar título da conversa
                        if chat_session["title"] == "Nova Conversa":
                            chat_session["title"] = prompt[:25] + "..."
                            st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")

with tab2:
    st.header("Python Lab")
    st.write("Teste o código gerado pela IA ou faça as suas próprias análises.")
    
    code_area = st.text_area("Editor de Código:", height=300, 
                            value="# Exemplo de análise\nimport pandas as pd\nprint('Ambiente de teste pronto.')")
    
    c1, c2 = st.columns(2)
    with c1:
        run = st.button("▶ Executar Código", use_container_width=True)
    with c2:
        st.download_button(
            label="📥 Descarregar Script (.py)",
            data=code_area,
            file_name="script_lab.py",
            mime="text/x-python",
            use_container_width=True
        )

    if run:
        old_stdout = sys.stdout
        sys.stdout = out = StringIO()
        try:
            # Execução com variáveis globais úteis
            exec(code_area, {'pd': pd, 'st': st, 'genai': genai})
            st.subheader("Consola:")
            result = out.getvalue()
            st.code(result if result else "Executado com sucesso.")
        except Exception as e:
            st.error(f"Erro de Execução: {e}")
        finally:
            sys.stdout = old_stdout

