import io
import json
import os
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
import streamlit as st
import streamlit_authenticator as stauth

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Separador de Cargas", page_icon="📁", layout="centered"
)


# --- CARREGA OS USUÁRIOS PARA VALIDAÇÃO DIRETA ---
def carregar_configuracao():
    if "usuarios_hub" in st.secrets:
        return dict(st.secrets["usuarios_hub"])
    elif os.path.exists("usuarios.json"):
        with open("usuarios.json", "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {
            "credentials": {"usernames": {}},
            "cookie": {
                "name": "hub_cookie",
                "key": "chave_padrao",
                "expiry_days": 1,
            },
        }


config = carregar_configuracao()

cookie_config = {
    "name": "hub_givova_cookie",
    "key": "chave_secreta_super_segura_123",
    "expiry_days": 1,
}

authenticator = stauth.Authenticate(
    config["credentials"],
    cookie_config["name"],
    cookie_config["key"],
    cookie_expiry_days=cookie_config["expiry_days"],
)

# Tenta carregar o estado da sessão de login
authentication_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")
username = st.session_state.get("username")

# --- BLOQUEIO DE SEGURANÇA SE NÃO ESTIVER LOGADO ---
if not authentication_status:
    st.error(
        "🔒 Acesso Negado! Por favor, faça o login na página principal do Hub"
        " primeiro."
    )
    if st.button("Ir para o Login"):
        st.switch_page("app.py")
    st.stop()

# Se estiver logado, exibe os elementos da barra lateral
authenticator.logout("Sair do Sistema", "sidebar", key="logout_xmls")
st.sidebar.markdown(f"👤 **Logado como:** {name}")


# --- TABELA DE PREÇO (FRETE) ---
def _norm(texto):
    """Maiúsculo, sem acento e sem espaços repetidos (p/ comparar cidades)."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip().upper()


# Cada cidade é um item separado. Regiões (Vale do Aço, Vale do Rio Doce etc.)
# foram ignoradas, conforme combinado.
BLOCO_1 = [
    "Belo Horizonte", "Baldim", "Betim", "Brumadinho", "Caeté",
    "Capim Branco", "Confins", "Contagem", "Esmeraldas", "Florestal",
    "Ibirité", "Igarapé", "Itaguara", "Itatiaiuçu", "Jaboticatubas",
    "Juatuba", "Lagoa Santa", "Mário Campos", "Mateus Leme", "Matozinhos",
    "Nova Lima", "Nova União", "Pedro Leopoldo", "Raposos",
    "Ribeirão das Neves", "Rio Acima", "Rio Manso", "Sabará", "Santa Luzia",
    "São Joaquim de Bicas", "São José da Lapa", "Sarzedo",
    "Taquaraçu de Minas", "Vespasiano",
]

BLOCO_2 = [
    "Pouso Alegre", "Poços de Caldas", "Varginha", "Itajubá", "Lavras",
    "Passos", "Alfenas", "Três Corações", "São Lourenço", "Caxambu",
    "Guaxupé", "Santa Rita do Sapucaí", "Extrema", "Cambuí", "Andradas",
    "Machado", "Ouro Fino", "Paraguaçu", "Boa Esperança", "Nepomuceno",
    "Campo Belo", "Três Pontas", "Juiz de Fora", "Ubá", "Muriaé", "Viçosa",
    "Cataguases", "Leopoldina", "Além Paraíba", "Ponte Nova", "Manhuaçu",
    "Santos Dumont", "Visconde do Rio Branco", "Carangola", "Itamarandiba",
    "Espera Feliz", "Raul Soares", "São João Nepomuceno", "Rio Pomba",
    "Uberlândia", "Uberaba", "Araguari", "Ituiutaba", "Patos de Minas",
    "Patrocínio", "Araxá", "Frutal", "Monte Carmelo", "Carmo do Paranaíba",
    "Sacramento", "Conceição das Alagoas", "Prata", "Tupaciguara",
    "Coromandel", "Divinópolis", "Itaúna", "Pará de Minas", "Nova Serrana",
    "Formiga", "Oliveira", "Bom Despacho", "Lagoa da Prata",
    "Santo Antônio do Monte", "Arcos", "Cláudio", "Abaeté", "Bambuí",
    "Piumhi", "Carmo do Cajuru", "Martinho Campos",
]

BLOCO_3 = [
    "Montes Claros", "Janaúba", "Pirapora", "Salinas", "Taiobeiras",
    "Bocaiuva", "Januária", "São Francisco", "Espinosa", "Francisco Sá",
    "Manga", "Brasília de Minas", "Porteirinha", "Governador Valadares",
    "Teófilo Otoni", "Ipatinga", "Coronel Fabriciano", "Timóteo",
    "Caratinga", "Aimorés", "Mantena", "Nanuque", "Almenara", "Araçuaí",
    "Pedra Azul", "Capelinha", "Diamantina", "Itamarandiba", "Serro",
    "Manhuaçu", "Ponte Nova", "João Monlevade", "Conselheiro Pena",
    "Resplendor", "Inhapim", "Guanhães", "Santa Maria de Itabira",
    "Santana do Paraíso", "Belo Oriente",
]

# Percentual de cada bloco (origem MG)
BLOCOS_MG = [(BLOCO_1, 17), (BLOCO_2, 19), (BLOCO_3, 24)]

# Cidade -> percentual. Se a cidade estiver em mais de um bloco, vale o MAIOR %.
CIDADES_MG = {}
for _cidades, _pct in BLOCOS_MG:
    for _c in _cidades:
        _k = _norm(_c)
        CIDADES_MG[_k] = max(CIDADES_MG.get(_k, 0), _pct)


def calcular_percentual(uf_origem, uf_destino, mun_destino):
    """Retorna o percentual (int) da tabela de preço ou None se não houver regra."""
    if not uf_origem or not uf_destino:
        return None

    if uf_origem == "MT":
        return 22

    if uf_origem == "BA":
        return 17

    if uf_origem == "MG":
        if uf_destino == "MG":
            # cidade na tabela de blocos; senão, demais cidades de MG = 24%
            return CIDADES_MG.get(_norm(mun_destino), 24)
        if uf_destino == "ES":
            return 28
        return None

    if uf_origem == "GO":
        return {"GO": 17, "DF": 19, "MG": 19, "TO": 23}.get(uf_destino)

    return None  # origem fora da tabela (ex.: SP)


# --- FUNÇÕES AUXILIARES: LEITURA DO XML (ORIGEM x DESTINO) ---
def _filho(elem, nome):
    """Primeiro filho direto com a tag `nome` (ignora namespace)."""
    if elem is None:
        return None
    for sub in elem:
        if sub.tag.split("}")[-1] == nome:
            return sub
    return None


def _texto(elem, nome):
    sub = _filho(elem, nome)
    if sub is not None and sub.text:
        return sub.text.strip()
    return None


def extrair_dados_nfe(bytes_xml):
    """Lê SOMENTE:
      - origem : <infNFe><emit><enderEmit><UF>
      - destino: <infNFe><dest><enderDest><UF> e <xMun>
    Caminhos exatos, sem varrer a nota (não confunde com transportadora,
    retirada, entrega etc.).
    Retorna (uf_origem, uf_destino, mun_destino); itens ausentes = None.
    """
    try:
        root = ET.fromstring(bytes_xml)
    except ET.ParseError:
        return None, None, None

    inf_nfe = None
    for elem in root.iter():
        if elem.tag.split("}")[-1] == "infNFe":
            inf_nfe = elem
            break
    if inf_nfe is None:
        return None, None, None

    ender_emit = _filho(_filho(inf_nfe, "emit"), "enderEmit")
    ender_dest = _filho(_filho(inf_nfe, "dest"), "enderDest")

    uf_origem = _texto(ender_emit, "UF")
    uf_destino = _texto(ender_dest, "UF")
    mun_destino = _texto(ender_dest, "xMun")

    return (
        uf_origem.upper() if uf_origem else None,
        uf_destino.upper() if uf_destino else None,
        mun_destino,
    )


# --- CORPO DO SISTEMA ---
st.title("📁 Separador de Cargas")
st.write(
    "Envie seus arquivos XMLs de notas/romaneios. O sistema lê o conteúdo, "
    "separa-os automaticamente por número de carga, inclui o percentual da "
    "tabela de preço e a UF de destino no nome do arquivo "
    "(ex.: 22%_GO_arquivo.xml) e gera um arquivo ZIP organizado."
)

# Componente para upload de múltiplos arquivos XML
arquivos_xml = st.file_uploader(
    "📂 Envie os arquivos XML", type=["xml"], accept_multiple_files=True
)

if arquivos_xml:
    if st.button("🚀 Processar e Organizar XMLs"):
        padrao_carga = re.compile(r"Carga:\s*(\d+)", re.IGNORECASE)

        contador_sucesso = 0
        contador_erro = 0
        sem_tabela = []
        # {numero_carga: {nome_no_zip: bytes}}
        cargas_encontradas = {}

        with st.spinner("Processando e organizando os arquivos..."):
            for arquivo in arquivos_xml:
                nome_arquivo = arquivo.name
                try:
                    bytes_conteudo = arquivo.read()
                    conteudo_texto = bytes_conteudo.decode(
                        "utf-8", errors="ignore"
                    )
                    match = padrao_carga.search(conteudo_texto)

                    if match:
                        numero_carga = match.group(1)
                        uf_origem, uf_dest, mun_dest = extrair_dados_nfe(
                            bytes_conteudo
                        )
                        uf_destino = uf_dest or "SEM-UF"
                        pct = calcular_percentual(uf_origem, uf_dest, mun_dest)

                        if pct is None:
                            prefixo = "SEM-TABELA"
                            sem_tabela.append(
                                f"{nome_arquivo} (origem: {uf_origem or '?'}"
                                f" → destino: {uf_dest or '?'})"
                            )
                        else:
                            prefixo = f"{pct}%"

                        # Novo nome: PERCENTUAL_UF_nomeoriginal.xml
                        novo_nome = f"{prefixo}_{uf_destino}_{nome_arquivo}"

                        if numero_carga not in cargas_encontradas:
                            cargas_encontradas[numero_carga] = {}

                        cargas_encontradas[numero_carga][novo_nome] = bytes_conteudo
                        contador_sucesso += 1
                    else:
                        contador_erro += 1

                except Exception:
                    contador_erro += 1

        # Exibe métricas do processamento
        col1, col2 = st.columns(2)
        col1.metric("XMLs Organizados com Sucesso", contador_sucesso)
        col2.metric("XMLs sem Carga / Erros", contador_erro)

        if sem_tabela:
            st.warning(
                f"⚠️ {len(sem_tabela)} XML(s) sem regra na tabela de preço "
                "(prefixo SEM-TABELA_):\n\n"
                + "\n".join(f"- {item}" for item in sem_tabela)
            )

        if contador_sucesso > 0:
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                for carga, arquivos_dict in cargas_encontradas.items():
                    for nome_arq, conteudo_bytes in arquivos_dict.items():
                        caminho_no_zip = f"carga {carga}/{nome_arq}"
                        zipf.writestr(caminho_no_zip, conteudo_bytes)

            zip_buffer.seek(0)

            st.success("✅ Organização concluída com sucesso!")

            st.download_button(
                label="📥 Baixar ZIP Organizado por Cargas",
                data=zip_buffer,
                file_name="xmls_organizados_por_carga.zip",
                mime="application/zip",
                key="btn_download_xmls",
            )
        else:
            st.warning(
                "⚠️ Nenhum arquivo continha uma 'Carga' válida para ser organizado."
            )
