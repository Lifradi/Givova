import zipfile
import io
import streamlit as st

# ... (restante do seu código anterior)

if arquivos_upload:
    if st.button("🚀 Processar Romaneios"):
        try:
            servico = autenticar_drive()
        except Exception as e:
            st.error(f"Erro na autenticação: {e}")
            st.stop()

        for idx, arquivo_upload in enumerate(arquivos_upload):
            bytes_pdf = arquivo_upload.read()
            dados_notas = extrair_dados_do_pdf(bytes_pdf)
            
            if not dados_notas:
                continue

            # --- OTIMIZAÇÃO: Gerenciamento em memória (Sem criar pastas no disco) ---
            zip_buffer = io.BytesIO()
            total_encontrados_drive = 0
            notas_nao_encontradas = []

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                for numero, uf in dados_notas:
                    # --- OTIMIZAÇÃO: Busca mais eficiente ---
                    # Nota: O Google Drive permite consultas complexas. 
                    # Se tiver muitos itens, considere processar em blocos.
                    query = f"mimeType='application/pdf' and name contains '{numero}' and trashed=false"
                    if uf:
                        query += f" and name contains '{uf}'"

                    resultados = servico.files().list(
                        q=query, spaces="drive", fields="files(id, name)"
                    ).execute()
                    
                    arquivos = resultados.get("files", [])

                    if not arquivos:
                        notas_nao_encontradas.append(f"{numero} ({uf})")
                    else:
                        for arquivo_alvo in arquivos:
                            file_id = arquivo_alvo['id']
                            file_name = arquivo_alvo['name']
                            
                            # Baixa o conteúdo do arquivo diretamente para um buffer
                            request = servico.files().get_media(fileId=file_id)
                            file_content = io.BytesIO()
                            downloader = MediaIoBaseDownload(file_content, request)
                            
                            done = False
                            while not done:
                                _, done = downloader.next_chunk()
                            
                            # Escreve o arquivo no ZIP sem salvar em disco
                            zipf.writestr(file_name, file_content.getvalue())
                            total_encontrados_drive += 1

            # Finaliza o buffer do ZIP
            zip_buffer.seek(0)

            # Exibe o botão de download usando o buffer na memória
            st.download_button(
                label=f"📥 Baixar ZIP: {arquivo_upload.name}",
                data=zip_buffer,
                file_name=f"notas_{os.path.splitext(arquivo_upload.name)[0]}.zip",
                mime="application/zip"
            )
            
            st.success(f"Processado: {total_encontrados_drive} arquivos adicionados ao ZIP.")
