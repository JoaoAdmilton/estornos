import streamlit as st
import sqlite3
import pandas as pd
import os
import smtplib
import random
import bcrypt  # Camada de segurança para senhas
import re
from datetime import datetime, timedelta
from email.message import EmailMessage
from dotenv import load_dotenv

# --- FUNÇÕES DE APOIO ---
def validar_cpf(cpf_string):
    """Remove caracteres especiais e garante exatamente 11 dígitos."""
    cpf_limpo = re.sub(r'\D', '', cpf_string)
    if len(cpf_limpo) == 11:
        return cpf_limpo
    return None

# --- CARREGAR CONFIGURAÇÕES ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Carrega o arquivo específico senha.env para garantir as credenciais de e-mail
load_dotenv(os.path.join(BASE_DIR, "senha.env"))

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Neon Suporte Pro", page_icon="n", layout="centered")

# --- SISTEMA DE LOGIN COM BCRYPT ---
def verificar_senha(senha_digitada):
    """
    Valida a senha digitada contra o Hash seguro.
    Para mudar a senha, gere um novo hash e substitua a string abaixo.
    """
    # Hash atual corresponde a 'admin123'
    hash_seguro = b'$2b$12$d8on5/FF0kik5I6BR1XMrO5BSPHgiTwAoFVhOayYJWgnkcI2J.zXq'
    
    return bcrypt.checkpw(senha_digitada.encode('utf-8'), hash_seguro)

def check_password():
    """Gerencia a sessão de acesso do usuário."""
    if "password_correct" not in st.session_state:
        st.title("n Neon Suporte - Acesso Restrito")
        senha_input = st.text_input("Digite a senha para acessar o sistema", type="password", key="login_pass")
        
        if st.button("Entrar"):
            if verificar_senha(senha_input):
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Senha incorreta Insira credenciais válidas.")
                st.session_state["password_correct"] = False
        return False
    return st.session_state["password_correct"]

# --- CAMADA DE DADOS E SERVIÇOS ---
def init_db():
    conn = sqlite3.connect('neon_web.db')
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contatos(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT, email TEXT, cpf TEXT UNIQUE,
            contrato TEXT, valor REAL, ritm TEXT,
            data_desc TEXT, data_limite TEXT, status TEXT
        )
    """)
    conn.close()

def enviar_email(destino, assunto, corpo):
    user = os.getenv('EMAIL_USER')
    password = os.getenv('EMAIL_PASS')
    if not user or not password:
        return False

    msg = EmailMessage()
    msg['Subject'] = assunto
    msg['From'] = user
    msg['To'] = destino
    msg.set_content(corpo)
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
        return True
    except:
        return False

# --- INTERFACE PRINCIPAL (SÓ ACESSÍVEL APÓS LOGIN) ---
if check_password():
    init_db()

    # Estilização Visual Neon
    st.markdown("""
        <style>
        .stApp { background-color: #0A0C0E; }
        h1 { color: #00E6FF; text-align: center; }
        .stButton>button { width: 100%; background-color: #00E6FF; color: black; font-weight: bold; border-radius: 10px; height: 3em; }
        </style>
    """, unsafe_allow_html=True)

    st.title("n Neon Suporte Pro")
    
    tab1, tab2 = st.tabs(["📝 Novo Registro", "📊 Consultar Base"])

    with tab1:
        st.markdown("### Cadastro de Estorno")
        with st.form("cadastro_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("Nome Completo")
            email = col2.text_input("E-mail")
            cpf_input = col1.text_input("CPF (somente números)")
            contrato = col2.text_input("Nº Contrato")
            valor = col1.number_input("Valor R$", min_value=0.0)
            data_desc = col2.date_input("Data do Desconto", datetime.now())
            
            submit = st.form_submit_button("REGISTRAR E ANALISAR PRAZO")

        if submit:
            cpf_limpo = validar_cpf(cpf_input)
            
            if nome and email and cpf_limpo:
                dt_limite = data_desc + timedelta(days=60)
                dt_lim_str = dt_limite.strftime("%d/%m/%Y")
                ritm = f"RITM{random.randint(10000, 99999)}"
                hoje = datetime.now().date()

                try:
                    conn = sqlite3.connect('neon_web.db')
                    cursor = conn.cursor()
                    
                    # Verificação de Duplicidade usando o CPF higienizado
                    cursor.execute("SELECT nome, status, data_limite FROM contatos WHERE cpf = ?", (cpf_limpo,))
                    duplicado = cursor.fetchone()

                    if duplicado:
                        dt_lim_duplicado = datetime.strptime(duplicado[2], "%d/%m/%Y").date()
                        if hoje >= dt_lim_duplicado:
                            st.warning(f"⚠️ Cliente {duplicado[0]} já possui registro. PRAZO EXPIRADO: NECESSITA DE CHAMADO.")
                        else:
                            st.info(f"ℹ️ Registro existente. Cliente em análise até {duplicado[2]}.")
                    else:
                        # Lógica de automação de status e e-mail
                        status = "EM ANÁLISE"
                        if hoje >= dt_limite:
                            status = "QUESTIONADO"
                            corpo = f"Olá {nome},\n\nO prazo de 60 dias para o estorno expirou. Caso a devolução não tenha ocorrido, entre em contato através do número 0800 943 8585 para abertura de chamado externo."
                        else:
                            corpo = f"Olá {nome},\n\nSeu chamado {ritm} foi registrado com sucesso. O prazo final para análise é {dt_lim_str}."
                        
                        enviar_email(email, f"Status do Chamado Neon - {ritm}", corpo)

                        # Inserção segura no banco
                        cursor.execute("""
                            INSERT INTO contatos (nome, email, cpf, contrato, valor, ritm, data_desc, data_limite, status) 
                            VALUES (?,?,?,?,?,?,?,?,?)
                        """, (nome, email, cpf_limpo, contrato, valor, ritm, data_desc.strftime("%d/%m/%Y"), dt_lim_str, status))
                        
                        conn.commit()
                        st.success(f"📌 {nome} registrado com sucesso! RITM gerado: {ritm}")
                    conn.close()
                except Exception as e:
                    st.error(f"Erro técnico ao acessar o banco: {e}")
            else:
                if not cpf_limpo:
                    st.error("❌ CPF inválido. Certifique-se de digitar os 11 números.")
                else:
                    st.error("⚠️ Preencha todos os campos obrigatórios para continuar.")

    with tab2:
        st.markdown("### Base de Dados em Tempo Real")
        try:
            conn = sqlite3.connect('neon_web.db')
            df = pd.read_sql_query("SELECT ritm, nome, contrato, valor, data_limite, status FROM contatos", conn)
            conn.close()

            if not df.empty:
                busca = st.text_input("🔍 Pesquisar na base (Nome, RITM ou Contrato)")
                if busca:
                    # Filtro dinâmico que ignora maiúsculas/minúsculas
                    df = df[df.apply(lambda row: busca.lower() in row.astype(str).str.lower().values, axis=1)]
                
                st.dataframe(df, use_container_width=True)
                
                # Botão de exportação para CSV
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Baixar Relatório Completo (CSV)", csv, "relatorio_neon_suporte.csv", "text/csv")
            else:
                st.info("A base de dados ainda está vazia.")
        except:
            st.warning("Banco de dados não encontrado ou inicializando...")