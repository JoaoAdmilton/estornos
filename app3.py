import os
import sqlite3
import random
import smtplib
import ctypes
import threading
import time
from email.message import EmailMessage
import customtkinter as ctk
from fpdf import FPDF
from tkinter import messagebox, font
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Substitua a linha load_dotenv() por estas:
# No início do arquivo, logo após os imports:
load_dotenv("senha.env") 

# E para garantir que ele ache o caminho certo na pasta:
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "senha.env"))
# LINHAS DE TESTE (Pode apagar depois que funcionar)
print(f"DEBUG: Usuário carregado: {os.getenv('EMAIL_USER')}")
print(f"DEBUG: Senha carregada: {os.getenv('EMAIL_PASS')}")

# --- CORREÇÃO DE ESCALA (DPI) ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

# --- CONFIGURAÇÃO ---
ctk.set_appearance_mode("dark")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'meu_mailing.db')

EMAIL_REMETENTE = os.getenv('EMAIL_USER')
SENHA_APP = os.getenv('EMAIL_PASS')

def get_best_font():
    fontes = ["Lucida Handwriting", "Segoe Script", "Arial"]
    disponiveis = font.families()
    for f in fontes:
        if f in disponiveis: return f
    return "Arial"

# --- BACKEND ---
def conectar():
    return sqlite3.connect(DB_PATH)

def inicializar_banco():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contatos(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT, email TEXT, cpf TEXT UNIQUE,
            contrato TEXT, valor_desconto REAL, ritm TEXT,
            data_desconto TEXT, data_limite TEXT,
            status TEXT DEFAULT 'EM ANÁLISE'
        )
    """)
    conn.commit()
    conn.close()

def enviar_email(destino, assunto, corpo):
    if not EMAIL_REMETENTE or not SENHA_APP:
        print("Erro: Credenciais não encontradas no arquivo .env")
        return False

    msg = EmailMessage()
    msg['Subject'] = assunto
    msg['From'] = EMAIL_REMETENTE
    msg['To'] = destino
    msg.set_content(corpo)
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_REMETENTE, SENHA_APP)
            smtp.send_message(msg)
        print(f"SUCESSO: E-mail enviado para {destino}")
        return True
    except Exception as e:
        print(f"--- FALHA NO ENVIO ---")
        print(f"Erro: {e}")
        return False

# --- INTERFACE ---
class AppEmail(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Neon Suporte - Relatório Completo")
        self.geometry("850x620")
        self.minsize(800, 600)
        inicializar_banco()

        threading.Thread(target=self.monitor_automatico, daemon=True).start()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.card = ctk.CTkFrame(self, width=780, height=560, fg_color="#0A0C0E", corner_radius=25, border_width=1, border_color="#1F2326")
        self.card.grid(row=0, column=0, padx=20, pady=20)
        self.card.pack_propagate(False)

        self.logo = ctk.CTkLabel(self.card, text="n", font=(get_best_font(), 70), text_color="#FFFFFF")
        self.logo.pack(pady=(10, 0))
        ctk.CTkLabel(self.card, text="SISTEMA DE GESTÃO E RELATÓRIO", font=("Helvetica", 9, "bold"), text_color="#00E6FF").pack()

        self.input_container = ctk.CTkFrame(self.card, fg_color="transparent")
        self.input_container.pack(fill="x", padx=40, pady=15)
        
        self.entries = {}
        fields = [
            ("NOME COMPLETO", "nome", 0, 0), ("E-MAIL", "email", 0, 1),
            ("CPF", "cpf", 1, 0), ("CONTRATO", "contrato", 1, 1),
            ("VALOR", "valor", 2, 0), ("DATA DESCONTO", "data_desc", 2, 1)
        ]

        for label, key, r, c in fields:
            f = ctk.CTkFrame(self.input_container, fg_color="transparent")
            f.grid(row=r, column=c, padx=15, pady=5, sticky="ew")
            self.input_container.grid_columnconfigure(c, weight=1)
            ctk.CTkLabel(f, text=label, font=("Helvetica", 8, "bold"), text_color="#5D656D").pack(anchor="w")
            e = ctk.CTkEntry(f, height=35, fg_color="#121417", border_color="#1F2326", corner_radius=10)
            e.pack(fill="x")
            self.entries[key] = e
        
        self.entries['data_desc'].insert(0, datetime.now().strftime("%d/%m/%Y"))

        self.btn_add = ctk.CTkButton(self.card, text="REGISTRAR E ANALISAR", command=self.add_contato, 
                                     fg_color="#00E6FF", text_color="#001B1F", font=("Helvetica", 14, "bold"), height=55, corner_radius=15)
        self.btn_add.pack(fill="x", padx=55, pady=20)

        self.btn_pdf = ctk.CTkButton(self.card, text="GERAR RELATÓRIO PDF COMPLETO", command=self.gerar_pdf, 
                                     fg_color="transparent", border_width=1, border_color="#00E6FF", text_color="#00E6FF", height=40, corner_radius=12)
        self.btn_pdf.pack(fill="x", padx=100, pady=(0, 20))

    def monitor_automatico(self):
        while True:
            hoje = datetime.now()
            try:
                conn = conectar()
                cursor = conn.cursor()
                cursor.execute("SELECT id, nome, email, ritm, data_limite FROM contatos WHERE status = 'EM ANÁLISE'")
                pendentes = cursor.fetchall()
                for p in pendentes:
                    id_db, nome, email, ritm, dt_limite_str = p
                    if hoje >= datetime.strptime(dt_limite_str, "%d/%m/%Y"):
                        corpo = (f"Olá {nome.split()[0]},\n\nO prazo de 60 dias para o estorno do chamado {ritm} expirou.\n\n"
                                 f"Caso o valor NÃO tenha sido creditado, por favor, entre em contato conosco "
                                 f"para abertura de chamado externo.")
                        if enviar_email(email, "Atualização: Prazo de Estorno - Neon", corpo):
                            cursor.execute("UPDATE contatos SET status = 'QUESTIONADO' WHERE id = ?", (id_db,))
                conn.commit()
                conn.close()
            except:
                pass
            time.sleep(3600)

    def add_contato(self):
        d = {k: v.get() for k, v in self.entries.items()}
        cpf_digitado = d['cpf'].strip()
        hoje = datetime.now()
        
        try:
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute("SELECT nome, cpf, data_limite, status FROM contatos WHERE cpf = ?", (cpf_digitado,))
            cliente_existente = cursor.fetchone()
            
            if cliente_existente:
                nome, cpf, dt_limite_str, status = cliente_existente
                dt_limite = datetime.strptime(dt_limite_str, "%d/%m/%Y")
                msg = f"Cliente: {nome}\nCPF: {cpf}\n\n" + ("NECESSITA DE ABERTURA DE CHAMADO." if hoje >= dt_limite else f"Status: EM ANÁLISE\nData Limite: {dt_limite_str}")
                conn.close()
                messagebox.showwarning("Duplicidade", msg)
                return

            ritm = f"RITM{random.randint(10000, 99999)}"
            dt_desc = datetime.strptime(d['data_desc'], "%d/%m/%Y")
            dt_limite = dt_desc + timedelta(days=60)
            dt_limite_str = dt_limite.strftime("%d/%m/%Y")
            
            status_ini = "EM ANÁLISE"
            if hoje >= dt_limite:
                status_ini = "QUESTIONADO"
                enviar_email(d['email'], "Abertura de Chamado", f"Olá {d['nome']}, o prazo de 60 dias do chamado {ritm} já se esgotou.")
            else:
                enviar_email(d['email'], f"Chamado {ritm}", f"Olá {d['nome']}, chamado aberto. Prazo: {dt_limite_str}")

            cursor.execute("INSERT INTO contatos (nome, email, cpf, contrato, valor_desconto, ritm, data_desconto, data_limite, status) VALUES (?,?,?,?,?,?,?,?,?)",
                           (d['nome'], d['email'], cpf_digitado, d['contrato'], float(d['valor'].replace(',','.')), ritm, d['data_desc'], dt_limite_str, status_ini))
            conn.commit()
            conn.close()
            messagebox.showinfo("Sucesso", "Registrado!")
            self.limpar()
        except Exception as e: 
            messagebox.showerror("Erro", f"Verifique os dados: {e}")

    def gerar_pdf(self):
        try:
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute("SELECT ritm, nome, contrato, valor_desconto, data_desconto, data_limite, status FROM contatos")
            rows = cursor.fetchall()
            conn.close()
            
            pdf = FPDF(orientation='L')
            pdf.add_page()
            pdf.set_fill_color(0, 27, 31)
            pdf.rect(0, 0, 297, 40, 'F')
            pdf.set_font("Arial", 'B', 30)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 15, "n", ln=True, align='C')
            pdf.set_font("Arial", 'B', 12)
            pdf.set_text_color(0, 230, 255)
            pdf.cell(0, 10, "RELATORIO DETALHADO DE ESTORNOS - NEON", ln=True, align='C')
            pdf.ln(10)
            
            w = [30, 65, 35, 25, 35, 35, 52]
            cols = ["CHAMADO", "CLIENTE", "CONTRATO", "VALOR", "DATA DESC.", "LIMITE 60D", "STATUS"]
            
            pdf.set_fill_color(20, 25, 30)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", 'B', 8)
            for i, c in enumerate(cols):
                pdf.cell(w[i], 12, c, 1, 0, 'C', True)
            pdf.ln()
            
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", '', 8)
            for r in rows:
                for i in range(len(w)):
                    texto = f"R$ {r[i]:.2f}" if i == 3 else str(r[i])
                    pdf.cell(w[i], 10, texto, 1, 0, 'C')
                pdf.ln()
            
            pdf.output("Relatorio_Neon_Completo.pdf")
            messagebox.showinfo("Sucesso", "PDF Gerado!")
        except Exception as e:
            messagebox.showerror("Erro PDF", str(e))

    def limpar(self):
        for e in self.entries.values():
            e.delete(0, 'end')
        self.entries['data_desc'].insert(0, datetime.now().strftime("%d/%m/%Y"))

if __name__ == "__main__":
    app = AppEmail()
    app.mainloop()