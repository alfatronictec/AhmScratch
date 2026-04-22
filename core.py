import zipfile
import json
import operator

OPERADORES = {
    "operator_add": operator.add,
    "operator_subtract": operator.sub,
}

OPERADOR_SIMBOLO = {
    "operator_add": "+",
    "operator_subtract": "-",
}

OPERADORES_LOGICOS = {
    "operator_gt": ">",
    "operator_lt": "<",
    "operator_equals": "="
}

# ===============================
# LOAD
# ===============================

def load_sb3(path):
    with zipfile.ZipFile(path, "r") as z:
        with z.open("project.json") as f:
            return json.load(f)

# ===============================
# RESOLVER EXPRESSÕES
# ===============================

def resolver_valor(entrada, blocks, variaveis):

    valor = entrada[1]

    if isinstance(valor, list):

        if valor[0] == 10:
            return int(valor[1])

        if valor[0] == 12:
            return variaveis.get(valor[1], 0)

    if isinstance(valor, str):

        bloco = blocks[valor]
        opcode = bloco["opcode"]

        if opcode in OPERADORES:

            a = resolver_valor(bloco["inputs"]["NUM1"], blocks, variaveis)
            b = resolver_valor(bloco["inputs"]["NUM2"], blocks, variaveis)

            return OPERADORES[opcode](a, b)

    return 0

def extrair_nome(entrada, blocks):

    valor = entrada[1]

    if isinstance(valor, list):
        return valor[1]

    if isinstance(valor, str):
        bloco = blocks[valor]
        if "fields" in bloco:
            return bloco["fields"]["VARIABLE"][0]

    return "?"

def resolver_condicao(cond_id, blocks, variaveis):

    bloco = blocks[cond_id]
    opcode = bloco["opcode"]

    if opcode in OPERADORES_LOGICOS:

        a = resolver_valor(bloco["inputs"]["OPERAND1"], blocks, variaveis)
        b = resolver_valor(bloco["inputs"]["OPERAND2"], blocks, variaveis)

        nome_a = extrair_nome(bloco["inputs"]["OPERAND1"], blocks)
        nome_b = extrair_nome(bloco["inputs"]["OPERAND2"], blocks)

        return a, OPERADORES_LOGICOS[opcode], b, nome_a, nome_b

    return None, None, None, None, None

def op_data_setvariableto(bloco, blocks, variaveis, codigo_python):

    variavel = bloco["fields"]["VARIABLE"][0]
    entrada = bloco["inputs"]["VALUE"]

    valor = resolver_valor(entrada, blocks, variaveis)
    variaveis[variavel] = valor

    valor_raw = entrada[1]

    if isinstance(valor_raw, str):
        opcode_op = blocks[valor_raw]["opcode"]

        if opcode_op in OPERADORES:
            simbolo = OPERADOR_SIMBOLO[opcode_op]

            bloco_op = blocks[valor_raw]

            op1 = extrair_nome(bloco_op["inputs"]["NUM1"], blocks)
            op2 = extrair_nome(bloco_op["inputs"]["NUM2"], blocks)

            codigo_python.append(f"vr{simbolo}={variavel}|{op1}|{op2}")
            return

    codigo_python.append(f"v={variavel} = {valor}")


def op_data_showvariable(bloco, blocks, variaveis, codigo_python):

    variavel = bloco["fields"]["VARIABLE"][0]
    codigo_python.append(f"p={variavel}")


def op_control_if(bloco, blocks, variaveis, codigo_python):

    if "CONDITION" not in bloco["inputs"]:
        return  # não é um IF válido

    cond_id = bloco["inputs"]["CONDITION"][1]

    _, op, _, nome_a, nome_b = resolver_condicao(cond_id, blocks, variaveis)

    codigo_python.append(f"i{op}={nome_a}|{nome_b}")
    codigo_python.append("IF_START")

    stack = bloco["inputs"]["SUBSTACK"][1]

    while stack:
        b_stack = blocks[stack]

        OPCODE_HANDLERS[b_stack["opcode"]](
            b_stack, blocks, variaveis, codigo_python
        )

        stack = b_stack["next"]

    codigo_python.append("IF_END")

def op_control_if_else(bloco, blocks, variaveis, codigo_python):

    # Verifica se a condição existe
    if "CONDITION" not in bloco["inputs"]:
        return

    cond_id = bloco["inputs"]["CONDITION"][1]
    _, op, _, nome_a, nome_b = resolver_condicao(cond_id, blocks, variaveis)

    # Gera instrução de comparação
    codigo_python.append(f"i{op}={nome_a}|{nome_b}")
    codigo_python.append("IF_START")

    # =========================
    # BLOCO TRUE (SUBSTACK)
    # =========================
    stack_true = bloco["inputs"].get("SUBSTACK", [None, None])[1]
    while stack_true:
        b_stack = blocks[stack_true]
        handler = OPCODE_HANDLERS.get(b_stack["opcode"])
        if handler:
            handler(b_stack, blocks, variaveis, codigo_python)
        stack_true = b_stack["next"]

    # Marca início do ELSE
    codigo_python.append("ELSE_START")

    # =========================
    # BLOCO FALSE (SUBSTACK2)
    # =========================
    stack_false = bloco["inputs"].get("SUBSTACK2", [None, None])[1]
    while stack_false:
        b_stack = blocks[stack_false]
        handler = OPCODE_HANDLERS.get(b_stack["opcode"])
        if handler:
            handler(b_stack, blocks, variaveis, codigo_python)
        stack_false = b_stack["next"]

    codigo_python.append("IF_END")


OPCODE_HANDLERS = {
    "data_setvariableto": op_data_setvariableto,
    "data_showvariable": op_data_showvariable,
    "control_if": op_control_if,
    "control_if_else": op_control_if_else 
}

def gerar_codigo_python(project):

    codigo_python = []

    for target in project["targets"]:

        blocks = target["blocks"]

        for block_id, block in blocks.items():

            if block["topLevel"]:

                variaveis = {}

                current = block_id

                while current:
                    b = blocks[current]

                    opcode = b["opcode"]

                    if opcode in OPCODE_HANDLERS:
                        OPCODE_HANDLERS[opcode](
                            b, blocks, variaveis, codigo_python
                        )

                    current = b["next"]
    print("codigo_python:\n")
    print(codigo_python)
    return codigo_python