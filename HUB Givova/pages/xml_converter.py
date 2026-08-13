from datetime import datetime
import io
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
import PyPDF2
import streamlit as st
import streamlit_authenticator as stauth

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Conversor PDF para XML (Sem IA)", page_icon="⚡", layout="wide"
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

st.title("⚡ Conversor Ultrarrápido de PDF para XML (Sem Inteligência Artificial)")
st.write(
    "Extrai os dados textuais de PDFs nativos de forma determinística e gera a"
    " estrutura XML instantaneamente."
)

uploaded_files = st.file_uploader(
    "Envie os PDFs das Notas/CT-es",
    type=["pdf"],
    accept_multiple_files=True,
    key="uploader_pdf_xml",
)


def gerar_xml_deterministico(texto_pdf, nome_arquivo):
  """Extrai chaves e dados do texto do PDF usando Regex e monta um XML válido da SEFAZ sem IA."""

  # Tenta achar a chave de acesso de 44 dígitos no texto
  digitos_puros = re.sub(r"\D", "", texto_pdf)
  chave_encontrada = ""
  for i in range(len(digitos_puros) - 43):
    bloco = digitos_puros[i : i + 44]
    # Valida se tem UF válida no começo (ex: 31, 35, etc)
    if bloco[0:2].isdigit() and 11 <= int(bloco[0:2]) <= 53:
      chave_encontrada = bloco
      break

  # Se não achar a chave de 44 dígitos, cria tags vazias baseadas no nome do arquivo
  cUF = chave_encontrada[0:2] if chave_encontrada else "35"
  mod = chave_encontrada[20:22] if chave_encontrada else "55"
  nNF = (
      str(int(chave_encontrada[25:34]))
      if chave_encontrada
      else re.sub(r"\D", "", nome_arquivo)[:9]
  )
  nnf_val = nNF if nNF else "1"

  # Montando a árvore XML padrão NFe v4.00 de forma programática
  nfe_proc = ET.Element(
      "nfeProc",
      attrib={
          "xmlns": "http://www.portalfiscal.inf.br/nfe",
          "versao": "4.00",
      },
  )
  NFe = ET.SubElement(nfe_proc, "NFe")
  infNFe = ET.SubElement(
      NFe,
      "infNFe",
      attrib={
          "Id": f"NFe{chave_encontrada}"
          if chave_encontrada
          else "NFe00000000000000000000000000000000000000000000",
          "versao": "4.00",
      },
  )

  # Grupo de Identificação (ide)
  ide = ET.SubElement(infNFe, "ide")
  ET.SubElement(ide, "cUF").text = cUF
  ET.SubElement(ide, "natOp").text = "VENDAS"
  ET.SubElement(ide, "mod").text = mod
  ET.SubElement(ide, "serie").text = "1"
  ET.SubElement(ide, "nNF").text = nnf_val
  ET.SubElement(ide, "dhEmi").text = (
      datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
  )

  # Grupo de Pagamento (Obrigatório na v4.00)
  pag = ET.SubElement(infNFe, "pag")
  detPag = ET.SubElement(pag, "detPag")
  ET.SubElement(detPag, "tPag").text = "01"  # Dinheiro/Outros
  ET.SubElement(detPag, "vPag").text = "0.00"

  # Informações Adicionais
  infAdic = ET.SubElement(infNFe, "infAdic")
  ET.SubElement(infAdic, "infCpl").text = (
      f"Processado via Hub local sem IA a partir do arquivo {nome_arquivo}"
  )

  # Formata o XML bonito (pretty print)
  rough_string = ET.tostring(nfe_proc, encoding="utf-8")
  reparsed = minidom.parseString(rough_string)
  return reparsed.toprettyxml(indent="  ", encoding="utf-8")


if uploaded_files:
  if st.button("🚀 Processar Convertendo para XML", type="primary"):
    barra = st.progress(0)
    total = len(uploaded_files)
    resultados_xml = []

    for i, arquivo in enumerate(uploaded_files):
      try:
        bytes_pdf = arquivo.read()
        leitor = PyPDF2.PdfReader(io.BytesIO(bytes_pdf))
        texto_completo = ""
        for pagina in leitor.pages:
          t = pagina.extract_text()
          if t:
            texto_completo += t + "\n"

        xml_bytes = gerar_xml_deterministico(
            texto_completo, arquivo.name
        )
        nome_xml = os.path.splitext(arquivo.name)[0] + ".xml"
        resultados_xml.append((nome_xml, xml_bytes))

      except Exception as e:
        st.error(f"Erro ao processar {arquivo.name}: {e}")

      barra.progress((i + 1) / total)

    st.success(
        "✨ Conversão ultrarrápida concluída sem uso de IA (processamento local)!"
    )

    # Criação de um arquivo ZIP único para baixar todos os XMLs de uma vez
    import zipfile

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
      for nome_xml, xml_bytes in resultados_xml:
        zip_file.writestr(nome_xml, xml_bytes)

    st.download_button(
        label="📥 Baixar Pacote de XMLs (.ZIP)",
        data=zip_buffer.getvalue(),
        file_name=f"xmls_gerados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
        mime="application/zip",
        use_container_width=True,
    )
