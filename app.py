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

# --- 2. Funções de Extração de Documentos ---
def extrair_texto_pdf(file):
    try:
        reader = PdfReader(file)
        return "".join([p.extract_text() for p in reader.pages])
    except: return "Erro ao ler PDF."

def extrair_texto_word(file):
    try:
        doc = Document(file)
        return "\n".join([p.text for p in doc.paragraphs])
    except: return "Erro ao ler Word."

# --- 3. Gestão de Estado (Sessões) ---
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {}
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

# --- 4. Barra Lateral (Navegação e Configurações) ---
with st.sidebar:
    st.title("🚀 Gemini AI Lab")
    
    # NAVEGAÇÃO PRINCIPAL (Substitui as Tabs de topo)
    st.subheader("Navegação")
    menu_opcao = st.radio("Ir para:", ["💬 Chat Multimodal", "💻 Python Lab"])
    
    st.divider()
    st.subheader("📂 Conversas")
    
    if st.button("➕ Nova Conversa", use_container_width=True):
        nid = str(uuid.uuid4())
        st.session_state.all_chats[nid] = {"title": "Nova Conversa", "messages": []}
        st.session_state.current_chat_id = nid
        st.rerun()
    
    # Listar Histórico
    for cid, data in list(st.session_state.all_chats.items()):
        col1, col2 = st.columns([0.8, 0.2])
        if col1.button(data["title"], key=cid, use_container_width=True):
            st.session_state.current_chat_id = cid
            # Forçar mudança para o chat se clicar numa conversa antiga
            # menu_opcao = "💬 Chat Multimodal" 
        if col2.button("🗑️", key=f"del_{cid}"):
            del st.session_state.all_chats[cid]
            if st.session_state.current_chat_id == cid: st.session_state.current_chat_id = None
            st.rerun()

    st.divider()
    
    # API Key
    api_key = st.secrets.get("GOOGLE_API_KEY", "")
    if not api_key:
        api_key = st.text_input("Introduza a Google API Key:", type="password")

    selected_model = None
    if api_key:
        genai.configure(api_key=api_key)
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            selected_model = st.selectbox("Modelo:", models)
        except: st.error("Erro na API Key.")

# --- 5. Lógica de Exibição Baseada na Navegação Lateral ---

if menu_opcao == "💬 Chat Multimodal":
    st.header("Chat Dinâmico")
    
    if not st.session_state.current_chat_id:
        st.info("Crie uma conversa na barra lateral para começar.")
    elif not selected_model:
        st.warning("Configure a API Key para continuar.")
    else:
        chat_data = st.session_state.all_chats[st.session_state.current_chat_id]
        
        # Histórico
        for msg in chat_data["messages"]:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])

        # Upload
        files = st.file_uploader("Upload: PDF, Word, Imagem, CSV", accept_multiple_files=True)

        if prompt := st.chat_input("Pergunte algo ao Gemini..."):
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
                                contexto += f"\n[CSV: {f.name}]\n{pd.read_csv(f).head().to_string()}"
                        
                        if contexto: payload.insert(0, f"Contexto:\n{contexto}")
                        
                        resp = model.generate_content(payload)
                        st.markdown(resp.text)
                        chat_data["messages"].append({"role": "assistant", "content": resp.text})
                        
                        if chat_data["title"] == "Nova Conversa":
                            chat_data["title"] = prompt[:20] + "..."
                            st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")

elif menu_opcao == "💻 Python Lab":
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
            exec(editor_code, {'pd': pd, 'st': st, 'genai': genai})
            st.subheader("Output da Consola:")
            st.code(out.getvalue() if out.getvalue() else "Executado com sucesso.")
        except Exception as e:
            st.error(f"Erro: {e}")
        finally:
            sys.stdout = old_stdout

