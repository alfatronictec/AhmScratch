import os
import sys
import time
import customtkinter as ctk
from tkinter import filedialog
from PIL import Image, ImageTk, ImageEnhance
from core import load_sb3, gerar_codigo_python
import subprocess
from tkinter import font

# Precisa contar o numero de variaveis para colocar o ORG 128 e ORG 0
# JN Pula se negativo
# JP Pula se positivo

# JZ Pula se valor é zero
# JNZ Pula se valor não é zero


idioma = "pt"
codigo_python = 0

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ===============================
# Configuração do tema
# ===============================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ===============================
# Criação da janela
# ===============================
janela = ctk.CTk()
janela.title("AhmScratch")
janela.iconbitmap(resource_path("images/icon.ico"))
janela.geometry("700x400")
janela.minsize(500, 250)
janela.maxsize(900, 600)
janela.resizable(True, True)

# ===============================
# Funções dos botões
# ===============================
def mostrar_erro(msg):
    label_erro.configure(text=msg)

    # remove depois de 3 segundos (3000 ms)
    janela.after(3000, lambda: label_erro.configure(text=""))

def carregar_zip():
    global codigo_python

    try:
        arquivo_zip = filedialog.askopenfilename(
            title="Selecione um arquivo .sb3",
            filetypes=[("Arquivos Scratch", "*.sb3")]
        )

        if not arquivo_zip:
            return
        
        project = load_sb3(arquivo_zip)
        codigo_python = gerar_codigo_python(project)

        for i in range(101):
            barra_progresso.set(i/100)
            janela.update()
            time.sleep(0.01)
        
        gerar_assembly(codigo_python)
        
        print(f"Arquivo carregado: {arquivo_zip}")

        print("\nGERADO:\n")
        for linha in codigo_python:
            print(linha)

    except KeyError:
        mostrar_erro("Código tem uma variável não definida")

    except Exception as e:
        # Captura qualquer outro erro e exibe na interface
        mostrar_erro(str(e))
        print(f"[ERRO]: {e}")  # Opcional: mantém o log no terminal

# ===============================
# Frame central
# ===============================
frame_central = ctk.CTkFrame(janela, fg_color="transparent")
frame_central.pack(expand=True, fill="both")

# ===============================
# Fundo
# ===============================
imagem_original = Image.open(resource_path("images/plano_fundo.png")).convert("RGBA")
alpha = 0.3
imagem_transparente = Image.blend(imagem_original, Image.new("RGBA", imagem_original.size), 1 - alpha)

bg_image_tk = ImageTk.PhotoImage(imagem_transparente)

label_fundo = ctk.CTkLabel(frame_central, image=bg_image_tk, text="")
label_fundo.place(relx=0.5, rely=0.5, anchor="center")

def atualizar_fundo(event):
    largura = event.width
    altura = event.height

    img = imagem_transparente.resize((largura, altura), Image.Resampling.LANCZOS)
    img_tk = ImageTk.PhotoImage(img)

    label_fundo.configure(image=img_tk)
    label_fundo.image = img_tk

frame_central.bind("<Configure>", atualizar_fundo)

# ===============================
# BARRA + BOTÃO
# ===============================
barra_progresso = ctk.CTkProgressBar(frame_central, width=400, progress_color="#19E912")
barra_progresso.place(relx=0.5, rely=0.3, anchor="center")
barra_progresso.set(0)

digital_font = font.Font(
    family="Digital-7",
    size=20,
    weight="bold"
)

botao_zip = ctk.CTkButton(
    frame_central,
    text="CARREGAR .sb3",
    command=carregar_zip,

    font=("Digital-7", 22),   # fonte estilo display

    fg_color="#1a1a1a",       # fundo escuro (tipo painel)
    hover_color="#2a2a2a",

    text_color="#00FF00",     # verde neon
    corner_radius=6,

    border_width=2,
    border_color="#0f0f0f"
)

botao_zip.place(relx=0.5, rely=0.45, anchor="center")

label_erro = ctk.CTkLabel(
    frame_central,
    text="",
    text_color="#ff4d4d",
    font=("Arial", 14)
)
label_erro.place(relx=0.5, rely=0.55, anchor="center")


def get_base_path():
    caminhos = [
        "C:\\ScratchV",
        os.path.join(os.getenv("LOCALAPPDATA", ""), "ScratchV"),
        os.path.join(os.path.expanduser("~"), "ScratchV")
    ]

    for caminho in caminhos:
        try:
            if caminho:
                os.makedirs(caminho, exist_ok=True)
                return caminho
        except PermissionError:
            continue

    raise Exception("Não foi possível criar diretório em nenhum local.")
    
def get_nome_arquivo():
    nomes = {
        "pt": "codigo_gerado.ahd"
    }
    return nomes.get(idioma, "codigo_gerado.ahd")

def gerar_assembly(codigo_python):

    reg = 0
    ultimo_reg = None
    registradores = {}
    label_id = 0
    stack_labels = []

    pasta_scratchv = get_base_path()
    os.makedirs(pasta_scratchv, exist_ok=True)

    nome_arquivo = get_nome_arquivo()
    caminho_arquivo = os.path.join(pasta_scratchv, nome_arquivo)

    with open(caminho_arquivo, "w", encoding="utf-8") as f:

        f.write("        ORG 128\n\n")

        for linha in codigo_python:

            print(f"[DEBUG LINHA]: '{linha}'")
            
            linha = linha.strip()   # 🔥 CORRETO

            if not linha:
                continue

            if linha.startswith("v="):
                partes = linha.split("=")
                var = partes[1].strip()

                # Verifica se há um valor imediato
                valor = None
                if len(partes) > 2 and partes[2].strip().isdigit():
                    valor = partes[2].strip()

                # Reutiliza registrador se a variável já existir
                if var in registradores:
                    reg_var = registradores[var]
                else:
                    reg_var = reg
                    registradores[var] = reg_var
                    reg += 1

                    if reg > 6:
                        raise Exception(f"Código Ultrapassou o Número de Variáveis Permitido")
                        
                ultimo_reg = reg_var
                
                # Geração do assembly
                if valor is not None:
                    f.write( f"{var}:   DB   {valor}" f"   ; Armazena a variavel {var} com valor inicial {valor} na posição de memoria { 128 + reg_var}\n\n" )

            # =========================
            # SOMA
            # =========================
            elif linha.startswith("vr+"):
                conteudo = linha.split("=", 1)[1].strip()
                var_dest, op1, op2 = [p.strip() for p in conteudo.split("|")]

                if op1 not in registradores or op2 not in registradores:
                    raise Exception(f"Código tem uma Variável não definida")
                    
                r1 = registradores[op1]
                r2 = registradores[op2]

                # Reutiliza registrador do destino
                if var_dest in registradores:
                    reg_dest = registradores[var_dest]
                else:
                    reg_dest = reg
                    registradores[var_dest] = reg_dest
                    reg += 1

                    if reg > 6:
                        raise Exception(f"Código Ultrapassou o Número de Variáveis Permitido")
                        
                
                f.write(f"   add t{reg_dest}, t{r1}, t{r2}              # Soma o valor armazenado em t{r1} com o armazenado em t{r2} e armazena o resultado no registrador t{reg_dest} \n\n")
                ultimo_reg = reg_dest
                
            # =========================
            # SUBTRAÇÃO
            # =========================
            elif linha.startswith("vr-"):
                print("DEBUG SUB:", linha)
                conteudo = linha.split("=", 1)[1].strip()

                # Caso 1: formato ideal → var_dest|var1|var2
                if "|" in conteudo:
                    partes = conteudo.split("|")

                    if len(partes) != 3:
                        raise Exception(f"Formato inválido para subtração")

                    var_dest = partes[0].strip()
                    op1 = partes[1].strip()
                    op2 = partes[2].strip()

                # Caso 2: formato tipo → soma=(var1-var2)
                elif "-" in conteudo:
                    var_dest, expr = conteudo.split("=", 1)
                    var_dest = var_dest.strip()

                    expr = expr.replace("(", "").replace(")", "")
                    op1, op2 = expr.split("-")

                    op1 = op1.strip()
                    op2 = op2.strip()

                else:
                    raise Exception(f"Formato inválido para subtração")


                # Validação das variáveis de origem
                if op1 not in registradores:
                    raise Exception(f"Código tem uma Variável não definida")
                                        
                if op2 not in registradores:
                    raise Exception(f"Código tem uma Variável não definida")

                r1 = registradores[op1]
                r2 = registradores[op2]

                # 🔹 Reutiliza registrador da variável de destino, se existir
                if var_dest in registradores:
                    reg_dest = registradores[var_dest]
                else:
                    reg_dest = reg
                    registradores[var_dest] = reg_dest
                    reg += 1

                    if reg > 1:
                        raise Exception(f"Código Ultrapassou o Número de Variáveis Permitido")
                        
                # Geração do assembly
                f.write(f"   sub t{reg_dest}, t{r1}, t{r2}              # Subtrai o valor armazenado em t{r1} do valor armazenado em t{r2} e armazena no registrador t{reg_dest} \n\n")

                ultimo_reg = reg_dest
            

            # =========================
            # IF IGUAL
            # =========================
            elif linha.startswith("i=="):
                conteudo = linha[len("i=="):].strip()
                var1, var2 = [v.strip() for v in conteudo.split("|")]

                if var1 not in registradores:
                    raise Exception(f"Código tem uma Variável não definida")
                if var2 not in registradores:
                    raise Exception(f"Código tem uma Variável não definida")

                r1 = registradores[var1]
                r2 = registradores[var2]

                label_true = f"SE_IGUAL_{label_id}"
                label_else = f"SE_NAO_IGUAL_{label_id}"
                label_end = f"FIM_SE_{label_id}"

                stack_labels.append({
                    "true": label_true,
                    "else": label_else,
                    "end": label_end,
                    "has_else": False
                })
                label_id += 1

                f.write(f"   beq t{r1}, t{r2}, {label_true}             # Compara os valores armazenados, se t{r1} = t{r2} pula para {label_true}, se nao continua \n")
                f.write(f"   j {label_end}              # Salta para {label_end} se diferente \n\n")
                        
            # =========================
            # IF MAIOR
            # =========================
            elif linha.startswith("i>="):
                conteudo = linha[len("i>="):].strip()
                var1, var2 = [v.strip() for v in conteudo.split("|")]

                if var1 not in registradores:
                    raise Exception(f"Código tem uma Variável não definida")
                if var2 not in registradores:
                    raise Exception(f"Código tem uma Variável não definida")

                r1 = registradores[var1]
                r2 = registradores[var2]

                label_true = f"SE_MAIOR_{label_id}"
                label_else = f"SE_NAO_MAIOR_{label_id}"
                label_end = f"FIM_SE_{label_id}"

                stack_labels.append({
                    "true": label_true,
                    "else": label_else,
                    "end": label_end,
                    "has_else": False
                })
                label_id += 1

                # Se a condição for verdadeira, executa o bloco IF
                # Caso contrário, salta diretamente para o final
                f.write(f"   bgt t{r1}, t{r2}, {label_true}             # Se t{r1} > t{r2}, pula para {label_true}\n")
                f.write(f"   j {label_end}              # Senao, pula para {label_end}\n\n")

            # =========================
            # IF MENOR 
            # =========================
            elif linha.startswith("i<="):
                conteudo = linha[len("i<="):].strip()
                var1, var2 = [v.strip() for v in conteudo.split("|")]

                if var1 not in registradores:
                    raise Exception(f"Código tem uma Variável não definida")
                if var2 not in registradores:
                    raise Exception(f"Código tem uma Variável não definida")

                r1 = registradores[var1]
                r2 = registradores[var2]

                label_true = f"SE_MENOR_{label_id}"
                label_else = f"SE_NAO_MENOR_{label_id}"
                label_end = f"FIM_SE_{label_id}"

                stack_labels.append({
                    "true": label_true,
                    "else": label_else,
                    "end": label_end,
                    "has_else": False
                })
                label_id += 1

                # a <= b  <=>  b >= a
                f.write(f"   blt t{r2}, t{r1}, {label_true}      #Se t{r1} < t{r2}, pula para {label_true} \n\n")
                f.write(f"   j {label_end}      #Senao, pula para {label_end} \n\n")

            elif linha == "IF_START":
                if not stack_labels:
                    raise Exception("IF_START encontrado sem um IF correspondente.")

                labels = stack_labels[-1]
                f.write(f"{labels['true']}:\n")

            elif linha == "ELSE_START":
                # O compilador RISC-V suporta apenas a estrutura IF...THEN.
                # Portanto, a presença de um bloco ELSE é considerada um erro.
                raise Exception(
                    "Bloco 'senão' não é suportado na geração de assembly RISC-V. "
                    "Utilize apenas a estrutura 'se ... então'."
                )

            elif linha == "IF_END":
                if not stack_labels:
                    raise Exception("IF_END encontrado sem um IF correspondente.")

                labels = stack_labels.pop()
                f.write(f"{labels['end']}:\n\n")

            else:
                print("Linha não reconhecida:", linha)
    
    try:
        subprocess.Popen(f'explorer "{pasta_scratchv}"')
    except Exception as e:
        raise Exception(f"Erro ao abrir pasta: {e}")
        
# ===============================
# Executa
# ===============================
janela.mainloop()
