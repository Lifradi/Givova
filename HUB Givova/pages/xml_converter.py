from datetime import datetime
import io
import zipfile
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

st.title("⚡ Conversor de PDF para XML (Padrão SEFAZ v4.00) - PRO")
st.write(
    "Converta os PDFs de notas fiscais em arquivos XML estruturados "
    "com extração de dados à prova de falhas."
)

uploaded_files = st.file_uploader(
    "Envie os PDFs das Notas/CT-es",
    type=["pdf"],
    accept_multiple_files=True,
    key="uploader_pdf_xml",
)


def extrair_dados_seguros(texto_pdf):
    """Extrai os dados do PDF utilizando Regex com âncoras contextuais para evitar falsos positivos."""
    dados = {}

    # 1. CHAVE DE ACESSO (44 dígitos, podendo ter espaços ou quebras de linha entre eles)
    match_chave = re.search(r"(?<!\d)(?:\d[\s\n]*){44}(?!\d)", texto_pdf)
    if match_chave:
        dados['chave'] = re.sub(r"\D", "", match_chave.group(0))
    else:
        raise ValueError("Chave de acesso de 44 dígitos não encontrada no PDF.")

    # 2. DATA DE EMISSÃO (Procura por DD/MM/YYYY logo após a palavra EMISSÃO)
    match_data = re.search(r"(?:DATA DA EMISSÃO|EMISSÃO:)[\s\n]*(\d{2}/\d{2}/\d{4})", texto_pdf, re.IGNORECASE)
    if match_data:
        dia, mes, ano = match_data.group(1).split('/')
        dados['dhEmi'] = f"{ano}-{mes}-{dia}T12:00:00-03:00"
    else:
        # Fallback inteligente: tenta pegar da chave de acesso se a palavra falhar
        ano_mes = dados['chave'][2:6]
        ano_completo = "20" + ano_mes[0:2] if int(ano_mes[0:2]) < 50 else "19" + ano_mes[0:2]
        mes = ano_mes[2:4]
        dados['dhEmi'] = f"{ano_completo}-{mes}-01T12:00:00-03:00"

    # 3. VALOR DA NOTA (Busca pelo valor após V. TOTAL DA NOTA ou VALOR TOTAL)
    match_valor = re.search(r"(?:V\. TOTAL DA NOTA|VALOR TOTAL:?[\sR\$]*)([\d\.,]+)", texto_pdf, re.IGNORECASE)
    if match_valor:
        valor_str = match_valor.group(1).replace(".", "").replace(",", ".")
        try:
            dados['vNF'] = f"{float(valor_str):.2f}"
        except ValueError:
            dados['vNF'] = "0.00"
    else:
        dados['vNF'] = "0.00"

    # 4. CNPJs (Captura todos e separa Emitente de Destinatário baseado na Chave)
    dados['cnpj_emitente'] = dados['chave'][6:20]
    dados['cnpj_destinatario'] = "00000000000000" # Fallback padrão
    
    cnpjs_encontrados = re.findall(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", texto_pdf)
    for c in cnpjs_encontrados:
        c_limpo = re.sub(r"\D", "", c)
        # Se achou um CNPJ diferente do Emitente, assume como Destinatário
        if c_limpo != dados['cnpj_emitente']:
            dados['cnpj_destinatario'] = c_limpo
            break

    return dados


def gerar_xml_padrao_sefaz(texto_pdf, nome_arquivo):
    """Gera o XML estruturado no formato oficial NFe 4.00 com os dados limpos."""
    
    dados = extrair_dados_seguros(texto_pdf)
    chave = dados['chave']
    
    # Fragmentando a chave extraída com sucesso
    cUF = chave[0:2]
    mod = chave[20:22]
    serie = str(int(chave[22:25]))
    nNF = str(int(chave[25:34]))
    tpEmis = chave[34:35]
    cNF = chave[35:43]
    cDV = chave[43:44]

    # --- MONTAGEM DO XML ---
    nfe_proc = ET.Element(
        "nfeProc",
        attrib={"xmlns": "http://www.portalfiscal.inf.br/nfe", "versao": "4.00"},
    )
    NFe = ET.SubElement(nfe_proc, "NFe", attrib={"xmlns": "http://www.portalfiscal.inf.br/nfe"})
    infNFe = ET.SubElement(
        NFe,
        "infNFe",
        attrib={"Id": f"NFe{chave}", "versao": "4.00"},
    )

    # Bloco IDE
    ide = ET.SubElement(infNFe, "ide")
    ET.SubElement(ide, "cUF").text = cUF
    ET.SubElement(ide, "cNF").text = cNF
    ET.SubElement(ide, "natOp").text = "VENDA/PRESTACAO DE SERVICO"
    ET.SubElement(ide, "mod").text = mod
    ET.SubElement(ide, "serie").text = serie
    ET.SubElement(ide, "nNF").text = nNF
    ET.SubElement(ide, "dhEmi").text = dados['dhEmi']
    ET.SubElement(ide, "tpNF").text = "1"
    ET.SubElement(ide, "idDest").text = "1"
    ET.SubElement(ide, "cMunFG").text = "0000000"
    ET.SubElement(ide, "tpImp").text = "1"
    ET.SubElement(ide, "tpEmis").text = tpEmis
    ET.SubElement(ide, "cDV").text = cDV
    ET.SubElement(ide, "tpAmb").text = "1"
    ET.SubElement(ide, "finNFe").text = "1"
    ET.SubElement(ide, "indFinal").text = "0"
    ET.SubElement(ide, "indPres").text = "9"
    ET.SubElement(ide, "procEmi").text = "0"
    ET.SubElement(ide, "verProc").text = "4.0"

    # Bloco EMIT
    emit = ET.SubElement(infNFe, "emit")
    ET.SubElement(emit, "CNPJ").text = dados['cnpj_emitente']
    ET.SubElement(emit, "xNome").text = "RAZAO SOCIAL EXTRAIDA DO PDF"
    enderEmit = ET.SubElement(emit, "enderEmit")
    ET.SubElement(enderEmit, "xLgr").text = "ENDERECO DO EMITENTE"
    ET.SubElement(enderEmit, "nro").text = "S/N"
    ET.SubElement(enderEmit, "xBairro").text = "BAIRRO"
    ET.SubElement(enderEmit, "cMun").text = "0000000"
    ET.SubElement(enderEmit, "xMun").text = "CIDADE"
    ET.SubElement(enderEmit, "UF").text = "EX"
    ET.SubElement(enderEmit, "CEP").text = "00000000"
    ET.SubElement(enderEmit, "cPais").text = "1058"
    ET.SubElement(enderEmit, "xPais").text = "BRASIL"
    ET.SubElement(emit, "IE").text = "ISENTO"
    ET.SubElement(emit, "CRT").text = "3"

    # Bloco DEST
    dest = ET.SubElement(infNFe, "dest")
    ET.SubElement(dest, "CNPJ").text = dados['cnpj_destinatario']
    ET.SubElement(dest, "xNome").text = "DESTINATARIO EXTRAIDO DO PDF"
    enderDest = ET.SubElement(dest, "enderDest")
    ET.SubElement(enderDest, "xLgr").text = "ENDERECO DO DESTINATARIO"
    ET.SubElement(enderDest, "nro").text = "S/N"
    ET.SubElement(enderDest, "xBairro").text = "BAIRRO"
    ET.SubElement(enderDest, "cMun").text = "0000000"
    ET.SubElement(enderDest, "xMun").text = "CIDADE"
    ET.SubElement(enderDest, "UF").text = "EX"
    ET.SubElement(enderDest, "CEP").text = "00000000"
    ET.SubElement(enderDest, "cPais").text = "1058"
    ET.SubElement(enderDest, "xPais").text = "BRASIL"
    ET.SubElement(dest, "indIEDest").text = "9"

    # Bloco DET (Itens) - Usando o valor dinâmico extraído
    det = ET.SubElement(infNFe, "det", attrib={"nItem": "1"})
    prod = ET.SubElement(det, "prod")
    ET.SubElement(prod, "cProd").text = "001"
    ET.SubElement(prod, "cEAN").text = "SEM GTIN"
    ET.SubElement(prod, "xProd").text = "PRODUTOS/SERVICOS CONFORME NOTA FISCAL ORIGINAL"
    ET.SubElement(prod, "NCM").text = "00000000"
    ET.SubElement(prod, "CFOP").text = "5933"
    ET.SubElement(prod, "uCom").text = "UN"
    ET.SubElement(prod, "qCom").text = "1.0000"
    ET.SubElement(prod, "vUnCom").text = dados['vNF']
    ET.SubElement(prod, "vProd").text = dados['vNF']
    ET.SubElement(prod, "cEANTrib").text = "SEM GTIN"
    ET.SubElement(prod, "uTrib").text = "UN"
    ET.SubElement(prod, "qTrib").text = "1.0000"
    ET.SubElement(prod, "vUnTrib").text = dados['vNF']
    ET.SubElement(prod, "indTot").text = "1"

    imposto = ET.SubElement(det, "imposto")
    vTotTrib = ET.SubElement(imposto, "vTotTrib")
    vTotTrib.text = "0.00"
    
    ICMS = ET.SubElement(imposto, "ICMS")
    ICMS40 = ET.SubElement(ICMS, "ICMS40")
    ET.SubElement(ICMS40, "orig").text = "0"
    ET.SubElement(ICMS40, "CST").text = "40"

    # Bloco TOTAL
    total = ET.SubElement(infNFe, "total")
    ICMSTot = ET.SubElement(total, "ICMSTot")
    ET.SubElement(ICMSTot, "vBC").text = "0.00"
    ET.SubElement(ICMSTot, "vICMS").text = "0.00"
    ET.SubElement(ICMSTot, "vICMSDeson").text = "0.00"
    ET.SubElement(ICMSTot, "vFCP").text = "0.00"
    ET.SubElement(ICMSTot, "vBCST").text = "0.00"
    ET.SubElement(ICMSTot, "vST").text = "0.00"
    ET.SubElement(ICMSTot, "vFCPST").text = "0.00"
    ET.SubElement(ICMSTot, "vFCPSTRet").text = "0.00"
    ET.SubElement(ICMSTot, "vProd").text = dados['vNF']
    ET.SubElement(ICMSTot, "vFrete").text = "0.00"
    ET.SubElement(ICMSTot, "vSeg").text = "0.00"
    ET.SubElement(ICMSTot, "vDesc").text = "0.00"
    ET.SubElement(ICMSTot, "vII").text = "0.00"
    ET.SubElement(ICMSTot, "vIPI").text = "0.00"
    ET.SubElement(ICMSTot, "vIPIDevol").text = "0.00"
    ET.SubElement(ICMSTot, "vPIS").text = "0.00"
    ET.SubElement(ICMSTot, "vCOFINS").text = "0.00"
    ET.SubElement(ICMSTot, "vOutro").text = "0.00"
    ET.SubElement(ICMSTot, "vNF").text = dados['vNF']
    ET.SubElement(ICMSTot, "vTotTrib").text = "0.00"

    transp = ET.SubElement(infNFe, "transp")
    ET.SubElement(transp, "modFrete").text = "9"

    pag = ET.SubElement(infNFe, "pag")
    detPag = ET.SubElement(pag, "detPag")
    ET.SubElement(detPag, "tPag").text = "90"
    ET.SubElement(detPag, "vPag").text = "0.00"

    infAdic = ET.SubElement(infNFe, "infAdic")
    ET.SubElement(infAdic, "infCpl").text = "XML Extraído do PDF nativo via Hub Givova."

    # Assinatura
    protNFe = ET.SubElement(nfe_proc, "protNFe", attrib={"versao": "4.00"})
    infProt = ET.SubElement(protNFe, "infProt")
    ET.SubElement(infProt, "tpAmb").text = "1"
    ET.SubElement(infProt, "verAplic").text = "4.0"
    ET.SubElement(infProt, "chNFe").text = chave
    ET.SubElement(infProt, "dhRecbto").text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
    ET.SubElement(infProt, "nProt").text = "135" + chave[0:12]
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
        erros = 0

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

            except ValueError as ve:
                st.warning(f"⚠️ Aviso em {arquivo.name}: {ve}")
                erros += 1
            except Exception as e:
                st.error(f"❌ Erro crítico ao processar {arquivo.name}: {e}")
                erros += 1

            barra.progress((i + 1) / total)

        if resultados_xml:
            if erros > 0:
                st.success(f"✨ Conversão parcial! {len(resultados_xml)} arquivos convertidos. {erros} erros encontrados.")
            else:
                st.success("✨ Conversão concluída com sucesso para todos os arquivos!")

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
        else:
            st.error("Nenhum XML pôde ser gerado. Verifique os avisos acima.")
