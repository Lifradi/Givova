import os
import shutil
import re

def organizar_xmls_por_carga():
    # Define os diretórios de entrada e saída conforme a sua estrutura
    pasta_entrada = 'entrada'
    pasta_saida = 'saida'

    # Cria a pasta de saída principal caso ela tenha sido apagada acidentalmente
    if not os.path.exists(pasta_saida):
        os.makedirs(pasta_saida)

    # Verifica se a pasta de entrada existe
    if not os.path.exists(pasta_entrada):
        print(f"Erro: A pasta '{pasta_entrada}' não foi encontrada.")
        return

    # Expressão regular para localizar o número da carga (Ex: "Carga: 258066")
    padrao_carga = re.compile(r'Carga:\s*(\d+)', re.IGNORECASE)

    contador_sucesso = 0
    contador_erro = 0

    # Percorre todos os arquivos dentro da pasta 'entrada'
    for nome_arquivo in os.listdir(pasta_entrada):
        # Filtra apenas os arquivos com extensão .xml
        if nome_arquivo.lower().endswith('.xml'):
            caminho_origem = os.path.join(pasta_entrada, nome_arquivo)

            try:
                # Abre e lê o conteúdo do XML (tratando a codificação padrão)
                with open(caminho_origem, 'r', encoding='utf-8', errors='ignore') as arquivo_xml:
                    conteudo = arquivo_xml.read()

                # Busca o padrão da carga no texto do arquivo
                match = padrao_carga.search(conteudo)

                if match:
                    # Extrai apenas os números da carga
                    numero_carga = match.group(1)
                    nome_subpasta = f"carga {numero_carga}"
                    caminho_subpasta = os.path.join(pasta_saida, nome_subpasta)

                    # Cria a subpasta na 'saida' se ela ainda não existir
                    if not os.path.exists(caminho_subpasta):
                        os.makedirs(caminho_subpasta)

                    # Move o arquivo da 'entrada' para a subpasta correspondente na 'saida'
                    caminho_destino = os.path.join(caminho_subpasta, nome_arquivo)
                    shutil.move(caminho_origem, caminho_destino)
                    
                    print(f"[OK] Arquivo '{nome_arquivo}' movido para '{nome_subpasta}'.")
                    contador_sucesso += 1
                else:
                    print(f"[Aviso] Nenhuma 'Carga' encontrada no arquivo '{nome_arquivo}'.")
                    contador_erro += 1

            except Exception as e:
                print(f"[Erro] Falha ao processar o arquivo '{nome_arquivo}': {e}")
                contador_erro += 1

    print("-" * 30)
    print("Processamento Concluído!")
    print(f"Arquivos movidos com sucesso: {contador_sucesso}")
    print(f"Arquivos ignorados/com erro: {contador_erro}")

if __name__ == "__main__":
    organizar_xmls_por_carga()
