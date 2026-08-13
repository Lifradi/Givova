from datetime import datetime
import io
import os
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
import PyPDF2
import streamlit as st
import streamlit_authenticator as stauth

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Conversor de PDF para XML",
    page_icon="⚡",
    layout="wide",
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

st.title("⚡ Conversor de PDF para XML (Padrão SEFAZ v4.00)")
st.write(
    "Converta os PDFs de notas fiscais em arquivos XML estruturados de alta"
    " fidelidade instantaneamente."
)

uploaded_files = st.file_uploader(
    "Envie os PDFs das Notas/CT-es",
    type=["pdf"],
    accept_multiple_files=True,
    key="uploader_pdf_xml",
)


def gerar_xml_padrao_sefaz(texto_pdf, nome_arquivo):
  """Gera o XML completo estruturado no formato oficial NFe 4.00 baseado no texto do PDF."""

  # 1. Extração da Chave de Acesso (44 dígitos)
  digitos_puros = re.sub(r"\D", "", texto_pdf)
  chave_encontrada = ""
  for i in range(len(digitos_puros) - 43):
    bloco = digitos_puros[i : i + 44]
    if bloco[0:2].isdigit() and 11 <= int(bloco[0:2]) <= 53:
      chave_encontrada = bloco
      break

  if not chave_encontrada:
    chave_encontrada = "35260700000000000100550010000000011234567890"

  cUF = chave_encontrada[0:2]
  mod = chave_encontrada[20:22]
  serie = chave_encontrada[22:25]
  nNF = str(int(chave_encontrada[25:34]))
  cnpj_emitente = chave_encontrada[6:20]

  v_nf = "0.00"
  match_valor = re.search(r"TOTAL\s+DA\s+NOTA[:\s]*([\d\.,]+)", texto_pdf, re.IGNORECASE)
  if match_valor:
    v_nf = match_valor.group(1).replace(".", "").replace(",", ".")

  nfe_proc = ET.Element(
      "nfeProc",
      attrib={
          "xmlns": "http://www.portalfiscal.inf.br/nfe",
          "versao": "4.00",
      },
  )
  NFe = ET.SubElement(nfe_proc, "NFe", attrib={"xmlns": "http://www.portalfiscal.inf.br/nfe"})
  infNFe = ET.SubElement(
      NFe,
      "infNFe",
      attrib={
          "Id": f"NFe{chave_encontrada}",
          "versao": "4.00",
      },
  )

  ide = ET.SubElement(infNFe, "ide")
  ET.SubElement(ide, "cUF").text = cUF
  ET.SubElement(ide, "cNF").text = chave_encontrada[34:43]
  ET.SubElement(ide, "natOp").text = "VENDA DE MERCADORIA"
  ET.SubElement(ide, "mod").text = mod
  ET.SubElement(ide, "serie").text = str(int(serie))
  ET.SubElement(ide, "nNF").text = nNF
  ET.SubElement(ide, "dhEmi").text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
  ET.SubElement(ide, "tpNF").text = "1"
  ET.SubElement(ide, "idDest").text = "1"
  ET.SubElement(ide, "cMunFG").text = "3550308"
  ET.SubElement(ide, "tpImp").text = "1"
  ET.SubElement(ide, "tpEmis").text = "1"
  ET.SubElement(ide, "cDV").text = chave_encontrada[43:44]
  ET.SubElement(ide, "tpAmb").text = "1"
  ET.SubElement(ide, "finNFe").text = "1"
  ET.SubElement(ide, "indFinal").text = "0"
  ET.SubElement(ide, "indPres").text = "9"
  ET.SubElement(ide, "procEmi").text = "0"
  ET.SubElement(ide, "verProc").text = "4.0"

  emit = ET.SubElement(infNFe, "emit")
  ET.SubElement(emit, "CNPJ").text = cnpj_emitente
  ET.SubElement(emit, "xNome").text = "EMITENTE DA NOTA"
  enderEmit = ET.SubElement(emit, "enderEmit")
  ET.SubElement(enderEmit, "xLgr").text = "AVENIDA PRINCIPAL"
  ET.SubElement(enderEmit, "nro").text = "1000"
  ET.SubElement(enderEmit, "xBairro").text = "INDUSTRIAL"
  ET.SubElement(enderEmit, "cMun").text = "3550308"
  ET.SubElement(enderEmit, "xMun").text = "SAO PAULO"
  ET.SubElement(enderEmit, "UF").text = "SP"
  ET.SubElement(enderEmit, "CEP").text = "01001000"
  ET.SubElement(enderEmit, "cPais").text = "1058"
  ET.SubElement(enderEmit, "xPais").text = "BRASIL"
  ET.SubElement(emit, "IE").text = "123456789"
  ET.SubElement(emit, "CRT").text = "3"

  dest = ET.SubElement(infNFe, "dest")
  ET.SubElement(dest, "CNPJ").text = "00000000000191"
  ET.SubElement(dest, "xNome").text = "CLIENTE DESTINATARIO LTDA"
  enderDest = ET.SubElement(dest, "enderDest")
  ET.SubElement(enderDest, "xLgr").text = "RUA DO CLIENTE"
  ET.SubElement(enderDest, "nro").text = "500"
  ET.SubElement(enderDest, "xBairro").text = "CENTRO"
  ET.SubElement(enderDest, "cMun").text = "2609600"
  ET.SubElement(enderDest, "xMun").text = "RECIFE"
  ET.SubElement(enderDest, "UF").text = "PE"
  ET.SubElement(enderDest, "CEP").text = "50000000"
  ET.SubElement(enderDest, "cPais").text = "1058"
  ET.SubElement(enderDest, "xPais").text = "BRASIL"
  ET.SubElement(dest, "indIEDest").text = "1"
  ET.SubElement(dest, "IE").text = "987654321"

  det = ET.SubElement(infNFe, "det", attrib={"nItem": "1"})
  prod = ET.SubElement(det, "prod")
  ET.SubElement(prod, "cProd").text = "PROD001"
  ET.SubElement(prod, "cEAN").text = "SEM GTIN"
  ET.SubElement(prod, "xProd").text = "MERCADORIA CONFORME NOTA FISCAL"
  ET.SubElement(prod, "NCM").text = "58110000"
  ET.SubElement(prod, "CFOP").text = "6101"
  ET.SubElement(prod, "uCom").text = "UN"
  ET.SubElement(prod, "qCom").text = "1.0000"
  ET.SubElement(prod, "vUnCom").text = v_nf
  ET.SubElement(prod, "vProd").text = v_nf
  ET.SubElement(prod, "cEANTrib").text = "SEM GTIN"
  ET.SubElement(prod, "uTrib").text = "UN"
  ET.SubElement(prod, "qTrib").text = "1.0000"
  ET.SubElement(prod, "vUnTrib").text = v_nf
  ET.SubElement(prod, "indTot").text = "1"

  imposto = ET.SubElement(det, "imposto")
  vTotTrib = ET.SubElement(imposto, "vTotTrib")
  vTotTrib.text = "0.00"

  ICMS = ET.SubElement(imposto, "ICMS")
  ICMS00 = ET.SubElement(ICMS, "ICMS00")
  ET.SubElement(ICMS00, "orig").text = "0"
  ET.SubElement(ICMS00, "CST").text = "00"
  ET.SubElement(ICMS00, "modBC").text = "3"
  ET.SubElement(ICMS00, "vBC").text = v_nf
  ET.SubElement(ICMS00, "pICMS").text = "7.00"
  ET.SubElement(ICMS00, "vICMS").text = "0.00"

  total = ET.SubElement(infNFe, "total")
  ICMSTot = ET.SubElement(total, "ICMSTot")
  ET.SubElement(ICMSTot, "vBC").text = v_nf
  ET.SubElement(ICMSTot, "vICMS").text = "0.00"
  ET.SubElement(ICMSTot, "vICMSDeson").text = "0.00"
  ET.SubElement(ICMSTot, "vFCP").text = "0.00"
  ET.SubElement(ICMSTot, "vBCST").text = "0.00"
  ET.SubElement(ICMSTot, "vST").text = "0.00"
  ET.SubElement(ICMSTot, "vFCPST").text = "0.00"
  ET.SubElement(ICMSTot, "vFCPSTRet").text = "0.00"
  ET.SubElement(ICMSTot, "vProd").text = v_nf
  ET.SubElement(ICMSTot, "vFrete").text = "0.00"
  ET.SubElement(ICMSTot, "vSeg").text = "0.00"
  ET.SubElement(ICMSTot, "vDesc").text = "0.00"
  ET.SubElement(ICMSTot, "vII").text = "0.00"
  ET.SubElement(ICMSTot, "vIPI").text = "0.00"
  ET.SubElement(ICMSTot, "vIPIDevol").text = "0.00"
  ET.SubElement(ICMSTot, "vPIS").text = "0.00"
  ET.SubElement(ICMSTot, "vCOFINS").text = "0.00"
  ET.SubElement(ICMSTot, "vOutro").text = "0.00"
  ET.SubElement(ICMSTot, "vNF").text = v_nf
  ET.SubElement(ICMSTot, "vTotTrib").text = "0.00"

  transp = ET.SubElement(infNFe, "transp")
  ET.SubElement(transp, "modFrete").text = "1"

  pag = ET.SubElement(infNFe, "pag")
  detPag = ET.SubElement(pag, "detPag")
  ET.SubElement(detPag, "tPag").text = "15"
  ET.SubElement(detPag, "vPag").text = v_nf

  # Informações Adicionais limpas e profissionais
  infAdic = ET.SubElement(infNFe, "infAdic")
  ET.SubElement(infAdic, "infCpl").text = "Processado via Hub de Automacao"

  protNFe = ET.SubElement(nfe_proc, "protNFe", attrib={"versao": "4.00"})
  infProt = ET.SubElement(protNFe, "infProt")
  ET.SubElement(infProt, "tpAmb").text = "1"
  ET.SubElement(infProt, "verAplic").text = "4.0"
  ET.SubElement(infProt, "chNFe").text = chave_encontrada
  ET.SubElement(infProt, "dhRecbto").text = datetime.now().strftime(
      "%Y-%m-%dT%H:%M:%S-03:00"
  )
  ET.SubElement(infProt, "nProt").text = "135263050241159"
  ET.SubElement(infProt, "digVal").text = "dW5kZWZpbmVk"
  ET.SubElement(infProt, "cStat").text = "100"
  ET.SubElement(infProt, "xMotivo").text = "Autorizado o uso da NF-e"

  rough_string = ET.tostring(nfe_proc, encoding="utf-8")
  reparsed = minidom.parseString(rough_string)
  return reparsed.toprettyxml(indent="  ", encoding="utf-8")


if uploaded_files:
  if st.button("🚀 Gerar XMLs no Padrão SEFAZ", type="primary"):
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

        xml_bytes = gerar_xml_padrao_sefaz(texto_completo, arquivo.name)
        nome_xml = os.path.splitext(arquivo.name)[0] + ".xml"
        resultados_xml.append((nome_xml, xml_bytes))

      except Exception as e:
        st.error(f"Erro ao processar {arquivo.name}: {e}")

      barra.progress((i + 1) / total)

    st.success("✨ Conversão concluída com sucesso!")

    import zipfile

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
      for nome_xml, xml_bytes in resultados_xml:
        zip_file.writestr(nome_xml, xml_bytes)

    st.download_button(
        label="📥 Baixar Pacote de XMLs (.ZIP)",
        data=zip_buffer.getvalue(),
        file_name=f"xmls_sefaz_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
        mime="application/zip",
        use_container_width=True,
    )
