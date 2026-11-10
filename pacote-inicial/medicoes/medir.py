#!/usr/bin/env python3
"""Medições do trabalho (seção 4 do enunciado). Cada medição grava os dados brutos em
medicoes/dados/, num arquivo com data e hora no nome, e imprime um resumo.

Uso (na pasta pacote-inicial, com a rede no ar):
  python3 medicoes/medir.py condicoes --nota "programas abertos: VS Code, terminal"
  python3 medicoes/medir.py operacao [--minutos 10] [--sem-esperar]
  python3 medicoes/medir.py falha-servico [--repeticoes 5]
  python3 medicoes/medir.py falha-enlace  [--repeticoes 5]
  python3 medicoes/medir.py mudanca       [--repeticoes 5]
  python3 medicoes/medir.py filtragem
"""
import argparse
import csv
import json
import os
import random
import re
import statistics
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

PROMETHEUS = "http://localhost:9090"
PASTA = Path(__file__).resolve().parent
PROJETO = PASTA.parent
DADOS = PASTA / "dados"
ROTEADORES = ["rt-borda", "rt-andar1", "rt-andar2"]


# ------------------------------------------------------------------ utilidades

def arquivo(nome, extensao):
    DADOS.mkdir(exist_ok=True)
    return DADOS / f"{nome}-{datetime.now():%Y%m%d-%H%M%S}.{extensao}"


def docker(*args):
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=True).stdout


def prometheus(caminho, **parametros):
    url = f"{PROMETHEUS}{caminho}?{urllib.parse.urlencode(parametros)}"
    with urllib.request.urlopen(url, timeout=5) as resposta:
        return json.load(resposta)["data"]


def alertas(estado=None):
    """Nomes dos alertas no estado pedido ("firing" ou "pending"); sem estado, todos."""
    return {a["labels"]["alertname"] for a in prometheus("/api/v1/alerts")["alerts"]
            if estado is None or a["state"] == estado}


def esperar(condicao, limite, intervalo=0.2):
    inicio = time.time()
    while time.time() - inicio < limite:
        if condicao():
            return True
        time.sleep(intervalo)
    return False


def hora(t):
    return datetime.fromtimestamp(t).strftime("%H:%M:%S.%f")[:-3]


# ------------------------------------------------------------------ condições

def condicoes(args):
    def rodar(comando):
        r = subprocess.run(comando, shell=True, capture_output=True, text=True,
                           env={**os.environ, "LC_ALL": "C"})  # saída em inglês, igual em todo PC
        return (r.stdout or r.stderr).strip()

    texto = f"""Condições das medições
Data: {datetime.now():%Y-%m-%d %H:%M:%S}
Sistema: {rodar("grep PRETTY_NAME /etc/os-release | cut -d= -f2 | tr -d '\"'")}
Kernel: {rodar("uname -r")}
Processador: {rodar("lscpu | grep 'Model name' | cut -d: -f2 | xargs")}
Núcleos: {rodar("nproc")}
Memória: {rodar("free -h | awk '/Mem:/ {print $2}'")}
Docker: {rodar("docker version --format '{{.Server.Version}}'")}
Docker Compose: {rodar("docker compose version --short")}
Carga do computador (1, 5, 15 min): {rodar("cut -d' ' -f1-3 /proc/loadavg")}
Outros programas abertos: {args.nota or "(não informado: use --nota)"}

Contêineres:
{rodar("docker compose ps --format '{{.Name}} {{.Status}}'")}
"""
    destino = arquivo("condicoes", "txt")
    destino.write_text(texto, encoding="utf-8")
    print(texto)
    print(f"Gravado em {destino}")


# ------------------------------------------------------------------ operação normal

def operacao(args):
    if not args.sem_esperar:
        print(f"Aguardando {args.minutos} min de operação normal (não mexa na rede)...")
        time.sleep(args.minutos * 60)
    fim = time.time()
    destino = arquivo("operacao", "csv")
    amostras = {}
    with open(destino, "w", newline="") as f:
        saida = csv.writer(f)
        saida.writerow(["criterio", "alvo", "metrica", "instante", "valor"])
        for metrica in ["probe_duration_seconds", "probe_success", "probe_http_status_code"]:
            consulta = f'{metrica}{{job=~"C1|C2|C3"}}[{args.minutos}m]'
            for serie in prometheus("/api/v1/query", query=consulta, time=fim)["result"]:
                job, alvo = serie["metric"]["job"], serie["metric"]["instance"]
                for instante, valor in serie["values"]:
                    saida.writerow([job, alvo, metrica, instante, valor])
                    amostras.setdefault((job, metrica), []).append(float(valor))

    print(f"Operação normal, últimos {args.minutos} min (fim {hora(fim)}):")
    print(f"{'critério':8} {'amostras':>8} {'mediana':>10} {'máximo':>10} {'sucesso':>8}")
    for job in ["C1", "C2", "C3"]:
        tempos = [v * 1000 for v in amostras.get((job, "probe_duration_seconds"), [])]
        sucesso = amostras.get((job, "probe_success"), [])
        if not tempos:
            print(f"{job:8} sem amostras")
            continue
        print(f"{job:8} {len(tempos):8} {statistics.median(tempos):8.1f}ms {max(tempos):8.1f}ms "
              f"{100 * sum(sucesso) / len(sucesso):7.1f}%")
    print(f"Dados brutos em {destino}")


# ------------------------------------------------------------------ falhas

def medir_falha(nome, quebrar, consertar, esperados, repeticoes):
    destino = arquivo(nome, "csv")
    with open(destino, "w", newline="") as f:
        saida = csv.writer(f)
        saida.writerow(["repeticao", "alerta", "t_falha", "t_disparo", "t_correcao", "t_fim",
                        "falha_ate_disparo_s", "correcao_ate_fim_s"])
        for r in range(1, repeticoes + 1):
            if not esperar(lambda: not alertas(), 180):
                sys.exit(f"Há alertas ativos que não terminam: {alertas()}. Corrija antes de medir.")
            # Espera um tempo sorteado, para a falha cair em pontos diferentes do ciclo de
            # coleta (5 s) e as repetições mostrarem a variação real.
            time.sleep(random.uniform(1, 6))

            t_falha = time.time()
            quebrar()
            disparo = {}
            while len(disparo) < len(esperados) and time.time() - t_falha < 120:
                disparados = alertas("firing")
                for a in esperados:
                    if a in disparados and a not in disparo:
                        disparo[a] = time.time()
                time.sleep(0.2)

            time.sleep(random.uniform(1, 6))   # o conserto também cai num ponto sorteado do ciclo
            t_correcao = time.time()
            consertar()
            fim = {}

            while len(fim) < len(esperados) and time.time() - t_correcao < 120:
                disparados = alertas("firing")
                for a in esperados:
                    if a not in disparados and a not in fim:
                        fim[a] = time.time()
                time.sleep(0.2)

            for a in esperados:
                d, e = disparo.get(a), fim.get(a)
                saida.writerow([r, a, f"{t_falha:.3f}", f"{d:.3f}" if d else "",
                                f"{t_correcao:.3f}", f"{e:.3f}" if e else "",
                                f"{d - t_falha:.3f}" if d else "", f"{e - t_correcao:.3f}" if e else ""])
                print(f"rep {r} {a:20} falha→alerta "
                      f"{f'{d - t_falha:5.1f} s' if d else 'NÃO DISPAROU'}   correção→fim "
                      f"{f'{e - t_correcao:5.1f} s' if e else 'NÃO TERMINOU'}")
            f.flush()
    print(f"Dados brutos em {destino}")


def falha_servico(args):
    medir_falha(
        "falha-servico",
        quebrar=lambda: docker("exec", "srv-portal", "pkill", "-x", "nginx"),
        consertar=lambda: docker("exec", "srv-portal", "nginx", "-c", "/run/nginx.conf"),
        esperados=["C1-portal-internet", "C2-portal-gama"],
        repeticoes=args.repeticoes)


def enlace_andar2(perda):
    # As duas pontas do enlace-andar2, mantendo as condições normais (5 ms, 20 Mbit/s).
    extra = ["loss", "100%"] if perda else []
    for maquina, interface in [("rt-borda", "eth3"), ("rt-andar2", "eth0")]:
        docker("exec", maquina, "tc", "qdisc", "replace", "dev", interface, "root", "netem",
               "delay", "5ms", "rate", "20mbit", *extra)


def falha_enlace(args):
    medir_falha(
        "falha-enlace",
        quebrar=lambda: enlace_andar2(perda=True),
        consertar=lambda: enlace_andar2(perda=False),
        esperados=["C2-portal-gama", "C3-arquivos-gama"],
        repeticoes=args.repeticoes)


# ------------------------------------------------------------------ mudança

TESTE = ('fim=$(( $(date +%s) + {duracao} )); while [ $(date +%s) -lt $fim ]; do '
         'for u in {urls}; do '
         'r=$(curl -s -o /dev/null -m 1 -w "%{{http_code}} %{{time_total}}" $u); '
         'echo "$(date +%s.%N) $u $r"; done; sleep 0.1; done')
SONDAS = {"sonda-internet": ["http://srv-portal/"],
          "sonda-gama": ["http://srv-portal/", "http://srv-arquivos:8080/"]}


def testar_durante(acao, duracao=12, antes=3):
    """Testa os serviços das sondas a cada 0,1 s enquanto a ação roda. Devolve as
    amostras (sonda, instante, url, código, tempo) e o início e o fim da ação."""
    amostras = []

    def sonda(nome, urls):
        saida = docker("exec", nome, "sh", "-c", TESTE.format(duracao=duracao, urls=" ".join(urls)))
        for linha in saida.splitlines():
            instante, url, codigo, tempo = linha.split()
            amostras.append((nome, float(instante), url, codigo, float(tempo)))

    linhas = [threading.Thread(target=sonda, args=item) for item in SONDAS.items()]
    for t in linhas:
        t.start()
    time.sleep(antes)
    inicio = time.time()
    acao()
    fim_acao = time.time()
    for t in linhas:
        t.join()
    return sorted(amostras, key=lambda a: a[1]), inicio, fim_acao


def sem_resposta(amostras, sonda, url):
    """Soma dos intervalos sem resposta: da 1ª falha de uma sequência até o próximo sucesso."""
    total, inicio_falha = 0.0, None
    for s, instante, u, codigo, _ in amostras:
        if s != sonda or u != url:
            continue
        if codigo != "200" and inicio_falha is None:
            inicio_falha = instante
        elif codigo == "200" and inicio_falha is not None:
            total += instante - inicio_falha
            inicio_falha = None
    return total


def mudanca(args):
    bruto, resumo = arquivo("mudanca-amostras", "csv"), arquivo("mudanca-resumo", "csv")
    with open(bruto, "w", newline="") as fb, open(resumo, "w", newline="") as fr:
        b, s = csv.writer(fb), csv.writer(fr)
        b.writerow(["repeticao", "fase", "sonda", "instante", "url", "codigo_http", "tempo_s"])
        s.writerow(["repeticao", "fase", "inicio", "fim", "duracao_s", "sonda", "url",
                    "amostras", "falhas", "sem_resposta_s"])
        for r in range(1, args.repeticoes + 1):
            for fase in ["aplicar", "reverter"]:
                amostras, inicio, fim = testar_durante(
                    lambda: subprocess.run(["./mudanca.sh", fase], cwd=PROJETO, check=True,
                                           capture_output=True))
                for a in amostras:
                    b.writerow([r, fase, *a])
                for sonda, urls in SONDAS.items():
                    for url in urls:
                        do_par = [a for a in amostras if a[0] == sonda and a[2] == url]
                        falhas = sum(1 for a in do_par if a[3] != "200")
                        parado = sem_resposta(amostras, sonda, url)
                        s.writerow([r, fase, f"{inicio:.3f}", f"{fim:.3f}", f"{fim - inicio:.3f}",
                                    sonda, url, len(do_par), falhas, f"{parado:.3f}"])
                        print(f"rep {r} {fase:8} {sonda:14} {url:26} amostras {len(do_par):3} "
                              f"falhas {falhas:2} sem resposta {parado:.2f} s")
                fb.flush(); fr.flush()
    print(f"Dados brutos em {bruto}\nResumo em {resumo}")


# ------------------------------------------------------------------ filtragem

def contadores():
    valores = {}
    for rt in ROTEADORES:
        regras = docker("exec", rt, "nft", "list", "table", "inet", "filtro")
        for pacotes, regra in re.findall(r'counter packets (\d+) bytes \d+ drop comment "([^"]+)"', regras):
            valores[(rt, regra)] = int(pacotes)
    return valores


def filtragem(args):
    destino = arquivo("filtragem", "csv")
    with open(destino, "w", newline="") as f:
        saida = csv.writer(f)
        saida.writerow(["servidor", "portas_abertas", "roteador", "regra", "antes", "depois", "diferenca"])
        for servidor in ["srv-portal", "srv-arquivos", "srv-dns"]:
            print(f"Varrendo {servidor} (pode levar alguns minutos)...")
            antes = contadores()
            varredura = docker("exec", "externo", "nmap", "-Pn", "-p", "1-1024", servidor)
            depois = contadores()
            arquivo(f"filtragem-nmap-{servidor}", "txt").write_text(varredura, encoding="utf-8")
            abertas = " ".join(re.findall(r"^(\d+/tcp)\s+open", varredura, re.M)) or "nenhuma"
            print(f"  portas abertas: {abertas}")
            for chave in sorted(depois):
                dif = depois[chave] - antes.get(chave, 0)
                saida.writerow([servidor, abertas, *chave, antes.get(chave, 0), depois[chave], dif])
                if dif:
                    print(f"  {chave[0]} {chave[1]}: {antes.get(chave, 0)} -> {depois[chave]} (+{dif})")
    print(f"Dados em {destino} (e a saída de cada nmap em filtragem-nmap-*.txt)")


# ------------------------------------------------------------------ linha de comando

def main():
    p = argparse.ArgumentParser(description="Medições do trabalho (seção 4 do enunciado).")
    sub = p.add_subparsers(dest="medicao", required=True)
    c = sub.add_parser("condicoes"); c.add_argument("--nota", default="")
    o = sub.add_parser("operacao"); o.add_argument("--minutos", type=int, default=10)
    o.add_argument("--sem-esperar", action="store_true",
                   help="usa os últimos N minutos, sem esperar (a rede já está no ar há N min)")
    for nome in ["falha-servico", "falha-enlace", "mudanca"]:
        sub.add_parser(nome).add_argument("--repeticoes", type=int, default=5)
    sub.add_parser("filtragem")
    args = p.parse_args()
    {"condicoes": condicoes, "operacao": operacao, "falha-servico": falha_servico,
     "falha-enlace": falha_enlace, "mudanca": mudanca, "filtragem": filtragem}[args.medicao](args)


if __name__ == "__main__":
    main()
