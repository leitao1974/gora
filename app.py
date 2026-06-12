import streamlit as st
import google.generativeai as genai
import pandas as pd
import numpy as np
import sys
import os
import requests
import matplotlib.pyplot as plt
import plotly.express as px
from io import StringIO
import uuid
import json
import time
from docx import Document
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

# --- 3. CSS Vanguardista ---
st.markdown("""
    <style>
    .stApp { background-color: #0b0f19; color: #e2e8f0; }
    [data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #1f2937; }
    .stButton>button { background: linear-gradient(135deg, #3b82f6, #8b5cf6); color: white; border: none; border-radius: 8px; padding: 0.5rem 1rem; font-weight: 600; transition: all 0.3s; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4); }
    .chat-box { background-color: #1f2937; border-radius: 12px; padding: 1.5rem; border: 1px solid #374151; margin-bottom: 1rem; }
    h1, h2, h3 { color: #f8fafc; font-family: 'Inter', sans-serif; }
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

# --- 5. Funções Auxiliares (Preços e Uploads) ---
def calcular_custo_eur(prompt_tokens, candidates_tokens, taxa_eur, modelo="gemini-2.5-pro"):
    # Configuração de preços padrão (ajustável para planos pagos se necessário)
    if "flash" in modelo:
        p_in = (prompt_tokens / 1_000_000) * 0.075
        p_out = (candidates_tokens / 1_000_000) * 0.30
    else:
        p_in = (prompt_tokens / 1_000_000) * 1.25
        p_out = (candidates_tokens / 1_000_000) * 5.00
    return (p_in + p_out) * taxa_eur

def enviar_para_google(uploaded_file):
    """
    Função atualizada para lidar com ficheiros grandes (Ex: PDFs de 95MB)
    evitando o erro HTTP 401 Unauthorized através da definição explícita do Mime Type
    e isolamento de contexto de rede.
    """
    # Preservar a extensão original do ficheiro para processamento correto na Google
    ext = os.path.splitext(uploaded_file.name)[1]
    temp_path = f"temp_{uuid.uuid4()}{ext}"
    
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    try:
        # Forçar a identificação do tipo MIME para ficheiros grandes (especialmente PDFs)
        mime_type = None
        if uploaded_file.type == "application/pdf":
            mime_type = "application/pdf"
        elif uploaded_file.type in ["image/png", "image/jpeg", "image/webp"]:
            mime_type = uploaded_file.type
            
        # Realiza o upload utilizando o chunking correto do SDK para ficheiros pesados
        g_file = genai.upload_file(path=temp_path, display_name=uploaded_file.name, mime_type=mime_type)
        
        # Aguardar o processamento interno da Google (essencial para vídeos e PDFs gigantes)
        while g_file.state.name == "PROCESSING":
            time.sleep(2)
            g_file = genai.get_file(g_file.name)
            
        return g_file
    except Exception as e:
        st.error(f"Erro ao processar upload para a Google API: {e}")
        raise e
    finally:
        # Segurança: Garante que o ficheiro temporário de 95MB é apagado do servidor Streamlit
        if os.path.exists(temp_path):
            os.remove(temp_path)

# --- 6. Interface Sidebar ---
with st.sidebar:
    st.image("https://img.icons8.com/fluent/96/000000/artificial-intelligence.png", width=60)
    st.markdown("# GORA Intelligence")
    st.markdown("---")
    
    # Gerador de Chave API Dinâmica
    api_key_env = os.environ.get("GEMINI_API_KEY", "")
    api_input = st.text_input("Chave API Gemini", value=api_key_env, type="password")
    if api_input:
        genai.configure(api_key=api_input)
    else:
        st.warning("Insira a sua chave API para começar.")

    st.markdown("### 📊 Métrica de Consumo")
    st.metric("Gasto Estimado (Sessão)", f"{st.session_state.total_eur:.4f} €")
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

    st.markdown("---")
    menu = st.radio("Navegação", ["💬 Chat Principal", "💻 GORA Lab", "📊 Business Analytics"])

# --- 7. Módulo Chat Principal ---
if menu == "💬 Chat Principal":
    st.markdown(f"## 💬 Sala: {st.session_state.chat_atual}")
    
    # Gestão de Múltiplos Chats
    col_c1, col_c2 = st.columns([3, 1])
    with col_c1:
        novo_chat = st.text_input("Criar nova sala de conversa...")
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

    chat_context = st.session_state.all_chats[st.session_state.chat_atual]
    
    # Seleção de Modelo para este chat específico
    chat_context["model"] = st.selectbox(
        "Motor de Inteligência", 
        ["gemini-2.5-pro", "gemini-2.5-flash"], 
        index=0 if chat_context.get("model", "gemini-2.5-pro") == "gemini-2.5-pro" else 1
    )

    # Upload Multimodal Avançado
    uploaded_files = st.file_uploader("Anexar Documentos ou Ficheiros de Grande Porte (PDF, Imagens, Vídeos)", accept_multiple_files=True)
    
    # Renderização do Histórico Existente
    for msg in chat_context["history"]:
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            # Filtrar e mostrar apenas o texto guardado para evitar lixo visual no histórico
            for part in msg["parts"]:
                if isinstance(part, str):
                    st.markdown(part)
                elif hasattr(part, "text"):
                    st.markdown(part.text)

    # Input do Utilizador
    if prompt := st.chat_input("Envie uma mensagem ou questione os documentos anexados..."):
        st.chat_message("user").markdown(prompt)
        
        conteudo = []
        
        # Processamento de Anexos
        if uploaded_files:
            with st.spinner("A carregar e a processar os anexos na infraestrutura Google..."):
                for f in uploaded_files:
                    if f.type in ["image/png", "image/jpeg", "image/webp"]:
                        conteudo.append(Image.open(f))
                    else:
                        # PDFs e outros ficheiros pesados (como os teus 95MB) entram aqui
                        g_file_ref = enviar_para_google(f)
                        conteudo.append(g_file_ref)
        
        conteudo.append(prompt)

        # Chamada à API
        with st.chat_message("assistant"):
            try:
                model_instance = genai.GenerativeModel(chat_context["model"])
                
                # Reconstruir histórico no formato correto do SDK do Gemini
                sdk_history = []
                for h_msg in chat_context["history"]:
                    sdk_history.append({
                        "role": h_msg["role"],
                        "parts": [p.text if hasattr(p, "text") else p for p in h_msg["parts"]]
                    })
                
                chat_sess = model_instance.start_chat(history=sdk_history)
                response = chat_sess.send_message(conteudo)
                
                # Atualizar Estado e Base de Dados de Custos
                u = response.usage_metadata
                custo = calcular_custo_eur(u.prompt_token_count, u.candidates_token_count, st.session_state.taxa_cambio, chat_context["model"])
                
                st.session_state.total_eur += custo
                st.session_state.total_tokens_session += u.total_token_count
                
                # Adicionar à persistência local em formato serializável (String)
                chat_context["history"].append({"role": "user", "parts": [prompt]})
                chat_context["history"].append({"role": "model", "parts": [response.text]})
                
                # Sincronizar com a Base de Dados JSON
                db["total_eur"] = st.session_state.total_eur
                db["total_tokens"] = st.session_state.total_tokens_session
                db["all_chats"] = st.session_state.all_chats
                salvar_dados(db)

                st.markdown(response.text)
                st.rerun()
            except Exception as e:
                st.error(f"Erro na geração da resposta: {e}")

# --- 8. Módulo Lab ---
elif menu == "💻 GORA Lab":
    st.markdown("## 💻 GORA Python Lab")
    code = st.text_area("Script Python", height=300)
    if st.button("⚡ Executar"):
        old_stdout = sys.stdout
        redirected_output = sys.stdout = StringIO()
        try:
            exec(code)
            sys.stdout = old_stdout
            st.success("Executado com sucesso!")
            st.code(redirected_output.getvalue())
        except Exception as e:
            sys.stdout = old_stdout
            st.error(f"Erro na execução: {e}")

# --- 9. Módulo Business Analytics ---
elif menu == "📊 Business Analytics":
    st.markdown("## 📊 Painel Business Analytics")
    uploaded_csv = st.file_uploader("Carregue dados operacionais (CSV ou Excel)", type=["csv", "xlsx"])
    
    if uploaded_csv:
        if uploaded_csv.name.endswith(".csv"):
            df = pd.read_csv(uploaded_csv)
        else:
            df = pd.read_excel(uploaded_csv)
            
        st.dataframe(df.head())
        
        col1, col2 = st.columns(2)
        columns_list = df.columns.tolist()
        
        with col1:
            x_axis = st.selectbox("Eixo X (Temporal/Categorias)", columns_list)
        with col2:
            y_axis = st.selectbox("Eixo Y (Métricas Numéricas)", columns_list)
            
        chart_type = st.selectbox("Tipo de Gráfico", ["Linhas", "Barras", "Dispersão"])
        
        if chart_type == "Linhas":
            fig = px.line(df, x=x_axis, y=y_axis, title=f"{y_axis} ao longo de {x_axis}")
        elif chart_type == "Barras":
            fig = px.bar(df, x=x_axis, y=y_axis, title=f"Distribuição de {y_axis}")
        else:
            fig = px.scatter(df, x=x_axis, y=y_axis, title=f"Correlação: {x_axis} vs {y_axis}")
            
        st.plotly_chart(fig, use_container_width=True)



