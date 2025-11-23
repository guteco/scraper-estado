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
    st.image("https://sigeduc.rn.gov.br/sigeduc/javax.faces.resource/images/brasao_rn.png.jsf?ln=tema", width=100)
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
        value=2,
        help="Defina quantas escolas deseja processar. Use 0 para processar todas as encontradas."
    )
    
    headless_mode = st.checkbox("Modo Oculto (Headless)", value=False, help="Executa o navegador em segundo plano, sem abrir a janela.")
    
    st.divider()
    st.info("Desenvolvido por Antigravity Agent 🤖")

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
        log_container = log_expander.container()
        
        # Função de callback para atualizar progresso
        def update_progress(percent, message):
            progress_bar.progress(percent)
            status_text.text(message)
        
        # Ajuste do parâmetro max_escolas
        max_escolas_param = qtd_escolas if qtd_escolas > 0 else 9999
        
        try:
            with st.spinner('Inicializando o navegador...'):
                scraper = SigEducScraper(
                    direc_numero=direc_selecionada,
                    max_escolas=max_escolas_param,
                    headless=headless_mode,
                    progress_callback=update_progress
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
    
    # Métricas
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Professores Extraídos", len(df))
    with m2:
        st.metric("Escolas Processadas", df['escola'].nunique())
    with m3:
        st.metric("Disciplinas Únicas", df['disciplina'].nunique())
        
    # Tabela
    st.dataframe(df, use_container_width=True)
    
    # Downloads
    c1, c2, c3 = st.columns(3)
    
    # CSV
    csv = df.to_csv(index=False).encode('utf-8')
    with c1:
        st.download_button(
            label="📥 Baixar CSV",
            data=csv,
            file_name=f"sigeduc_{st.session_state['timestamp']}.csv",
            mime="text/csv",
        )
        
    # JSON
    json_str = json.dumps(dados, ensure_ascii=False, indent=4)
    with c2:
        st.download_button(
            label="📥 Baixar JSON",
            data=json_str,
            file_name=f"sigeduc_{st.session_state['timestamp']}.json",
            mime="application/json",
        )
        
    # HTML Original
    with open(st.session_state['arquivo_html'], "r", encoding="utf-8") as f:
        html_data = f.read()
    with c3:
        st.download_button(
            label="📥 Baixar Relatório HTML",
            data=html_data,
            file_name=os.path.basename(st.session_state['arquivo_html']),
            mime="text/html",
        )

else:
    with col2:
        st.info("👆 Configure as opções na barra lateral e clique em 'Iniciar Scraping' para começar.")
