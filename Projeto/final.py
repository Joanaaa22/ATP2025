import json
import re
from datetime import datetime
import FreeSimpleGUI as sg
import matplotlib.pyplot as plt
import io
import os
import random
import numpy as np
import copy

# ------------------------
# Configurações Globais e UI
# ------------------------
BDDoentes = []
TABELA_VIEW = []   
MEDICOS_SERVICO = 0

LAST_IMG_FILA = None
LAST_IMG_OCUP = None
LAST_IMG_REL = None
LAST_IMG_BAR_ESTADOS = None
LAST_IMG_PIE_ESP = None

tiposfile = [("JSON (*.json)", "*.json")]
sg.theme("LightGreen8")

COR_PRIMARIA = "#0F6B6B"   
COR_ACENTO = "#F4A742"    
COR_FUNDO_HEADER = "#E7F1F1"

SIDEBAR_BG = "#E9F3F2"      
CARD_BG = "#F6FBFA"         
TXT_DARK = "#1E2E2D"
TXT_MUTED = "#4A5E5C"

BTN_TXT = "white"
BTN_MAIN = COR_PRIMARIA     
BTN_GREEN = "#2E7D32"       
BTN_PURPLE = "#F2701F"      
BTN_GREY = "#445A64"        

PAD_CARD = ((10, 10), (10, 10))
PAD_BTN = ((10, 10), (6, 6))
BTN_SIZE = (18, 2)

PREFIXO_DEFAULT = "HS"
ESTADOS_VALIDOS = ("ATIVO", "INATIVO", "FALECIDO")
ESPECIALIDADES_UI = ["Medicina Geral", "Ortopedia", "Pediatria", "Cardiologia", "Neurologia"]

# ------------------------
# Lógica da Simulação
# ------------------------

PESOS_MEDICOS = {
    "Medicina Geral": 0.4,
    "Ortopedia": 0.2,
    "Pediatria": 0.15,
    "Cardiologia": 0.15,
    "Neurologia": 0.1
}
especialidades = list(PESOS_MEDICOS.keys())
pulseiras_prioridade = ["vermelho", "laranja", "amarela", "verde", "azul"]

CHEGADA = "chegada"
TRIAGEM_INICIO = "triagem_início"
TRIAGEM_SAIDA = "triagem_saída"
CONSULTA_SAIDA = "consulta_saída"

def procuraPosQueue(q, t):
    i = 0
    while i < len(q) and t > q[i][0]:
        i += 1
    return i

def enqueue(q, e):
    pos = procuraPosQueue(q, e[0])
    return q[:pos] + [e] + q[pos:]

def dequeue(q):
    e = q[0]
    return e, q[1:]

def e_tempo(e): return e[0]
def e_tipo(e): return e[1]
def e_doente(e): return e[2]

def verifica_obito(dados_doente):
   
    pul = dados_doente.get("pulseira", "").lower()
    
    if pul != "vermelho":
        return False
    
    try: idade = int(dados_doente.get("idade", 0))
    except: idade = 0
        
    fumador = dados_doente.get("fumador", False)
    if isinstance(fumador, str): fumador = fumador.lower() in ("sim", "s", "true")

    prob_morte = 0.0

    # Cenários de risco
    if fumador and idade > 65:
        prob_morte = 0.15
    elif idade > 65:
        prob_morte = 0.10
    elif fumador:
        prob_morte = 0.08
    else:
        prob_morte = 0.05

    return random.random() < prob_morte

def gerar_tempo_distribuicao(tipo_dist, media):
    val = 0.0
    if tipo_dist == "Normal":
        val = np.random.normal(loc=media, scale=media*0.25)
    elif tipo_dist == "Uniforme":
        val = np.random.uniform(low=media*0.5, high=media*1.5)
    else: 
        val = np.random.exponential(scale=media)
    return max(0.1, val)

def simula_eventos(
    taxa_chegada_h=10,
    tempo_simulacao_min=480, 
    num_medicos=6,
    num_enfermeiros_triagem=1,
    tempo_medio_triagem=7, 
    tempo_medio_consulta=15, 
    tipo_distribuicao="Exponencial", 
    max_sala_espera_por_esp=12, 
    pessoas_db=None, 
    lista_bd_global=None 
):
   

    tempo_atual = 0.0
    queueEventos = []
    fila_pre_triagem = [] 
    
    def cria_fila_espera_consulta():
        return {
            esp: {pul: [] for pul in pulseiras_prioridade[::-1]} 
            for esp in especialidades
        }
    
    fila_espera_consulta = cria_fila_espera_consulta()

    def gera_medicos(n):
        meds = []
        count = 0
        if n >= len(especialidades):
            for esp in especialidades:
                count += 1
                meds.append([f"m{count}", esp, False, None, 0.0, 0.0])
        
        while count < n:
            esp = random.choices(especialidades, weights=list(PESOS_MEDICOS.values()), k=1)[0]
            count += 1
            meds.append([f"m{count}", esp, False, None, 0.0, 0.0])
        return meds
    
    def gera_enfermeiros(n):
        return [[f"t{i+1}", False, None] for i in range(n)]

    medicos = gera_medicos(num_medicos)
    enfermeiros = gera_enfermeiros(n=num_enfermeiros_triagem)
    estado = {}

    tempos_hist = []
    triagem_hist = []
    consulta_hist = []
    ocupacao_hist = []

    def regista(t):
        t_cons = sum(len(fila_espera_consulta[esp][pul]) for esp in especialidades for pul in pulseiras_prioridade)
        t_tri = len(fila_pre_triagem)
        t_doc = sum(1 for m in medicos if m[2])
        tempos_hist.append(t)
        triagem_hist.append(t_tri)
        consulta_hist.append(t_cons)
        ocupacao_hist.append(t_doc)

    def procuraMedicoLivre(esp):
        for m in medicos:
            if m[1] == esp and m[2] is False:
                return m
        return None

    def procuraEnfermeiroLivre():
        for t in enfermeiros:
            if t[1] is False:
                return t
        return None

    lam_per_min = taxa_chegada_h / 60.0
    t_corrente = 0.0
    
    if pessoas_db and len(pessoas_db) > 0:
        ids_do_json = list(pessoas_db.keys())
        random.shuffle(ids_do_json)
        
        for db_id in ids_do_json:
            t_corrente += np.random.exponential(1 / lam_per_min)
            queueEventos = enqueue(queueEventos, (t_corrente, CHEGADA, db_id))
    else:
        pass 

    regista(0.0)
    doentes_atendidos = 0
    obitos_simulados = 0

    def gera_especialidade_prevista(doente_id):
        if pessoas_db and doente_id in pessoas_db:
            p = pessoas_db.get(doente_id)
            if p:
                try: idade = int(p.get("idade", 99))
                except: idade = 99
                
                if idade < 18: return "Pediatria"
                else:
                    pess_adulto = {k: v for k, v in PESOS_MEDICOS.items() if k != "Pediatria"}
                    pesos_adulto = list(pess_adulto.values())
                    esp_adulto = list(pess_adulto.keys())
                    if pesos_adulto:
                        return random.choices(esp_adulto, weights=pesos_adulto, k=1)[0]
        return "Medicina Geral"

    def sala_tem_espaco(esp):
        atual = sum(len(fila_espera_consulta[esp][pul]) for pul in pulseiras_prioridade)
        return atual < max_sala_espera_por_esp

    def prox_doente(esp):
        for pul in pulseiras_prioridade:
            if fila_espera_consulta[esp][pul]:
                return fila_espera_consulta[esp][pul].pop(0)
        return None

    def tenta_iniciar_triagem(t_now, q_ev):
        enf_livre = procuraEnfermeiroLivre()
        if not enf_livre or not fila_pre_triagem: return q_ev
        
        t_cheg, d_id = fila_pre_triagem[0]
        esp_prev = gera_especialidade_prevista(d_id)
        
        if not sala_tem_espaco(esp_prev): return q_ev
        
        fila_pre_triagem.pop(0)
        enf_livre[1] = True 
        enf_livre[2] = d_id
        
        estado[d_id] = {"especialidade_prevista": esp_prev}
        
        t_tri = gerar_tempo_distribuicao(tipo_distribuicao, tempo_medio_triagem)
        
        q_ev = enqueue(q_ev, (t_now, TRIAGEM_INICIO, d_id))
        q_ev = enqueue(q_ev, (t_now + t_tri, TRIAGEM_SAIDA, d_id))
        return q_ev

    def tenta_iniciar_consulta(t_now, d_id, q_ev):
        esp = estado[d_id]["especialidade"]
        med = procuraMedicoLivre(esp)
        if med:
            med[2] = True 
            med[3] = d_id
            med[5] = t_now
            
            t_cons = gerar_tempo_distribuicao(tipo_distribuicao, tempo_medio_consulta)
            
            q_ev = enqueue(q_ev, (t_now + t_cons, CONSULTA_SAIDA, d_id))
        else:
            pul = random.choices(pulseiras_prioridade, weights=[0.20, 0.20, 0.20, 0.20, 0.20], k=1)[0]
            estado[d_id]["pulseira"] = pul
            fila_espera_consulta[esp][pul].append((t_now, d_id))
        return q_ev

    while queueEventos:
        evento, queueEventos = dequeue(queueEventos)
        t_now = e_tempo(evento)
        
        if t_now > tempo_simulacao_min:
            break
            
        tipo = e_tipo(evento)
        d_id = e_doente(evento)

        if tipo == CHEGADA:
            fila_pre_triagem.append((t_now, d_id))
            queueEventos = tenta_iniciar_triagem(t_now, queueEventos)
            regista(t_now)
        
        elif tipo == TRIAGEM_INICIO:
            regista(t_now)

        elif tipo == TRIAGEM_SAIDA:
            for enf in enfermeiros:
                if enf[2] == d_id:
                    enf[1] = False
                    enf[2] = None
                    break
            
            esp = estado[d_id]["especialidade_prevista"]
            estado[d_id]["especialidade"] = esp
            
            queueEventos = tenta_iniciar_consulta(t_now, d_id, queueEventos)
            queueEventos = tenta_iniciar_triagem(t_now, queueEventos)
            regista(t_now)

        elif tipo == CONSULTA_SAIDA:
            doentes_atendidos += 1
            pul_triagem = estado[d_id].get("pulseira", "verde")
            esp = estado[d_id]["especialidade"]
            morreu = False
            
            if pessoas_db and d_id in pessoas_db:
                p_bd = pessoas_db.get(d_id)
                if p_bd:
                    try: idade_real = int(p_bd.get("idade", 0))
                    except: idade_real = 0
                    fumador_real = obter_fumador(p_bd)
                    
                    
                    p_bd["timestamp_atendimento"] = t_now
                    
                    
                    morreu = verifica_obito({"idade": idade_real, "fumador": fumador_real, "pulseira": pul_triagem})
                    
                    if morreu:
                        p_bd["estado"] = "FALECIDO"
                        p_bd["auditoria"].append({"ts": agora_str(), "acao": "OBITO_SIMULADO", "detalhes": "Faleceu após consulta"})
                    
                    p_bd["especialidade"] = esp
                    p_bd["pulseira"] = pul_triagem

            if morreu:
                obitos_simulados += 1

            med_atual = None
            for m in medicos:
                if m[3] == d_id:
                    med_atual = m
                    break
            
            if med_atual:
                med_atual[2] = False
                med_atual[3] = None
                med_atual[4] += (t_now - med_atual[5])
                
                esp = med_atual[1]
                prox = prox_doente(esp)
                if prox:
                    _, d_prox = prox
                    med_atual[2] = True
                    med_atual[3] = d_prox
                    med_atual[5] = t_now
                    
                    t_cons = gerar_tempo_distribuicao(tipo_distribuicao, tempo_medio_consulta)
                    
                    queueEventos = enqueue(queueEventos, (t_now + t_cons, CONSULTA_SAIDA, d_prox))
            
            queueEventos = tenta_iniciar_triagem(t_now, queueEventos)
            regista(t_now)

    return tempos_hist, triagem_hist, consulta_hist, ocupacao_hist, doentes_atendidos, obitos_simulados


# ------------------------
# Funções Auxiliares
# ------------------------
def agora_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def garantir_auditoria(d):
    if "auditoria" not in d or not isinstance(d.get("auditoria"), list):
        d["auditoria"] = []

def add_audit(d, acao, detalhes=""):
    garantir_auditoria(d)
    d["auditoria"].append({"ts": agora_str(), "acao": str(acao), "detalhes": str(detalhes)})

def carregarBDDoentes(caminho):
    with open(caminho, "r", encoding="utf-8") as f:
        dados = json.load(f)
    if isinstance(dados, dict) and "doentes" in dados:
        dados = dados["doentes"]
    if not isinstance(dados, list): return []
    garantir_t_doente(dados)
    garantir_campos_gestao(dados)
    for d in dados:
        if isinstance(d, dict): garantir_auditoria(d)
    return dados

def guardarBDDoentes(caminho, bd):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(bd, f, ensure_ascii=False, indent=2)

def fumador_para_bool(valor):
    if isinstance(valor, bool): return valor
    if isinstance(valor, (int, float)): return valor != 0
    if isinstance(valor, str):
        v = valor.strip().lower()
        return v in ("sim", "s", "true", "1", "yes", "y")
    return False

def obter_fumador(d):
    attrs = d.get("atributos", {})
    if isinstance(attrs, dict) and "fumador" in attrs:
        return fumador_para_bool(attrs.get("fumador"))
    for k in ("fumador", "Fumador", "smoker", "Smoker"):
        if k in d: return fumador_para_bool(d.get(k))
    return False

def extrair_numero_t_doente(t):
    if not isinstance(t, str): return None
    m = re.match(r"^(HS|PRO|SIM)-(\d+)$", t.strip().upper())
    if not m: return None
    return int(m.group(2))

def proximo_numero_global(bd):
    if not bd: return 1
    max_num = 0
    for d in bd:
        if not isinstance(d, dict): continue
        n = extrair_numero_t_doente(d.get("T_doente"))
        if n is not None and n > max_num: max_num = n
    return max_num + 1

def gerar_t_doente(prefixo, numero):
    prefixo = (prefixo or PREFIXO_DEFAULT).strip().upper()
    if prefixo not in ("HS", "PRO", "SIM"): prefixo = PREFIXO_DEFAULT
    return f"{prefixo}-{int(numero)}"

def garantir_t_doente(bd):
    prox = proximo_numero_global(bd)
    for d in bd:
        if not isinstance(d, dict): continue
        if extrair_numero_t_doente(d.get("T_doente")) is None:
            d["T_doente"] = gerar_t_doente(PREFIXO_DEFAULT, prox)
            prox += 1

def garantir_campos_gestao(bd):
    for d in bd:
        if not isinstance(d, dict): continue
        estado = str(d.get("estado", "ATIVO")).strip().upper()
        if estado not in ESTADOS_VALIDOS: estado = "ATIVO"
        d["estado"] = estado

def inserirDoente(bd, prefixo, nome, idade, fumador, pul, esp):
    num = proximo_numero_global(bd)
    novo = {
        "T_doente": gerar_t_doente(prefixo, num),
        "nome": nome.strip(),
        "idade": int(idade),
        "atributos": {"fumador": bool(fumador)},
        "pulseira": pul,
        "especialidade": esp.strip(),
        "estado": "ATIVO",
        "auditoria": []
    }
    add_audit(novo, "CRIADO", f"Criado doente {novo['T_doente']}")
    bd.append(novo)

def encontrar_doente_por_t(bd, t_doente):
    for d in bd:
        if isinstance(d, dict) and d.get("T_doente") == t_doente: return d
    return None

def marcar_falecido(bd, t_doente):
    d = encontrar_doente_por_t(bd, t_doente)
    if not d: return False
    if d.get("estado") == "FALECIDO": return True
    d["estado"] = "FALECIDO"
    add_audit(d, "ESTADO", "Marcado como FALECIDO")
    return True

def alternar_ativo_inativo(bd, t_doente):
    d = encontrar_doente_por_t(bd, t_doente)
    if not d: return False
    if d.get("estado") == "FALECIDO": return False
    novo = "INATIVO" if d.get("estado") == "ATIVO" else "ATIVO"
    d["estado"] = novo
    add_audit(d, "ESTADO", f"Alterado para {novo}")
    return True

def filtrar_doentes(bd, termo):
    termo = (termo or "").strip().lower()
    if termo == "": return list(bd)
    out = []
    for d in bd:
        if not isinstance(d, dict): continue
        campos = [str(d.get("T_doente", "")), str(d.get("nome", "")), str(d.get("idade", "")), str(obter_fumador(d)), str(d.get("pulseira", "")), str(d.get("especialidade", "")), str(d.get("estado", ""))]
        if any(termo in c.lower() for c in campos): out.append(d)
    return out

def ordenar_por_atendimento(bd):
    """Ordena a BD: primeiro os atendidos (por ordem de tempo), depois os não atendidos."""
    atendidos = []
    outros = []
    
    for d in bd:
        if not isinstance(d, dict): continue
        
        if "timestamp_atendimento" in d and d["timestamp_atendimento"] is not None:
            atendidos.append(d)
        else:
            outros.append(d)
            
    atendidos.sort(key=lambda x: x["timestamp_atendimento"])
    
   
    outros.sort(key=lambda x: extrair_numero_t_doente(x.get("T_doente")) or 0)
    
    return atendidos + outros

def tabela_de_doentes(bd):
    valores = []
    for d in bd:
        if not isinstance(d, dict): continue
        valores.append([d.get("T_doente", ""), d.get("nome", ""), d.get("idade", ""), "Sim" if obter_fumador(d) else "Não", d.get("pulseira", ""), d.get("especialidade", ""), d.get("estado", "ATIVO")])
    return valores

# ------------------------
# Janelas
# ------------------------
def janela_inserir_doente():
    layout = [
        [sg.Text("Inserir Doente", font=("Segoe UI", 16, "bold"))],
        [sg.Text("Prefixo (HS/PRO):", size=(18, 1)), sg.Input(default_text=PREFIXO_DEFAULT, key="-PFX-", size=(10, 1))],
        [sg.Text("Nome:", size=(18, 1)), sg.Input(key="-NOME-", size=(30, 1))],
        [sg.Text("Idade:", size=(18, 1)), sg.Input(key="-IDADE-", size=(10, 1))],
        [sg.Text("Fumador:", size=(18, 1)), sg.Combo(["Não", "Sim"], default_value="Não", readonly=True, key="-FUM-")],
        [sg.Text("Pulseira:", size=(18, 1)), sg.Combo(["vermelho", "laranja", "amarela", "verde", "azul"], default_value="verde", readonly=True, key="-PUL-")],
        [sg.Text("Especialidade:", size=(18, 1)), sg.Combo(ESPECIALIDADES_UI, default_value=ESPECIALIDADES_UI[0], readonly=True, key="-ESP-")],
        [sg.Button("Inserir", button_color=("white", "#2E7D32")), sg.Button("Cancelar")],
    ]
    w = sg.Window("Inserir Doente", layout, modal=True, finalize=True)
    while True:
        ev, vals = w.read()
        if ev in (sg.WIN_CLOSED, "Cancelar"): w.close(); return None
        if ev == "Inserir":
            try:
                nome = vals["-NOME-"].strip()
                idade = int(vals["-IDADE-"])
                if nome == "" or idade < 0: raise ValueError
                return vals["-PFX-"].strip().upper(), nome, idade, vals["-FUM-"] == "Sim", vals["-PUL-"], vals["-ESP-"]
            except Exception: sg.popup("Dados inválidos."); return None

def janela_ficha_doente(d):
    garantir_auditoria(d)
    cidade, distrito = (d.get("morada", {}).get("cidade", ""), d.get("morada", {}).get("distrito", ""))
    
    col_esq = [
        [sg.Text("T_doente:", size=(12, 1)), sg.Text(d.get("T_doente", ""), text_color=COR_PRIMARIA)],
        [sg.Text("Nome:", size=(12, 1)), sg.Input(d.get("nome", ""), key="-F_NOME-", size=(35, 1))],
        [sg.Text("Idade:", size=(12, 1)), sg.Input(str(d.get("idade", "")), key="-F_IDADE-", size=(10, 1))],
        [sg.Text("Fumador:", size=(12, 1)), sg.Combo(["Não", "Sim"], default_value="Sim" if obter_fumador(d) else "Não", readonly=True, key="-F_FUM-", size=(8, 1))],
    ]
    col_dir = [
        [sg.Text("Pulseira:", size=(12, 1)), sg.Combo(["vermelho", "laranja", "amarela", "verde", "azul"], default_value=d.get("pulseira", "verde"), readonly=True, key="-F_PUL-", size=(12, 1))],
        [sg.Text("Especialidade:", size=(12, 1)), sg.Combo(ESPECIALIDADES_UI, default_value=d.get("especialidade", ESPECIALIDADES_UI[0]), readonly=True, key="-F_ESP-", size=(18, 1))],
        [sg.Text("Estado:", size=(12, 1)), sg.Text(d.get("estado", "ATIVO"))],
    ]
    sec_principal = sg.Frame("Dados Principais", [[sg.Column(col_esq), sg.VSep(), sg.Column(col_dir)]], expand_x=True)
    sec_extras = sg.Frame("Morada & Extras", [[sg.Text("Cidade:", size=(12, 1)), sg.Input(cidade, key="-F_CIDADE-", size=(25, 1)), sg.Text("Distrito:", size=(10, 1)), sg.Input(distrito, key="-F_DISTRITO-", size=(25, 1))], [sg.Text("Profissão:", size=(12, 1)), sg.Input(d.get("profissao", ""), key="-F_PROF-", size=(40, 1)), sg.Text("Documento:", size=(10, 1)), sg.Input(d.get("CC", d.get("BI", "")), key="-F_DOC-", size=(25, 1))], [sg.Text("Desportos:", size=(18, 1)), sg.Input(str(d.get("desportos", [])).replace("[","").replace("]","").replace("'", ""), key="-F_DESPORTOS-", size=(60, 1))], [sg.Text("Animais:", size=(18, 1)), sg.Input(str(d.get("animais", [])).replace("[","").replace("]","").replace("'", ""), key="-F_ANIMAIS-", size=(60, 1))], [sg.Text("Descrição:", size=(12, 1)), sg.Multiline(d.get("descrição", ""), key="-F_DESC-", size=(75, 4))]], expand_x=True)
    
    def auditoria_formatada(d):
        aud = d.get("auditoria", [])
        if not aud: return "Sem histórico."
        return "\n".join([f"{a.get('ts','')} | {a.get('acao','')} | {a.get('detalhes','')}" for a in aud[-100:]])

    sec_auditoria = sg.Frame("Auditoria", [[sg.Multiline(default_text=auditoria_formatada(d), size=(90, 10), disabled=True, key="-F_AUD-")]], expand_x=True)

    layout = [[sg.Column([[sg.Text("Ficha do Doente", font=("Segoe UI", 16, "bold"))], [sec_principal], [sec_extras], [sec_auditoria]], scrollable=True, vertical_scroll_only=True)], [sg.Button("Guardar", button_color=("white", COR_PRIMARIA)), sg.Button("Fechar")]]

    w = sg.Window("Ficha do Doente", layout, modal=True, finalize=True, resizable=True)
    alterou = False
    while True:
        ev, vals = w.read()
        if ev in (sg.WIN_CLOSED, "Fechar"): break
        if ev == "Guardar":
            antes = {k: d.get(k) for k in ["nome", "idade", "especialidade", "morada", "profissao", "desportos", "animais", "descrição"]}
            
            d["nome"] = vals["-F_NOME-"]
            try: d["idade"] = int(vals["-F_IDADE-"])
            except: pass
            d["atributos"]["fumador"] = vals["-F_FUM-"] == "Sim"
            d["pulseira"] = vals["-F_PUL-"]
            d["especialidade"] = vals["-F_ESP-"]
            if not isinstance(d.get("morada"), dict): d["morada"] = {}
            d["morada"]["cidade"] = vals["-F_CIDADE-"]; d["morada"]["distrito"] = vals["-F_DISTRITO-"]
            d["profissao"] = vals["-F_PROF-"]
            d["CC"] = vals["-F_DOC-"]
            d["desportos"] = [x.strip() for x in vals["-F_DESPORTOS-"].split(",") if x.strip()]
            d["animais"] = [x.strip() for x in vals["-F_ANIMAIS-"].split(",") if x.strip()]
            d["descrição"] = vals["-F_DESC-"]

            diffs = {k: antes[k] for k in antes if antes[k] != d.get(k)}
            if diffs:
                add_audit(d, "EDIT_FICHA", diffs)
                alterou = True
                w["-F_AUD-"].update(auditoria_formatada(d))
                sg.popup("Ficha guardada ✅")
            else: sg.popup("Sem alterações.")
    w.close()
    return alterou

def _fig_to_bytes(fig):
    bio = io.BytesIO()
    fig.tight_layout()
    fig.savefig(bio, format="png", dpi=150)
    plt.close(fig)
    return bio.getvalue()

def grafico_barras_atendidos_falecidos(bd):
    if not bd: 
        fig = plt.figure(figsize=(6, 4))
        plt.text(0.5, 0.5, "BD Vazia", ha='center')
        return _fig_to_bytes(fig)
        
    
    falecidos = sum(1 for d in bd if isinstance(d, dict) and str(d.get("estado", "")).upper() == "FALECIDO")
    
    
    atendidos = sum(1 for d in bd 
                   if isinstance(d, dict) 
                   and "timestamp_atendimento" in d 
                   and d["timestamp_atendimento"] is not None
                   and str(d.get("estado", "")).upper() in ("ATIVO", "INATIVO"))
                   
    fig = plt.figure(figsize=(6, 4))
    plt.bar(["Atendidos (Vivos)", "Falecidos"], [atendidos, falecidos], color=['#2E7D32', '#F2701F'])
    plt.title("Resultados da Simulação")
    plt.ylabel("Nº de pessoas")
    for i, v in enumerate([atendidos, falecidos]):
        plt.text(i, v, str(v), ha='center', va='bottom')
    return _fig_to_bytes(fig)

def grafico_circular_pulseiras_por_especialidade(bd):
    if not bd: 
        fig = plt.figure(figsize=(7, 4))
        plt.text(0.5, 0.5, "BD Vazia", ha='center')
        return _fig_to_bytes(fig)

    cont = {}
    for d in bd:
        if not isinstance(d, dict): continue
        
        if not ("timestamp_atendimento" in d and d["timestamp_atendimento"] is not None):
            continue
            
        estado = str(d.get("estado", "")).upper()
        if estado == "FALECIDO": continue 
        
        esp = (d.get("especialidade") or "").strip()
        if not esp or esp == "Sem esp" or esp == "": continue
        cont[esp] = cont.get(esp, 0) + 1
        
    fig = plt.figure(figsize=(7, 4))
    if not cont: 
        plt.text(0.5, 0.5, "Sem dados (Doentes Atendidos)", ha="center")
        plt.axis("off")
    else:
        plt.pie(list(cont.values()), labels=list(cont.keys()), autopct="%1.0f%%")
        plt.title("Doentes Atendidos por Especialidade")
    return _fig_to_bytes(fig)

def abrir_grafico_em_janela_bytes(titulo, img_bytes):
    layout = [[sg.Text(titulo, font=("Segoe UI", 14, "bold"))], [sg.Image(data=img_bytes, key="-IMG-")], [sg.Button("Fechar")]]
    win = sg.Window(titulo, layout, modal=True, resizable=True, finalize=True)
    while True:
        ev, _ = win.read()
        if ev in ("Fechar", sg.WIN_CLOSED): break
    win.close()

# ------------------------
# Layouts
# ------------------------
layout_sidebar = [
    [sg.Text("GESTÃO", font=("Segoe UI", 14, "bold"), background_color=SIDEBAR_BG, text_color=TXT_DARK)],
    [sg.Frame("Ficheiro", [[sg.Button("Carregar BD", size=(10, 2), button_color=(BTN_TXT, BTN_GREY)), sg.Button("Guardar BD", size=(10, 2), button_color=(BTN_TXT, BTN_MAIN))]], background_color=CARD_BG)],
    [sg.Frame("Operações", [[sg.Button("Inserir Doente", size=BTN_SIZE, button_color=(BTN_TXT, BTN_GREEN)), sg.Button("Marcar Falecido", size=BTN_SIZE, button_color=("white", COR_ACENTO)), sg.Button("Ativar/Desativar", size=BTN_SIZE, button_color=("white", BTN_GREY))]], background_color=CARD_BG)],
]

layout_consulta_main = [
    [sg.Text("Pesquisa Rápida:", font=("Segoe UI", 11)), sg.Input(key="-BUSCA-", size=(30, 1)), sg.Button("Consultar"), sg.Button("Mostrar Todos"), sg.Button("Abrir Ficha", key="-ABRIR_FICHA-")],
    [sg.Table(values=[["-", "-", "-", "-", "-", "-", "-"]], headings=["T_doente", "Nome", "Idade", "Fumador", "Pulseira", "Especialidade", "Estado"], auto_size_columns=True, display_row_numbers=True, num_rows=25, key="-TABELA-", enable_events=True, select_mode=sg.TABLE_SELECT_MODE_EXTENDED, expand_x=True, expand_y=True, alternating_row_color="#D9EEF7")]
]

layout_consulta = [[sg.Column(layout_sidebar, vertical_alignment="top", background_color=SIDEBAR_BG), sg.VSeparator(), sg.Column(layout_consulta_main, expand_x=True, expand_y=True)]]

layout_stats = [
    [
        sg.Column([
            [sg.Frame("Parâmetros", [
                [sg.Text("Taxa de chegada (doentes/hora):")],
                [sg.Slider(range=(10, 30), default_value=10, orientation="h", size=(22, 15), key="-SIM_LAMBDA-")],
                
                [sg.Text("Tempo Simulação (min):"), sg.Input(default_text="480", key="-SIM_TEMPO-", size=(10,1))],
                [sg.Text("Nº Enfermeiros (Triagem):"), sg.Spin(values=list(range(1, 11)), initial_value=1, key="-SIM_ENF-")],
                
                [sg.Text("Nº médicos:"), sg.Spin(values=list(range(1, 21)), initial_value=6, key="-SIM_MEDICOS-")],
                [sg.Text("Capacidade sala de espera (esp):"), sg.Spin(values=list(range(5, 51, 5)), initial_value=12, key="-SIM_CAP-")],
                
                [sg.HorizontalSeparator()],
                [sg.Text("Tipo de Distribuição:", font=("Segoe UI", 9, "bold"))],
                [sg.Combo(["Exponencial", "Normal", "Uniforme"], default_value="Exponencial", key="-SIM_DIST-", readonly=True, size=(15, 1))],
                [sg.Text("Tempo Médio Consulta (min):")],
                [sg.Input(default_text="15", key="-SIM_T_CONS-", size=(10,1))],
                
                [sg.Text("")],
                [sg.Button("Executar Simulação", key="-RUN_SIM-", button_color=("white", COR_PRIMARIA), size=(20, 1))]
            ])]
        ], vertical_alignment="top"),
        
        sg.VSep(),
        
        sg.Column([
            [sg.Frame("Gráficos", [
                [sg.Button("Abrir: Fila de espera", key="-OPEN_FILA-", button_color=("white", COR_ACENTO), size=(20, 1))],
                [sg.Button("Abrir: Ocupação médicos", key="-OPEN_OCUP-", button_color=("white", COR_ACENTO), size=(20, 1))],
                [sg.Button("Abrir: Fila vs Taxa", key="-OPEN_REL-", button_color=("white", COR_ACENTO), size=(20, 1))],
                [sg.HorizontalSeparator()],
                [sg.Button("Abrir: Atendidos vs Falecidos", key="-OPEN_BAR_EST-", button_color=("white", COR_ACENTO), size=(20, 1))],
                [sg.Button("Abrir: Pulseiras por Especialidade", key="-OPEN_PIE_ESP-", button_color=("white", COR_ACENTO), size=(20, 1))]
            ])],
            [sg.Frame("Estado / Mensagens", [
                [sg.Multiline(
                    default_text="1) Ajusta os parâmetros\n2) Clica em 'Executar Simulação'\n3) Usa os botões 'Abrir' para ver os gráficos",
                    size=(70, 15), disabled=True, key="-SIM_STATUS-"
                )]
            ])]
        ], expand_x=True, vertical_alignment="top")
    ]
]

try:
    BASE_DIR = os.getcwd()
    LOGO_PATH = os.path.join(BASE_DIR, "logo_circle.png")
    if os.path.exists(LOGO_PATH): header_logo = sg.Image(filename=LOGO_PATH, subsample=5, background_color=COR_FUNDO_HEADER)
    else: header_logo = sg.Text("LOGO", background_color=COR_FUNDO_HEADER)
except: header_logo = sg.Text("LOGO", background_color=COR_FUNDO_HEADER)

header = [[header_logo, sg.Text("HOSPITAL", font=("Segoe UI", 22, "bold"), text_color=COR_PRIMARIA, background_color=COR_FUNDO_HEADER)]]

layout = [[sg.Column(header, background_color=COR_FUNDO_HEADER, expand_x=True)], [sg.TabGroup([[sg.Tab("Listagem e Consulta", layout_consulta), sg.Tab("Relatórios", layout_stats)]], expand_x=True, expand_y=True)]]

window = sg.Window("Hospital Manager v1.0", layout, resizable=True, finalize=True)

def refresh_table(view_bd):
    global TABELA_VIEW
    TABELA_VIEW = list(view_bd)
    window["-TABELA-"].update(values=tabela_de_doentes(TABELA_VIEW))

refresh_table(BDDoentes)

while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED: break

    if event == "-OPEN_BAR_EST-" and LAST_IMG_BAR_ESTADOS: abrir_grafico_em_janela_bytes("Atendidos vs Falecidos", LAST_IMG_BAR_ESTADOS)
    if event == "-OPEN_PIE_ESP-" and LAST_IMG_PIE_ESP: abrir_grafico_em_janela_bytes("Pulseiras por Especialidade", LAST_IMG_PIE_ESP)

    if event == "Carregar BD":
        caminho = sg.popup_get_file("Seleciona BD", file_types=tiposfile, no_window=True)
        if caminho:
            try:
                BDDoentes = carregarBDDoentes(caminho)
                refresh_table(BDDoentes)
                sg.popup("BD carregada ✅")
            except Exception as e: sg.popup(f"Erro: {e}")

    if event == "Guardar BD":
        caminho = sg.popup_get_file("Guardar BD", save_as=True, file_types=tiposfile, no_window=True)
        if caminho:
            try: guardarBDDoentes(caminho, BDDoentes); sg.popup("BD guardada ✅")
            except Exception as e: sg.popup(f"Erro: {e}")

    if event == "Inserir Doente":
        dados = janela_inserir_doente()
        if dados: inserirDoente(BDDoentes, *dados); refresh_table(BDDoentes)

    if event == "Marcar Falecido":
        sel = values.get("-TABELA-", [])
        if sel and marcar_falecido(BDDoentes, TABELA_VIEW[sel[0]]["T_doente"]): refresh_table(BDDoentes)
        elif sel: sg.popup("Erro ao marcar.")

    if event == "Ativar/Desativar":
        sel = values.get("-TABELA-", [])
        if sel and alternar_ativo_inativo(BDDoentes, TABELA_VIEW[sel[0]]["T_doente"]): refresh_table(BDDoentes)
        elif sel: sg.popup("Não foi possível alterar.")

    if event == "Consultar": refresh_table(filtrar_doentes(BDDoentes, values.get("-BUSCA-", "")))
    if event == "Mostrar Todos": refresh_table(BDDoentes)
    if event == "-ABRIR_FICHA-":
        sel = values.get("-TABELA-", [])
        if sel:
            d = TABELA_VIEW[sel[0]]
            if janela_ficha_doente(d): refresh_table(filtrar_doentes(BDDoentes, values.get("-BUSCA-", "")))

    # --- SIMULAÇÃO ---
    if event == "-RUN_SIM-":
        if not BDDoentes: sg.popup("Carrega uma BD primeiro!"); continue

        taxa = int(values.get("-SIM_LAMBDA-", 10))
        nm = int(values.get("-SIM_MEDICOS-", 6))
        cap = int(values.get("-SIM_CAP-", 12))
        
        try: tempo_sim = int(values.get("-SIM_TEMPO-", 480))
        except: tempo_sim = 480
        
        try: n_enf = int(values.get("-SIM_ENF-", 1))
        except: n_enf = 1
        
        try: t_med_cons = float(values.get("-SIM_T_CONS-", 15))
        except: t_med_cons = 15.0
        
        tipo_dist = values.get("-SIM_DIST-", "Exponencial")

        pessoas_dict = {d["T_doente"]: d for d in BDDoentes if isinstance(d, dict)}

        try:
            window["-SIM_STATUS-"].update(f"A simular ({tempo_sim} min, {tipo_dist})... aguarde.")
            window.refresh()
            
        
            
            tempos, tri, cons, occ, atendidos, obitos = simula_eventos(
                taxa_chegada_h=taxa,
                tempo_simulacao_min=tempo_sim, 
                num_medicos=nm,
                num_enfermeiros_triagem=n_enf, 
                max_sala_espera_por_esp=cap,
                tempo_medio_consulta=t_med_cons, 
                tipo_distribuicao=tipo_dist,
                pessoas_db=pessoas_dict,
                lista_bd_global=BDDoentes
            )

            fig1 = plt.figure(figsize=(7, 4))
            plt.plot(tempos, [t+c for t,c in zip(tri, cons)], label="Total")
            plt.plot(tempos, tri, label="Triagem")
            plt.plot(tempos, cons, label="Consulta")
            plt.title("Evolução da fila")
            plt.xlabel("Tempo (min)")
            plt.legend()
            LAST_IMG_FILA = _fig_to_bytes(fig1)

            fig2 = plt.figure(figsize=(7, 4))
            plt.plot(tempos, occ)
            plt.title("Ocupação Médicos")
            plt.ylabel("Nº Médicos Ocupados")
            LAST_IMG_OCUP = _fig_to_bytes(fig2)

            taxas = list(range(10, 31, 2))
            medias = []
            for tx in taxas:
                
                db_copy = copy.deepcopy(pessoas_dict)
                
                _, t_res, c_res, _, _, _ = simula_eventos(
                    taxa_chegada_h=tx,
                    num_medicos=nm,
                    num_enfermeiros_triagem=n_enf,
                    max_sala_espera_por_esp=cap,
                    tempo_simulacao_min=tempo_sim,
                    tempo_medio_consulta=t_med_cons, 
                    tipo_distribuicao=tipo_dist,
                    pessoas_db=db_copy,
                    lista_bd_global=None 
                )
                medias.append(np.mean([x+y for x,y in zip(t_res, c_res)]))
            
            fig3 = plt.figure(figsize=(7, 4))
            plt.plot(taxas, medias, marker="o")
            plt.title("Fila Média vs Taxa de Chegada")
            plt.xlabel("Taxa (doentes/h)")
            plt.ylabel("Fila Média")
            LAST_IMG_REL = _fig_to_bytes(fig3)

            
            LAST_IMG_BAR_ESTADOS = grafico_barras_atendidos_falecidos(BDDoentes)
            LAST_IMG_PIE_ESP = grafico_circular_pulseiras_por_especialidade(BDDoentes)
            
            # --- ATUALIZA A ORDEM DA LISTA ---
            BDDoentes = ordenar_por_atendimento(BDDoentes)
            refresh_table(BDDoentes)
            
            window["-SIM_STATUS-"].update(f"Simulação concluída ✅\nTempo: {tempo_sim} min\nDoentes: {atendidos}\nÓbitos: {obitos}")

        except Exception as e:
            sg.popup(f"Erro na simulação: {e}")
            import traceback
            traceback.print_exc()

    if event == "-OPEN_FILA-" and LAST_IMG_FILA: abrir_grafico_em_janela_bytes("Filas", LAST_IMG_FILA)
    if event == "-OPEN_OCUP-" and LAST_IMG_OCUP: abrir_grafico_em_janela_bytes("Ocupação", LAST_IMG_OCUP)
    if event == "-OPEN_REL-" and LAST_IMG_REL: abrir_grafico_em_janela_bytes("Relatório", LAST_IMG_REL)

window.close()