import streamlit as st
import google.generativeai as genai
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

# --- 3. Interface Visual Premium (Modo Escuro Focado) ---
st.markdown("""
    <style>
    /* Fundo Geral da Aplicação */
    .stApp { 
        background-color: #0b0f19 !important; 
        color: #f1f5f9 !important; 
        font-family: 'Inter', sans-serif; 
    }
    
    /* Configuração Estrita da Barra Lateral (Sidebar) */
    [data-testid="stSidebar"] { 
        background-color: #111827 !important; 
        border-right: 1px solid #1f2937 !important; 
    }
    
    /* Forçar contraste máximo de textos e etiquetas na Sidebar */
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] div { 
        color: #f1f5f9 !important; 
    }
    
    /* Títulos Principais */
    h1, h2, h3 { 
        color: #f8fafc !important; 
        font-weight: 800 !important; 
        letter-spacing: -0.5px; 
    }
    
    /* Estilização das Caixas de Mensagem do Chat */
    .stChatMessage {
        background-color: #1f2937 !important; 
        border: 1px solid #374151 !important;
        border-radius: 12px !important; 
        margin-bottom: 15px; 
        padding: 20px !important;
    }
    
    /* Estilização dos Botões de Ação Dinâmicos */
    .stButton>button { 
        background: linear-gradient(135deg, #3b82f6, #8b5cf6) !important; 
        color: #ffffff !important; 
        border: none !important; 
        border-radius: 8px !important; 
        padding: 0.5rem 1rem !important; 
        font-weight: 600 !important; 
        transition: all 0.3s !important; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
    }
    .stButton>button:hover { 
        transform: translateY(-1px) !important; 
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4) !important; 
    }
    
    /* Botão de Reset na Sidebar (Vermelho para Aviso) */
    div[data-testid="stSidebar"] .stButton>button {
        background: #ef4444 !important;
    }
    div[data-testid="stSidebar"] .stButton>button:hover {
        box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4) !important;
    }
    
    /* Input Boxes e Selectores adaptados para o Modo Escuro */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #1f2937 !important;
        color: #f1f5f9 !important;
        border: 1px solid #374151 !important;
    }
    
    /* Destaque visual das caixas de upload */
    .stFileUploader {
        background-color: #111827 !important;
        border: 1px dashed #374151 !important;
        border-radius: 8px !important;
        padding: 10px !important;
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
    st.session_state.all_chats[st.session_state.chat_atual] = {"model": "gemini-2.5-pro", "history": []}

# --- 5. Instruções de Sistema (Legislação Estrita) ---
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
- Nomenclatura dos Diplomas: Deves referir-te sempre ao 1.º diploma legal indicado na lista anterior, seguido obrigatoriamente da expressão "na sua redação atual" (Exemplo: "... nos termos do Decreto-Lei n.º 166/2008, de 22 de agosto, na sua redação atual..."). Não deves listar as leis alteradoras intermédias no texto final, usa apenas a fórmula de redação atual para manter o texto limpo e conciso.
- Fundamentação e Citação: Todas as tuas afirmações, conclusões ou propostas de decisão devem ser rigorosamente sustentadas por citações fundamentadas quer nos documentos carregados pelo utilizador (processos), quer nos artigos específicos da legislação abordada.
- Tom: Mantém um tom estritamente formal, técnico, objetivo e juridicamente blindado. Se o utilizador fornecer um "Documento Tipo", adota rigorosamente a estrutura, as divisões de secções e o estilo de escrita desse modelo.
- Universalidade: Embora estejas otimizado para fiscalização territorial, continuas a ser um assistente universal abrangente, capaz de ajudar em lógica, programação ou redação geral caso solicitado.
"""

# --- 6. Funções de Custo e Upload (Chunking de Grande Porte) ---
def calcular_custo_eur(prompt_tokens, candidates_tokens, taxa_eur, modelo="gemini-2.5-pro"):
    if "flash" in modelo:
        p_in = (prompt_tokens / 1_000_000) * 0.075
        p_out = (candidates_tokens / 1_000_000) * 0.30
    else:
        p_in = (prompt_tokens / 1_000_000) * 1.25
        p_out = (candidates_tokens / 1_000_000) * 5.00
    return (p_in + p_out) * taxa_eur

def enviar_para_google(uploaded_file):
    ext = os.path.splitext(uploaded_file.name)[1]
    temp_path = f"temp_{uuid.uuid4()}{ext}"
    
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    try:
        mime_type = "application/pdf" if uploaded_file.type == "application/pdf" else None
        g_file = genai.upload_file(path=temp_path, display_name=uploaded_file.name, mime_type=mime_type)
        
        while g_file.state.name == "PROCESSING":
            time.sleep(2)
            g_file = genai.get_file(g_file.name)
            
        return g_file
    except Exception as e:
        st.error(f"Erro no upload para a Google API: {e}")
        raise e
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# --- 7. Interface Sidebar ---
with st.sidebar:
    st.image("https://img.icons8.com/fluent/96/000000/artificial-intelligence.png", width=60)
    st.markdown("# GORA Intelligence")
    st.caption("Focado em Análise Confidencial e Fiscalização")
    st.markdown("---")
    
    api_key_env = os.environ.get("GEMINI_API_KEY", "")
    api_input = st.text_input("Chave API Gemini (Paga/Studio)", value=api_key_env, type="password")
    if api_input:
        genai.configure(api_key=api_input)
    else:
        st.warning("Insira a sua chave API para começar.")

    st.markdown("### 📊 Controlo de Consumo")
    st.metric("Gasto Estimado (Acumulado)", f"{st.session_state.total_eur:.4f} €")
    st.metric("Tokens Consumidos", f"{st.session_state.total_tokens_session:,}")
    
    if st.button("🗑️ Limpar Histórico Total"):
        st.session_state.total_eur = 0.0
        st.session_state.total_tokens_session = 0
        st.session_state.all_chats = {"Conversa Padrão": {"model": "gemini-2.5-pro", "history": []}}
        st.session_state.chat_atual = "Conversa Padrão"
        db["total_eur"] = 0.0
        db["total_tokens"] = 0
        db["all_chats"] = st.session_state.all_chats
        salvar_dados(db)
        st.rerun()

# --- 8. Módulo Central do Chat ---
st.markdown(f"## 💬 Painel Central de Análise: {st.session_state.chat_atual}")

# Seleção de Salas e Motor de Inteligência
col_c1, col_c2, col_c3 = st.columns([2, 1, 1])
with col_c1:
    novo_chat = st.text_input("Nova sala de análise...")
    if st.button("➕ Criar Sala") and novo_chat:
        if novo_chat not in st.session_state.all_chats:
            st.session_state.all_chats[novo_chat] = {"model": "gemini-2.5-pro", "history": []}
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
        ["gemini-2.5-pro", "gemini-2.5-flash"], 
        index=0 if chat_context.get("model", "gemini-2.5-pro") == "gemini-2.5-pro" else 1
    )

st.markdown("---")

# Duas colunas para gestão de documentos carregados na sessão
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

# Renderizar Histórico Existente
for msg in chat_context["history"]:
    role = "user" if msg["role"] == "user" else "assistant"
    with st.chat_message(role):
        for part in msg["parts"]:
            if isinstance(part, str):
                st.markdown(part)
            elif hasattr(part, "text"):
                st.markdown(part.text)

# Janela de Comando Central (Chat Input)
if prompt := st.chat_input("Insira o comando ou questão sobre os processos anexados..."):
    st.chat_message("user").markdown(prompt)
    
    conteudo = []
    
    # Processar os múltiplos ficheiros de processos (como o de 95MB)
    if uploaded_files:
        with st.spinner("A indexar processos e dossiers de fiscalização na Google Cloud..."):
            for f in uploaded_files:
                g_file_ref = enviar_para_google(f)
                conteudo.append(g_file_ref)
                
    # Processar o documento modelo de referência, se existir
    if uploaded_template:
        with st.spinner("A estruturar documento tipo/modelo de referência..."):
            g_template_ref = enviar_para_google(uploaded_template)
            conteudo.append("NOTA DO SISTEMA: O documento a seguir é o DOCUMENTO TIPO/MODELO. Deves mimetizar a sua estrutura, estilo, secções e tom em qualquer relatório solicitado.")
            conteudo.append(g_template_ref)
            
    conteudo.append(prompt)

    with st.chat_message("assistant"):
        try:
            # Inicializar o modelo já injetando as Instruções de Legislação do Sistema
            model_instance = genai.GenerativeModel(
                model_name=chat_context["model"],
                system_instruction=INSTRUCOES_SISTEMA
            )
            
            # Saneamento e Higienização Estrita do Histórico (Evita erro 400)
            sdk_history = []
            for h_msg in chat_context["history"]:
                texto_limpo = ""
                for p in h_msg["parts"]:
                    if isinstance(p, str):
                        texto_limpo += p
                    elif isinstance(p, dict) and "text" in p:
                        texto_limpo += p["text"]
                    elif hasattr(p, "text"):
                        texto_limpo += p.text
                
                if texto_limpo.strip():
                    sdk_history.append({
                        "role": "user" if h_msg["role"] == "user" else "model",
                        "parts": [texto_limpo]
                    })
            
            chat_sess = model_instance.start_chat(history=sdk_history)
            response = chat_sess.send_message(conteudo)
            
            # Cálculo de Métricas da Sessão Paga
            u = response.usage_metadata
            custo = calcular_custo_eur(u.prompt_token_count, u.candidates_token_count, st.session_state.taxa_cambio, chat_context["model"])
            
            st.session_state.total_eur += custo
            st.session_state.total_tokens_session += u.total_token_count
            
            # Guardar apenas strings no JSON local para evitar quebras de serialização
            chat_context["history"].append({"role": "user", "parts": [prompt]})
            chat_context["history"].append({"role": "model", "parts": [response.text]})
            
            db["total_eur"] = st.session_state.total_eur
            db["total_tokens"] = st.session_state.total_tokens_session
            db["all_chats"] = st.session_state.all_chats
            salvar_dados(db)

            st.markdown(response.text)
            st.rerun()
        except Exception as e:
            st.error(f"Erro na geração da análise: {e}")


