from datetime import datetime
import io
import re
import unicodedata
import cv2
import numpy as np
import pandas as pd
import pytesseract
import streamlit as st

st.set_page_config(
    page_title="Processador de Canhotos", page_icon="📄", layout="wide"
)

st.title("📄 Processador Inteligente de Canhotos (DANFE & DACTE)")
st.write(
    "Faça o upload das imagens dos canhotos abaixo para extrair os números das"
    " notas fiscais/CT-es e gerar o relatório em Excel."
)

uploaded_files = st.file_uploader(
    "Selecione as imagens dos canhotos",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
)


def extrair_dados_texto(texto):
  """Função rápida que analisa o texto extraído e valida chaves SEFAZ"""
  txt_num = (
      texto.upper()
      .replace("O", "0")
      .replace("I", "1")
      .replace("L", "1")
      .replace("S", "5")
      .replace("B", "8")
  )
  chunks = re.split(r"[^\d\s\.\-]", txt_num)

  chave_cte = None
  chave_nfe = None

  for chunk in chunks:
    digitos = re.sub(r"\D", "", chunk)
    if len(digitos) >= 44:
      for i in range(len(digitos) - 43):
        chave = digitos[i : i + 44]
        uf = int(chave[0:2]) if chave[0:2].isdigit() else 0
        mod = chave[20:22]

        if 11 <= uf <= 53:
          if mod == "57":
            chave_cte = chave
          elif mod in ["55", "65"]:
            chave_nfe = chave

  if chave_cte:
    return "CTE", str(int(chave_cte[25:34]))
  if chave_nfe:
    return "NOTA", str(int(chave_nfe[25:34]))

  matches_n = re.findall(r"N[ºo\.\s]*(\d[\d.\-\s]{5,10}\d)", texto, re.IGNORECASE)
  for m in matches_n:
    num_limpo = re.sub(r"\D", "", m)
    if 6 <= len(num_limpo) <= 9:
      return "NOTA", str(int(num_limpo))

  return None, None


def processar_imagem_bytes(file_bytes):
  """Processa a imagem a partir dos bytes recebidos no Streamlit"""
  nparr = np.frombuffer(file_bytes, np.uint8)
  img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
  if img is None:
    return "DESCONHECIDO", None

  rotacoes = [0, 180, 90, 270]
  for rotacao in rotacoes:
    img_proc = img
    if rotacao == 180:
      img_proc = cv2.rotate(img, cv2.ROTATE_180)
    elif rotacao == 90:
      img_proc = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    elif rotacao == 270:
      img_proc = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)

    h, w = img_proc.shape[:2]
    if w > 1200:
      ratio = 1200 / w
      img_proc = cv2.resize(
          img_proc, (1200, int(h * ratio)), interpolation=cv2.INTER_AREA
      )

    gray = cv2.cvtColor(img_proc, cv2.COLOR_BGR2GRAY)
    texto = pytesseract.image_to_string(gray, lang="por")

    tipo, valor = extrair_dados_texto(texto)
    if tipo and valor:
      return tipo, valor

  return "DESCONHECIDO", None


if uploaded_files:
  if st.button("🚀 Processar Canhotos", type="primary"):
    dados_relatorio = []
    barra_progresso = st.progress(0)
    total_arquivos = len(uploaded_files)

    for i, uploaded_file in enumerate(uploaded_files):
      file_bytes = uploaded_file.read()
      tipo, valor = processar_imagem_bytes(file_bytes)

      nota_fiscal = ""
      cte = ""
      ocorrencia = "Sucesso"

      if tipo == "NOTA" and valor:
        nota_fiscal = valor
      elif tipo == "CTE":
        if valor != "Desconhecido":
          cte = valor
        else:
          ocorrencia = "CT-e identificado, mas com número ilegível"
      else:
        ocorrencia = "Não identificado / Verso"

      dados_relatorio.append({
          "Nome arquivo": uploaded_file.name,
          "nota fiscal": nota_fiscal,
          "cte": cte,
          "ocorrencia": ocorrencia,
      })

      barra_progresso.progress((i + 1) / total_arquivos)

    df_relatorio = pd.DataFrame(dados_relatorio)

    st.success("✨ Processamento concluído com sucesso!")
    st.subheader("📊 Prévia do Relatório")
    st.dataframe(df_relatorio, use_container_width=True)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
      df_relatorio.to_excel(writer, index=False)
    excel_data = output.getvalue()

    data_hora_atual = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo_excel = f"relatorio_notas_{data_hora_atual}.xlsx"

    st.download_button(
        label="📥 Baixar Planilha Excel (XLSX)",
        data=excel_data,
        file_name=nome_arquivo_excel,
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        use_container_width=True,
    )
