import json
import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class SigEducScraper:
    def __init__(self, direc_numero=10, max_escolas=2, headless=False, progress_callback=None):
        self.direc_numero = direc_numero
        self.max_escolas = max_escolas
        self.headless = headless
        self.progress_callback = progress_callback
        self.dados_extraidos = []
        self.log_execucao = []
        self.driver = None
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def log(self, mensagem, tipo="INFO"):
        timestamp_log = datetime.now().strftime("%H:%M:%S")
        icone = "ℹ️"
        if tipo == "SUCESSO": icone = "✅"
        elif tipo == "ERRO": icone = "❌"
        elif tipo == "AVISO": icone = "⚠️"
        
        msg_formatada = f"[{timestamp_log}] {icone} {mensagem}"
        print(msg_formatada)
        self.log_execucao.append(msg_formatada)

    def iniciar_driver(self):
        self.log("Iniciando navegador...", "INFO")
        options = webdriver.ChromeOptions()
        
        # Configurações para rodar no Streamlit Cloud e ambientes Docker/Linux
        if self.headless:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument("--window-size=1920,1080")
        
        # Tenta encontrar o binário do Chromium se não estiver no PATH padrão (comum em Linux)
        # No Streamlit Cloud, geralmente está no PATH, mas isso ajuda em outros ambientes
        if os.path.exists("/usr/bin/chromium"):
            options.binary_location = "/usr/bin/chromium"
        elif os.path.exists("/usr/bin/chromium-browser"):
            options.binary_location = "/usr/bin/chromium-browser"

        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--start-maximized')
        
        self.driver = webdriver.Chrome(options=options)

    def fechar_driver(self):
        if self.driver:
            self.driver.quit()
            self.log("Navegador fechado.", "INFO")

    def acessar_site(self):
        url = "https://sigeduc.rn.gov.br/sigeduc/public/transparencia/pages/consulta/relatorio_formacaoServidores/consulta_formacao_servidores.jsf"
        self.log(f"Acessando: {url}", "INFO")
        self.driver.get(url)
        # Aguarda o carregamento inicial da página
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='checkbox']"))
        )

    def selecionar_direc(self):
        try:
            # Marcar checkbox DIREC
            checkbox_direc = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox']"))
            )
            if not checkbox_direc.is_selected():
                checkbox_direc.click()
                self.log("Checkbox DIREC marcado", "SUCESSO")
            
            # Aguardar o select ficar habilitado/visível
            time.sleep(1) # Pequena pausa para garantir que o DOM atualizou após o click
            
            select_direc_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div/div/div[2]/div/div/div[3]/form/div[1]/div/select"))
            )
            
            select_direc = Select(select_direc_element)
            direc_texto = f"{self.direc_numero:02d}ª DIREC"
            
            encontrou = False
            for opcao in select_direc.options:
                if direc_texto in opcao.text:
                    select_direc.select_by_visible_text(opcao.text)
                    self.log(f"DIREC selecionada: {opcao.text}", "SUCESSO")
                    encontrou = True
                    break
            
            if not encontrou:
                raise Exception(f"Opção '{direc_texto}' não encontrada no select.")

        except Exception as e:
            self.log(f"Erro ao selecionar DIREC: {e}", "ERRO")
            raise

    def realizar_busca(self):
        try:
            time.sleep(1) # Estabilidade
            botao_buscar = self.driver.find_element(By.XPATH, "//input[@value='Buscar']")
            self.driver.execute_script("arguments[0].click();", botao_buscar)
            self.log("Botão BUSCAR clicado", "SUCESSO")
            
            # Aguardar resultados
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//img[@alt='Selecionar Escola']"))
            )
        except Exception as e:
            self.log(f"Erro ao realizar busca: {e}", "ERRO")
            raise

    def extrair_dados_escola(self, nome_escola):
        dados_escola = []
        try:
            # Aguardar tabela
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            # Tenta localizar a tabela de Vagas Acadêmicas
            # A estratégia aqui é procurar por todas as tabelas e verificar o caption
            tabelas = self.driver.find_elements(By.TAG_NAME, "table")
            tabela_alvo = None
            
            for tabela in tabelas:
                try:
                    caption = tabela.find_element(By.TAG_NAME, "caption")
                    if "acadêmicas" in caption.text.lower():
                        tabela_alvo = tabela
                        break
                except:
                    continue
            
            if not tabela_alvo:
                self.log(f"Tabela de Vagas Acadêmicas não encontrada para {nome_escola}", "AVISO")
                return []

            tbody = tabela_alvo.find_element(By.TAG_NAME, "tbody")
            linhas = tbody.find_elements(By.TAG_NAME, "tr")
            
            for linha in linhas:
                colunas = linha.find_elements(By.TAG_NAME, "td")
                
                # Validação básica da estrutura da linha
                if len(colunas) >= 6:
                    nome = colunas[0].text.strip()
                    matricula = colunas[1].text.strip()
                    # colunas[2] é escolaridade (muitas vezes vazio ou irrelevante na visualização rápida)
                    formacao = colunas[3].text.strip()
                    disciplina = colunas[4].text.strip()
                    ch = colunas[5].text.strip()
                    
                    # Filtros de qualidade
                    if (nome and 
                        nome.upper() not in ['NOME', 'PROFESSOR', 'SERVIDOR'] and 
                        len(nome) > 3):
                        
                        professor = {
                            'escola': nome_escola,
                            'nome': nome,
                            'matricula': matricula,
                            'formacao': formacao,
                            'disciplina': disciplina,
                            'ch': ch,
                            'direc': f"DIREC {self.direc_numero}",
                            'data_coleta': datetime.now().strftime("%d/%m/%Y %H:%M")
                        }
                        dados_escola.append(professor)

        except Exception as e:
            self.log(f"Erro ao extrair dados da escola {nome_escola}: {e}", "ERRO")
        
        return dados_escola

    def processar_escolas(self):
        try:
            escolas_links = self.driver.find_elements(By.XPATH, "//img[@alt='Selecionar Escola']")
            total_encontrado = len(escolas_links)
            self.log(f"Total de escolas encontradas: {total_encontrado}", "INFO")
            
            qtd_processar = min(self.max_escolas, total_encontrado)
            
            for i in range(qtd_processar):
                try:
                    # Refresh na lista de elementos para evitar StaleElementReferenceException
                    escolas_links = self.driver.find_elements(By.XPATH, "//img[@alt='Selecionar Escola']")
                    if i >= len(escolas_links): break
                    
                    link = escolas_links[i]
                    
                    # Tenta pegar o nome da escola antes de clicar (pode estar em uma coluna anterior)
                    # Estrutura: tr -> td (img) ... vamos tentar pegar o texto da linha
                    try:
                        linha_escola = link.find_element(By.XPATH, "./../../..")
                        # O nome geralmente está na segunda ou terceira coluna
                        colunas_escola = linha_escola.find_elements(By.TAG_NAME, "td")
                        # Ajuste conforme a tabela de resultados da busca (geralmente índice 1 ou 2)
                        nome_escola_lista = colunas_escola[1].text.strip() if len(colunas_escola) > 1 else f"Escola {i+1}"
                    except:
                        nome_escola_lista = f"Escola {i+1}"

                    self.log(f"Processando {i+1}/{qtd_processar}: {nome_escola_lista}", "INFO")
                    
                    if self.progress_callback:
                        percent = (i / qtd_processar)
                        self.progress_callback(percent, f"Processando: {nome_escola_lista}")

                    self.driver.execute_script("arguments[0].click();", link)
                    
                    # Aguarda carregar detalhes
                    time.sleep(3) # Wait explícito seria melhor, mas a página é lenta e dinâmica
                    
                    # Tenta pegar o nome oficial dentro da página de detalhes
                    try:
                        nome_escola_detalhe = self.driver.find_element(By.XPATH, "/html/body/div/div[4]/div/table/tbody/tr[1]/td").text.strip()
                    except:
                        nome_escola_detalhe = nome_escola_lista

                    novos_dados = self.extrair_dados_escola(nome_escola_detalhe)
                    self.dados_extraidos.extend(novos_dados)
                    self.log(f"Extraídos {len(novos_dados)} professores de {nome_escola_detalhe}", "SUCESSO")
                    
                    self.driver.back()
                    # Aguarda voltar para a lista
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//img[@alt='Selecionar Escola']"))
                    )
                    time.sleep(1)

                except Exception as e:
                    self.log(f"Erro ao processar escola índice {i}: {e}", "ERRO")
                    self.driver.back() # Tenta recuperar
                    time.sleep(2)
                    continue

        except Exception as e:
            self.log(f"Erro no loop de escolas: {e}", "ERRO")

    def executar(self):
        self.log("=== INICIANDO SCRAPER SIGEDUC ===", "INFO")
        try:
            self.iniciar_driver()
            self.acessar_site()
            self.selecionar_direc()
            self.realizar_busca()
            self.processar_escolas()
            
            self.gerar_json()
            arquivo_html = self.gerar_html()
            
            self.log("=== PROCESSO CONCLUÍDO ===", "SUCESSO")
            return arquivo_html
            
        except Exception as e:
            self.log(f"Erro fatal na execução: {e}", "ERRO")
        finally:
            self.fechar_driver()

    def gerar_json(self):
        arquivo = f"dados_sigeduc_{self.timestamp}.json"
        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(self.dados_extraidos, f, ensure_ascii=False, indent=4)
        self.log(f"Dados exportados para JSON: {arquivo}", "SUCESSO")

    def gerar_html(self):
        arquivo = f"relatorio_sigeduc_{self.timestamp}.html"
        
        # Estatísticas
        total_professores = len(self.dados_extraidos)
        escolas_unicas = list(set(d['escola'] for d in self.dados_extraidos))
        total_escolas = len(escolas_unicas)
        disciplinas_unicas = len(set(d['disciplina'] for d in self.dados_extraidos))
        
        # HTML Template
        html_content = f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Relatório SIGEduc - {self.timestamp}</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css" rel="stylesheet">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
            <style>
                body {{ background-color: #f8f9fa; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
                .dashboard-card {{ transition: transform 0.3s; border: none; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .dashboard-card:hover {{ transform: translateY(-5px); }}
                .card-icon {{ font-size: 2.5rem; opacity: 0.8; }}
                .bg-gradient-primary {{ background: linear-gradient(45deg, #4e73df, #224abe); color: white; }}
                .bg-gradient-success {{ background: linear-gradient(45deg, #1cc88a, #13855c); color: white; }}
                .bg-gradient-info {{ background: linear-gradient(45deg, #36b9cc, #258391); color: white; }}
                .main-header {{ background: white; padding: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 30px; }}
                .table-container {{ background: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
                #tabelaDados_wrapper .row {{ margin-bottom: 10px; }}
            </style>
        </head>
        <body>
            <div class="main-header">
                <div class="container">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h2 class="mb-0 fw-bold text-primary"><i class="fas fa-graduation-cap"></i> Relatório SIGEduc</h2>
                            <p class="text-muted mb-0">Extração de dados de servidores e professores</p>
                        </div>
                        <div class="text-end">
                            <span class="badge bg-light text-dark border">Data: {datetime.now().strftime("%d/%m/%Y")}</span>
                            <span class="badge bg-light text-dark border">Hora: {datetime.now().strftime("%H:%M")}</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="container mb-5">
                <!-- Dashboard -->
                <div class="row mb-4">
                    <div class="col-md-4">
                        <div class="card dashboard-card bg-gradient-primary h-100">
                            <div class="card-body d-flex justify-content-between align-items-center">
                                <div>
                                    <h6 class="text-uppercase mb-1">Total de Professores</h6>
                                    <h2 class="mb-0 fw-bold">{total_professores}</h2>
                                </div>
                                <div class="card-icon"><i class="fas fa-users"></i></div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card dashboard-card bg-gradient-success h-100">
                            <div class="card-body d-flex justify-content-between align-items-center">
                                <div>
                                    <h6 class="text-uppercase mb-1">Escolas Analisadas</h6>
                                    <h2 class="mb-0 fw-bold">{total_escolas}</h2>
                                </div>
                                <div class="card-icon"><i class="fas fa-school"></i></div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card dashboard-card bg-gradient-info h-100">
                            <div class="card-body d-flex justify-content-between align-items-center">
                                <div>
                                    <h6 class="text-uppercase mb-1">Disciplinas Únicas</h6>
                                    <h2 class="mb-0 fw-bold">{disciplinas_unicas}</h2>
                                </div>
                                <div class="card-icon"><i class="fas fa-book"></i></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Tabela -->
                <div class="table-container">
                    <h4 class="mb-4 text-secondary border-bottom pb-2">Detalhamento dos Dados</h4>
                    <div class="table-responsive">
                        <table id="tabelaDados" class="table table-hover table-striped" style="width:100%">
                            <thead class="table-light">
                                <tr>
                                    <th>Escola</th>
                                    <th>Nome</th>
                                    <th>Matrícula</th>
                                    <th>Disciplina</th>
                                    <th>CH</th>
                                    <th>Formação</th>
                                </tr>
                            </thead>
                            <tbody>
        """
        
        for p in self.dados_extraidos:
            html_content += f"""
                                <tr>
                                    <td>{p.get('escola', '')}</td>
                                    <td class="fw-bold text-primary">{p.get('nome', '')}</td>
                                    <td><span class="badge bg-secondary">{p.get('matricula', '')}</span></td>
                                    <td>{p.get('disciplina', '')}</td>
                                    <td>{p.get('ch', '')}h</td>
                                    <td><small class="text-muted">{p.get('formacao', '')[:50]}...</small></td>
                                </tr>
            """
            
        html_content += """
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <footer class="mt-5 text-center text-muted">
                    <small>Gerado automaticamente por SigEduc Scraper - Antigravity Agent</small>
                </footer>
            </div>

            <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
            <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
            <script src="https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js"></script>
            <script>
                $(document).ready(function () {
                    $('#tabelaDados').DataTable({
                        language: {
                            url: '//cdn.datatables.net/plug-ins/1.13.4/i18n/pt-BR.json'
                        },
                        pageLength: 25,
                        responsive: true,
                        dom: '<"row"<"col-md-6"l><"col-md-6"f>>rtip'
                    });
                });
            </script>
        </body>
        </html>
        """
        
        with open(arquivo, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        self.log(f"Relatório HTML gerado: {arquivo}", "SUCESSO")
        return arquivo

if __name__ == "__main__":
    # Configurações
    DIREC = 10
    MAX_ESCOLAS = 3  # Aumentei um pouco para o teste ficar mais interessante
    
    scraper = SigEducScraper(direc_numero=DIREC, max_escolas=MAX_ESCOLAS)
    arquivo_final = scraper.executar()
    
    print(f"\n\n✨ Processo finalizado! Abra o arquivo abaixo para ver o relatório:\n👉 {os.path.abspath(arquivo_final)}")
