from datetime import datetime
import io
import json
import os
import re
import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
import streamlit_authenticator as stauth

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Extrator de Cargas de XMLs", page_icon="📊", layout="wide"
)

# --- VALIDAÇÃO DE SEGURANÇA DA SESSÃO ---
authentication_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")

if not authentication_status:
  st.error(
      "🔒 Acesso Negado! Por favor, faça o login na página principal do Hub"
      " primeiro."
  )
  if st.button("Ir para o Login"):
    st.switch_page("app.py")
  st.stop()

st.sidebar.markdown(f"👤 **Logado como:** {name}")

st.title("📊 Extrator de Carga Origem e Destino de XMLs")
st.write(
    "Faça o upload dos arquivos XML das notas fiscais para extrair os números das"
    " notas e as respectivas cargas das observações de forma automática."
)

# Upload de múltiplos arquivos XML
uploaded_files = st.file_uploader(
    "Selecione os arquivos XML",
    type=["xml"],
    accept_multiple_files=True,
    key="uploader_extrator_xml",
)


def processar_xmls_bytes(files):
  dados = []
  ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

  for uploaded_file in files:
    try:
      xml_bytes = uploaded_file.read()
      root = ET.fromstring(xml_bytes)

      # 1. Extrai o Número da Nota Fiscal (nNF)
      n_nf_elem = root.find(".//nfe:nNF", ns)
      n_nota = n_nf_elem.text if n_nf_elem is not None else "Não encontrado"

      # 2. Busca o texto de observação/fisco
      inf_fisco = root.find(".//nfe:infAdFisco", ns)
      inf_cpl = root.find(".//nfe:infCpl", ns)

      texto_obs = ""
      if inf_fisco is not None and inf_fisco.text:
        texto_obs += inf_fisco.text + " "
      if inf_cpl is not None and inf_cpl.text:
        texto_obs += inf_cpl.text

      # 3. Lógica para extrair Carga Origem e Carga Destino
      carga_origem = "Não identificada"
      carga_destino = "Não identificada"

      matches_carga = re.findall(r"carga[:\s]*(\d+)", texto_obs, re.IGNORECASE)

      if len(matches_carga) >= 2:
        carga_origem = matches_carga[0]
        carga_destino = matches_carga[1]
      elif len(matches_carga) == 1:
        carga_origem = matches_carga[0]
        carga_destino = "Apenas uma carga"

      dados.append({
          "Arquivo": uploaded_file.name,
          "Numero de Nota": n_nota,
          "Carga Origem": carga_origem,
          "Carga Destino": carga_destino,
      })

    except Exception as e:
      st.error(f"Erro ao processar o arquivo {uploaded_file.name}: {e}")

  return pd.DataFrame(dados)


if uploaded_files:
  if st.button("🚀 Processar e Gerar Relatório", type="primary"):
    with st.spinner("Processando arquivos XML..."):
      df_resultado = processar_xmls_bytes(uploaded_files)

    if not df_resultado.empty:
      st.success("✨ Processamento concluído com sucesso!")
      st.subheader("📊 Prévia do Relatório")
      st.dataframe(df_resultado, use_container_width=True)

      # Prepara o arquivo Excel em memória para download
      output = io.BytesIO()
      with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_resultado.to_excel(writer, index=False)
      excel_data = output.getvalue()

      nome_arquivo_excel = (
          f"resultado_cargas_notas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
      )

      st.download_button(
          label="📥 Baixar Planilha Excel (XLSX)",
          data=excel_data,
          file_name=nome_arquivo_excel,
          mime=(
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          ),
          use_container_width=True,
      )
    else:
      st.warning("⚠️ Nenhum dado válido foi extraído dos arquivos enviados.")
