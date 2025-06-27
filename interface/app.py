# interface/app.py
import streamlit as st
import sys
import os

# Adiciona o diretório raiz ao sys.path para importar bia_main
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bia_main import rodar_atendimento

st.set_page_config(page_title="ImobIA - Cardoso Imóveis", layout="centered")
st.title("🤖 ImobIA - Cardoso Imóveis")

# --- GERENCIAMENTO DE ESTADO ---
# A conversa começa vazia. O usuário inicia.
if "estado_conversa" not in st.session_state:
    st.session_state.estado_conversa = {"nome": None, "cidade": None, "assunto": None, "agente_atual": None}
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []

# Exibe o histórico de mensagens que já existem
for mensagem in st.session_state.mensagens:
    with st.chat_message(mensagem["role"]):
        st.markdown(mensagem["content"])

# Obtém a entrada do usuário para iniciar ou continuar a conversa
if entrada_usuario := st.chat_input("Olá! Como posso te ajudar hoje?"):
    # Adiciona a mensagem do usuário ao histórico e exibe
    st.session_state.mensagens.append({"role": "user", "content": entrada_usuario})
    with st.chat_message("user"):
        st.markdown(entrada_usuario)

    # Roda a lógica de atendimento
    estado_atualizado, proxima_pergunta = rodar_atendimento(
        st.session_state.estado_conversa,
        entrada_usuario
    )
    
    # Atualiza o estado da conversa
    st.session_state.estado_conversa = estado_atualizado
    
    # Adiciona a resposta do assistente ao histórico e exibe
    with st.chat_message("assistant"):
        st.markdown(proxima_pergunta)
    st.session_state.mensagens.append({"role": "assistant", "content": proxima_pergunta})
    
    # Recarrega a página para garantir a consistência da exibição
    st.rerun()