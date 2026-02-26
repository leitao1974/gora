import streamlit as st
import sys
from io import StringIO

st.set_page_config(page_title="IA Chat & Lab", layout="wide")

st.title("🚀 AI Chat + Python Lab")

# Criando as abas
tab1, tab2 = st.tabs(["💬 Chat IA", "💻 Python Lab (Estilo Colab)"])

with tab1:
    st.header("Chat com IA")
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Exibir histórico
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Input do usuário
    if prompt := st.chat_input("Como posso ajudar?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Resposta simulada (Aqui você conectaria a API do Gemini/OpenAI)
        with st.chat_message("assistant"):
            response = f"Você disse: '{prompt}'. (Conecte sua API Key para respostas reais!)"
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

with tab2:
    st.header("Interpretador Python")
    st.info("Digite seu código abaixo e pressione Ctrl+Enter ou clique em Executar.")
    
    # Área de entrada de código
    code_input = st.text_area("Célula de Código", height=200, value='print("Olá do Streamlit!")\n\n# Tente somar: \na = 10\nb = 20\nprint(f"Resultado: {a + b}")')
    
    if st.button("▶ Executar"):
        # Redirecionar o output para capturar o print()
        old_stdout = sys.stdout
        redirected_output = sys.stdout = StringIO()
        
        try:
            # Executa o código
            exec(code_input)
            sys.stdout = old_stdout
            result = redirected_output.getvalue()
            
            st.subheader("Saída:")
            st.code(result if result else "Código executado com sucesso (sem retorno).")
        except Exception as e:
            sys.stdout = old_stdout
            st.error(f"Erro no código: {e}")