import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import numpy as np
import sys
import os
import requests
import uuid
import json
import time
from PIL import Image

# --- 1. Configuração da Página ---
st.set_page_config(page_title="GORA Workspace", layout="wide", initial_sidebar_state="expanded")

# --- 2. Persistência de Dados (Custos e Conversas) ---
DB_FILE = "gora_database.json"

def carregar_dados():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {
        "total_eur": 0.0, 
        "total_tokens": 0,
        "all_chats": {} 
    }

def salvar_dados(dados):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

# --- 3. Interface Visual Clássica ---
st.markdown("""
    <style>
    .stApp { 
        background-color: #F0F2F6 !important; 
        color: #1E1E1E !important; 
        font-family: 'Inter', sans-serif; 
    }
    [data-testid="stSidebar"] { 
        background-color: #FFFFFF !important; 
        border-right: 2px solid #E0E0E0 !important; 
    }
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] div { 
        color: #1E1E1E !important; 
    }
    h1, h2, h3 { 
        color: #2E7D32 !important; 
        font-weight: 800 !important; 
        letter-spacing: -0.5px; 
    }
    .stChatMessage {
        background-color: #FFFFFF !important; 
        border: 2px solid #E0E0E0 !important;
        border-radius: 12px !important; 
        box-shadow: 6px 6px 0px rgba(46, 125, 50, 0.08) !important;
        margin-bottom: 15px; 
        padding: 20px !important;
        color: #1E1E1E !important;
    }
    .stButton>button { 
        border-radius: 10px !important; 
        border: 2px solid #2E7D32 !important;
        background-color: #FFFFFF !important; 
        color: #2E7D32 !important;
        font-weight: 800 !important; 
        box-shadow: 4px 4px 0px rgba(46, 125, 50, 0.2) !important;
        transition: all 0.2s !important;
    }
    .stButton>button:hover { 
        background-color: #2E7D32 !important;
        color: #FFFFFF !important;
        transform: translate(-2px, -2px) !important;
        box-shadow: 6px 6px 0px rgba(46, 125, 50, 0.3) !important;
    }
    div[data-testid="stSidebar"] .stButton>button {
        border: 2px solid #ef4444 !important;
        color: #ef4444 !important;
        box-shadow: 4px 4px 0px rgba(239, 68, 68, 0.2) !important;
    }
    div[data-testid="stSidebar"] .stButton>button:hover {
        background-color: #ef4444 !important;
        color: #FFFFFF !important;
        box-shadow: 6px 6px 0px rgba(239, 68, 68, 0.3) !important;
    }
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #FFFFFF !important;
        color: #1E1E1E !important;
        border: 2px solid #E0E0E0 !important;
        border-radius: 8px !important;
    }
    .stFileUploader {
        background-color: #FFFFFF !important;
        border: 2px dashed #2E7D32 !important;
        border-radius: 10px !important;
        padding: 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)

db = carregar_dados()

# --- 4. Inicialização do State ---
if "total_eur" not in st.session_state:
    st.session_state.total_eur = db.get("total_eur", 0.0)
if "total_tokens_session" not in st.session_state:
    st.session_state.total_tokens_session = db.get("total_tokens", 0)
if "all_chats" not in st.session_state:
    st.session_state.all_chats = db.get("all_chats", {})
if "chat_atual" not in st.session_state:
    st.session_state.chat_atual = "Conversa Padrão"
if "taxa_cambio" not in st.session_state:
    try:
        res = requests.get("https://open.er-api.com/v6/latest/USD").json()
        st.session_state.taxa_cambio = res["rates"]["EUR"]
    except:
        st.session_state.taxa_cambio = 0.92

if st.session_state.chat_atual not in st.session_state.all_chats:
    st.session_state.all_chats[st.session_state.chat_atual] = {"model": "gemini-2.5-flash", "history": []}

# --- 5. Instruções de Sistema ---
INSTRUCOES_SISTEMA = """
Atuas como um assistente jurídico e analista técnico altamente qualificado, especializado em processos de fiscalização do território, planeamento regional e direito do ambiente em Portugal. O teu objetivo é analisar dados de processos confidenciais, emitir pareceres e cruzar informações com base nos documentos submetidos pelo utilizador e no enquadramento legislativo obrigatório detalhado abaixo.

Sempre que analisares uma infração, uso, ocupação ou ação no território, deves obrigatoriamente enquadrar e consultar a seguinte legislação aplicável, conforme o caso:

1. RESERVA ECOLÓGICA NACIONAL (REN):
- Decreto-Lei n.º 166/2008, de 22 de agosto (Estabelece o regime jurídico da Reserva Ecológica Nacional, na sua redação atual).
- Portaria n.º 419/2012, de 20 de dezembro (Condições e requisitos para usos e ações nos n.ºs 2 e 3 do art. 20.º do RJREN).

2. RESERVA AGRÍCOLA NACIONAL (RAN):
- Decreto-Lei n.º 73/2009, de 31 de março (Regime jurídico da Reserva Agrícola Nacional, na sua redação atual).
- Portaria n.º 162/2011, de 18 de abril (Utilizações não agrícolas em áreas integradas na RAN).

3. REDE NATURA 2000:
- Decreto-Lei n.º 140/99, de 24 de abril (Na sua redação atual).
- Decreto-Lei n.º 169/2001, de 25 de maio (Na sua redação atual).

4. ORDENAMENTO DO TERRITÓRIO E URBANISMO:
- Decreto-Lei n.º 80/2015, de 14 de maio - RJIGT (Regime Jurídico dos Instrumentos de Gestão Territorial, na sua redação atual).
- Decreto-Lei n.º 555/99, de 16 de dezembro - RJUE (Regime Jurídico da Urbanização e Edificação, na sua redação atual).

5. REGIME CONTRAORDENACIONAL AMBIENTAL:
- Lei n.º 50/2006, de 29 de agosto (Lei Quadro das Contraordenações Ambientais, na sua redação atual).

REGRAS DE FORMATAÇÃO E RESPOSTA:
- Nomenclatura dos Diplomas: Deves referir-te sempre ao 1.º diploma legal indicado na lista anterior, seguido obrigatoriamente da expressão "na sua redação atual".
- Fundamentação e Citação: Todas as tuas afirmações, conclusões ou propostas de decisão devem ser rigorosamente sustentadas por citações fundamentadas quer nos documentos carregados, quer nos artigos específicos da legislação abordada.
- Tom: Mantém um tom estritamente formal, técnico, objetivo e juridicamente blindado.
"""

# --- 6. Funções de Custo e Upload ---
def calcular_custo_eur(prompt_tokens, candidates_tokens, taxa_eur, modelo="gemini-2.5-flash"):
    if "pro" in modelo:
        p_in = (prompt_tokens / 1_000_000) * 1.25
        p_out = (candidates_tokens / 1_000_000) * 5.00
    else:
        p_in = (prompt_tokens / 1_000_000) * 0.075
        p_out = (candidates_tokens / 1_000_000) * 0.30
    return (p_in + p_out) * taxa_eur

def enviar_para_google(client, uploaded_file):
    ext = os.path.splitext(uploaded_file.name)[1]
    temp_path = f"temp_{uuid.uuid4()}{ext}"
    
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    try:
        mime_type = "application/pdf" if uploaded_file.type == "application/pdf" else None
        g_file = client.files.upload(file=temp_path, config=types.UploadFileConfig(display_name=uploaded_file.name, mime_type=mime_type))
        
        while g_file.state.name == "PROCESSING":
            time.sleep(2)
            g_file = client.files.get(name=g_file.name)
            
        return g_file
    except Exception as e:
        st.error(f"Erro no upload para a Google API: {e}")
        raise e
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# --- 7. Interface Sidebar ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/144/artificial-intelligence.png", width=60)
    st.title("GORA Workspace")
    st.caption("Focado em Análise Confidencial e Fiscalização")
    st.markdown("---")
    
    api_key_env = os.environ.get("GEMINI_API_KEY", "")
    api_input = st.text_input("Chave API Gemini (Paga/Studio)", value=api_key_env, type="password")
    
    # Inicializar o cliente com a chave fornecida
    client = None
    if api_input:
        client = genai.Client(api_key=api_input)
    else:
        st.warning("Insira a sua chave API para começar.")

    st.markdown("### 📊 Controlo de Consumo")
    st.metric("Gasto Estimado (Acumulado)", f"{st.session_state.total_eur:.4f} €")
    st.caption(f"Tokens Totais: {st.session_state.total_tokens_session:,}")
    
    if st.button("🗑️ Limpar Histórico Total"):
        st.session_state.total_eur = 0.0
        st.session_state.total_tokens_session = 0
        st.session_state.all_chats = {"Conversa Padrão": {"model": "gemini-2.5-flash", "history": []}}
        st.session_state.chat_atual = "Conversa Padrão"
        db["total_eur"] = 0.0
        db["total_tokens"] = 0
        db["all_chats"] = st.session_state.all_chats
        salvar_dados(db)
        st.rerun()

# --- 8. Módulo Central do Chat ---
st.markdown(f"## 💬 Painel Central de Análise: {st.session_state.chat_atual}")

col_c1, col_c2, col_c3 = st.columns([2, 1, 1])
with col_c1:
    novo_chat = st.text_input("Nova sala de análise...")
    if st.button("➕ Criar Sala") and novo_chat:
        if novo_chat not in st.session_state.all_chats:
            st.session_state.all_chats[novo_chat] = {"model": "gemini-2.5-flash", "history": []}
            st.session_state.chat_atual = novo_chat
            db["all_chats"] = st.session_state.all_chats
            salvar_dados(db)
            st.rerun()
with col_c2:
    salas = list(st.session_state.all_chats.keys())
    escolha = st.selectbox("Mudar de Sala", salas, index=salas.index(st.session_state.chat_atual))
    if escolha != st.session_state.chat_atual:
        st.session_state.chat_atual = escolha
        st.rerun()
with col_c3:
    chat_context = st.session_state.all_chats[st.session_state.chat_atual]
    chat_context["model"] = st.selectbox(
        "Motor Gemini", 
        ["gemini-2.5-flash", "gemini-2.5-pro"], 
        index=0 if chat_context.get("model", "gemini-2.5-flash") == "gemini-2.5-flash" else 1
    )

st.markdown("---")

col_u1, col_u2 = st.columns(2)
with col_u1:
    st.markdown("### 🗂️ 1. Processos de Fiscalização")
    uploaded_files = st.file_uploader(
        "Submete os dossiers/ficheiros grandes a analisar (PDFs)", 
        accept_multiple_files=True, 
        key="processos"
    )
with col_u2:
    st.markdown("### 📄 2. Documento Tipo (Modelo Padrão)")
    uploaded_template = st.file_uploader(
        "Submete a minuta ou relatório de referência (Apenas 1 PDF)", 
        accept_multiple_files=False, 
        key="template"
    )

st.markdown("---")

for msg in chat_context["history"]:
    role = "user" if msg["role"] == "user" else "assistant"
    with st.chat_message(role):
        for part in msg["parts"]:
            if isinstance(part, str):
                st.markdown(part)
            elif hasattr(part, "text"):
                st.markdown(part.text)

if prompt := st.chat_input("Insira o comando ou questão sobre os processos anexados..."):
    if not client:
        st.error("Por favor, insira uma Chave API válida na barra lateral.")
    else:
        st.chat_message("user").markdown(prompt)
        
        payload_conteudo = []
        
        texto_historico = ""
        for h_msg in chat_context["history"]:
            prefixo_role = "UTILIZADOR ANTERIOR: " if h_msg["role"] == "user" else "ASSISTENTE ANTERIOR: "
            texto_msg = ""
            for p in h_msg["parts"]:
                if isinstance(p, str): texto_msg += p
                elif isinstance(p, dict) and "text" in p: texto_msg += p["text"]
                elif hasattr(p, "text"): texto_msg += p.text
            if texto_msg.strip():
                texto_historico += f"{prefixo_role}\n{texto_msg}\n---\n"
                
        if texto_historico:
            payload_conteudo.append(f"HISTÓRICO DA CONVERSA:\n{texto_historico}")
                
        if uploaded_files:
            with st.spinner("A indexar processos e dossiers na Google Cloud..."):
                for f in uploaded_files:
                    g_file_ref = enviar_para_google(client, f)
                    payload_conteudo.append(g_file_ref)
                    
        if uploaded_template:
            with st.spinner("A estruturar documento tipo de referência..."):
                g_template_ref = enviar_para_google(client, uploaded_template)
                payload_conteudo.append("NOTA CRÍTICA DE FORMATO: O documento em anexo representa o teu DOCUMENTO TIPO/MODELO. Deves mimetizar de forma estrita e absoluta a sua estrutura, tom e divisões.")
                payload_conteudo.append(g_template_ref)
                
        payload_conteudo.append(f"COMANDO ATUAL DO UTILIZADOR:\n{prompt}")

        with st.chat_message("assistant"):
            try:
                # Chamada com o SDK novo, injetando Instruções de Sistema e Grounding (Google Search)
                response = client.models.generate_content(
                    model=chat_context["model"],
                    contents=payload_conteudo,
                    config=types.GenerateContentConfig(
                        system_instruction=INSTRUCOES_SISTEMA,
                        # Ativação da Pesquisa Web em Tempo Real
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        temperature=0.2
                    )
                )
                
                u = response.usage_metadata
                custo = calcular_custo_eur(u.prompt_token_count, u.candidates_token_count, st.session_state.taxa_cambio, chat_context["model"])
                
                st.session_state.total_eur += custo
                st.session_state.total_tokens_session += u.total_token_count
                
                chat_context["history"].append({"role": "user", "parts": [prompt]})
                chat_context["history"].append({"role": "model", "parts": [response.text]})
                
                db["total_eur"] = st.session_state.total_eur
                db["total_tokens"] = st.session_state.total_tokens_session
                db["all_chats"] = st.session_state.all_chats
                salvar_dados(db)

                # Apresentar Resposta Principal
                st.markdown(response.text)

                # Apresentar Fontes da Pesquisa Web (se aplicável)
                if response.candidates and response.candidates[0].grounding_metadata and response.candidates[0].grounding_metadata.grounding_chunks:
                    st.markdown("---")
                    st.markdown("### 📚 Fontes Web Consultadas (Grounding):")
                    chunks = response.candidates[0].grounding_metadata.grounding_chunks
                    for chunk in chunks:
                        if chunk.web:
                            st.markdown(f"- [{chunk.web.title}]({chunk.web.uri})")

                st.rerun()
            except Exception as e:
                st.error(f"Erro na geração da análise: {e}")
