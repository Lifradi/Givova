col1, col2 = st.columns(2)


    def ir_para_romaneios():
      st.switch_page("pages/romaneios.py")


    def ir_para_canhotos():
      st.switch_page("pages/canhotos.py")


    with col1:
      with st.container(border=True):
        st.subheader("📦 Processador de Romaneios")
        st.write(
            "Lê PDFs de romaneios, cruza com a UF e baixa as notas do Google"
            " Drive."
        )

        if st.button(
            "Abrir Romaneios", key="btn_romaneios", use_container_width=True
        ):
          ir_para_romaneios()

    with col2:
      with st.container(border=True):
        st.subheader("📄 Processador de Canhotos")
        st.write(
            "Lê imagens de DANFE/DACTE, extrai as notas e gera a planilha."
        )

        if st.button(
            "Abrir Canhotos", key="btn_canhotos", use_container_width=True
        ):
          ir_para_canhotos()
