import streamlit as st

st.set_page_config(
    page_title="Hub de Automação",
    page_icon="🛠️",
    layout="centered"
)

st.title("🛠️ Meu Hub de Scripts e Automações")
st.write("Bem-vindo ao seu painel central! Clique no quadro da ferramenta desejada abaixo:")

st.markdown("---")

col1, col2 = st.columns(2)

# Função para redirecionar
def ir_para_romaneios():
    st.switch_page("pages/romaneios.py")

with col1:
    # Criamos um container com borda que funciona como um botão clicável inteiro
    with st.container(border=True):
        st.subheader("📦 Processador de Romaneios")
        st.write("Lê PDFs de romaneios, cruza com a UF e baixa as notas do Google Drive.")
        
        # Botão sutil dentro do card que ocupa a largura e ativa a função de clique
        if st.button("Abrir Romaneios", key="btn_romaneios", use_container_width=True):
            ir_para_romaneios()

with col2:
    with st.container(border=True):
        st.subheader("🚀 Próximo Roteiro")
        st.write("Espaço reservado para o seu próximo roteiro de automação no futuro.")
        st.caption("Em breve...")
        
        # Botão desativado para futuros scripts
        st.button("Em Breve", key="btn_futuro", disabled=True, use_container_width=True)