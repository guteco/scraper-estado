import streamlit as st
import pandas as pd
import json
import os
import time
from datetime import datetime
from scrap import SigEducScraper

# Configuração da Página
st.set_page_config(
    page_title="SIGEduc Scraper",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo Customizado
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        background-color: #4e73df;
        color: white;
        border-radius: 10px;
        height: 50px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #2e59d9;
        color: white;
        border-color: #2e59d9;
    }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar - Configurações
with st.sidebar:
    # Tenta carregar imagem local, se não existir usa um emoji ou nada
    if os.path.exists("brasao_rn.png"):
        st.image("brasao_rn.png", width=100)
    else:
        st.markdown("# 🦁") # Fallback visual
    st.title("Configurações")
    
    direc_selecionada = st.selectbox(
        "Selecione a DIREC",
        options=list(range(1, 17)),
        index=9, # Default 10ª DIREC (index 9)
        format_func=lambda x: f"{x:02d}ª DIREC"
    )
    
    qtd_escolas = st.number_input(
        "Quantidade de Escolas (0 = Todas)",
        min_value=0,
        max_value=500,
        value=0,
        help="Defina quantas escolas deseja processar. Use 0 para processar todas as encontradas."
    )
    
    headless_mode = st.checkbox("Modo Oculto (Headless)", value=True, help="Executa o navegador em segundo plano, sem abrir a janela.")
    
    st.divider()
    st.info("Desenvolvido por Augusto Severo (@guteco) e Antigravity 🤖")

# Área Principal
st.title("🎓 Extrator de Dados SIGEduc")
st.markdown("Ferramenta automatizada para coleta de dados de servidores e professores da rede estadual de ensino.")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 🚀 Execução")
    
    if st.button("Iniciar Scraping"):
        # Container para logs e progresso
        progress_bar = st.progress(0)
        status_text = st.empty()
        log_expander = st.expander("Logs de Execução", expanded=True)
        log_placeholder = log_expander.empty()
        
        # Lista para acumular logs
        logs_acumulados = []
        
        # Função de callback para atualizar progresso
        def update_progress(percent, message):
            progress_bar.progress(percent)
            status_text.text(message)
            
        # Função de callback para logs em tempo real
        def update_log(message):
            logs_acumulados.append(message)
            # Renderiza logs com scroll e estilo de terminal
            log_content = "<br>".join(logs_acumulados)
            log_placeholder.markdown(
                f"""
                <div style="height: 200px; overflow-y: auto; background-color: #0e1117; color: #4CAF50; padding: 10px; border-radius: 5px; font-family: 'Courier New', monospace; font-size: 12px; border: 1px solid #303030;">
                    {log_content}
                </div>
                <script>
                    var objDiv = document.querySelector("div[style*='overflow-y: auto']");
                    if(objDiv) objDiv.scrollTop = objDiv.scrollHeight;
                </script>
                """,
                unsafe_allow_html=True
            )
        
        # Ajuste do parâmetro max_escolas
        max_escolas_param = qtd_escolas if qtd_escolas > 0 else 9999
        
        try:
            with st.spinner('Inicializando o navegador...'):
                scraper = SigEducScraper(
                    direc_numero=direc_selecionada,
                    max_escolas=max_escolas_param,
                    headless=headless_mode,
                    progress_callback=update_progress,
                    log_callback=update_log
                )
                
                # Redirecionar logs para a interface (opcional, aqui vamos confiar no retorno final)
                # Mas podemos mostrar mensagens chave
                status_text.text("Acessando o sistema...")
                
                # Executar
                arquivo_html = scraper.executar()
                
                # Finalização
                progress_bar.progress(100)
                status_text.success("Processo concluído com sucesso!")
                
                # Salvar dados na sessão para exibição
                st.session_state['dados'] = scraper.dados_extraidos
                st.session_state['arquivo_html'] = arquivo_html
                st.session_state['timestamp'] = scraper.timestamp
                
        except Exception as e:
            st.error(f"Ocorreu um erro durante a execução: {str(e)}")
            
if 'dados' in st.session_state and st.session_state['dados']:
    dados = st.session_state['dados']
    df = pd.DataFrame(dados)
    
    st.divider()
    st.markdown("### 📊 Resultados")
    
    # Filtros
    with st.expander("🔍 Filtros", expanded=True):
        nome_busca = st.text_input("Filtrar por Nome:", placeholder="Digite o nome do professor...")
        
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            disciplinas_unicas = sorted(df['disciplina'].unique())
            disciplinas_selecionadas = st.multiselect(
                "Filtrar por Disciplina:",
                options=disciplinas_unicas,
                default=[],
                placeholder="Selecione as disciplinas..."
            )
            
        with col_f2:
            escolas_unicas = sorted(df['escola'].unique())
            escolas_selecionadas = st.multiselect(
                "Filtrar por Escola:",
                options=escolas_unicas,
                default=[],
                placeholder="Selecione as escolas..."
            )
        
    # Aplicar Filtros
    df_filtered = df.copy()
    
    if nome_busca:
        df_filtered = df_filtered[df_filtered['nome'].str.contains(nome_busca, case=False, na=False)]
    
    if disciplinas_selecionadas:
        df_filtered = df_filtered[df_filtered['disciplina'].isin(disciplinas_selecionadas)]
        
    if escolas_selecionadas:
        df_filtered = df_filtered[df_filtered['escola'].isin(escolas_selecionadas)]
        
    if disciplinas_selecionadas or escolas_selecionadas:
        st.info(f"Exibindo {len(df_filtered)} registros de {len(df)} totais.")
    
    # Remover colunas redundantes para exibição e download
    cols_to_drop = ['direc', 'data_coleta']
    # Garante que só remove se existir
    cols_existing = [c for c in cols_to_drop if c in df_filtered.columns]
    df_final = df_filtered.drop(columns=cols_existing)
    
    # Métricas (Baseadas no DF Filtrado)
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Professores", len(df_final))
    with m2:
        st.metric("Escolas", df_final['escola'].nunique())
    with m3:
        st.metric("Disciplinas", df_final['disciplina'].nunique())
        
    # Tabela
    st.dataframe(df_final)
    
    # Downloads (Baseados no DF Final - sem colunas redundantes)
    c1, c2, c3 = st.columns(3)
    
    # CSV
    csv = df_final.to_csv(index=False).encode('utf-8')
    with c1:
        st.download_button(
            label="📥 Baixar CSV (Filtrado)",
            data=csv,
            file_name=f"sigeduc_filtrado_{st.session_state['timestamp']}.csv",
            mime="text/csv",
        )
        
    # JSON
    json_str = df_final.to_json(orient="records", force_ascii=False, indent=4)
    with c2:
        st.download_button(
            label="📥 Baixar JSON (Filtrado)",
            data=json_str,
            file_name=f"sigeduc_filtrado_{st.session_state['timestamp']}.json",
            mime="application/json",
        )
        
    # HTML Original (Mantém o original completo)
    with open(st.session_state['arquivo_html'], "r", encoding="utf-8") as f:
        html_data = f.read()
    with c3:
        st.download_button(
            label="📥 Baixar Relatório HTML (Completo)",
            data=html_data,
            file_name=os.path.basename(st.session_state['arquivo_html']),
            mime="text/html",
            help="O relatório HTML contém todos os dados coletados, independente dos filtros acima."
        )

else:
    with col2:
        st.info("👆 Configure as opções na barra lateral e clique em 'Iniciar Scraping' para começar.")
