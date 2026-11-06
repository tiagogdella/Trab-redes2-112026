#!/usr/bin/env python3
"""Compara o inventario.toml com a rede em funcionamento e lista cada diferença.

Uso (na pasta do projeto, com a rede no ar):  python3 verificar-inventario.py
Saída: uma linha por diferença; código de saída 0 se não houver nenhuma, 1 se houver.
"""
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

PROJETO = "ponto-comum"   # o "name:" do compose.yaml
INVENTARIO = Path(__file__).with_name("inventario.toml")

# Como verificar cada software do inventário dentro da máquina:
#   rodando: comando que só termina com sucesso se o software estiver em uso
#   versao:  comando que imprime a versão, e a expressão que a extrai
PROGRAMAS = {
    "nginx":    {"rodando": "pgrep -x nginx",
                 "versao": ("nginx -v 2>&1", r"nginx/([\d.]+)")},
    "dnsmasq":  {"rodando": "pgrep -x dnsmasq",
                 "versao": ("dnsmasq --version", r"version ([\d.]+)")},
    "snmpd":    {"rodando": "pgrep -x snmpd",
                 "versao": ("snmpd --version", r"version:\s+(\S+)")},
    "nftables": {"rodando": "nft list table inet filtro",
                 "versao": ("nft --version", r"v([\d.]+)")},
    "tc netem": {"rodando": "tc qdisc show | grep -q netem",
                 "versao": ("tc -V", r"iproute2-([\d.]+)")},
    "exportar-nft": {"rodando": "pgrep -f exportar-nft"},
    "prometheus": {"rodando": "pgrep -x prometheus",
                   "versao": ("prometheus --version 2>&1", r"version ([\d.]+)")},
    "prometheus-blackbox-exporter": {
        "rodando": "pgrep -f prometheus-blackbox-exporter",
        "versao": ("prometheus-blackbox-exporter --version 2>&1", r"version ([\d.]+)")},
}

# Processos que toda máquina tem e que não precisam estar no inventário.
PROCESSOS_BASE = {"tini", "sleep", "ps", "sh"}
# Nome do processo (como o ps mostra) -> software do inventário.
PROCESSO_PARA_SOFTWARE = {
    "nginx": "nginx", "dnsmasq": "dnsmasq", "snmpd": "snmpd", "prometheus": "prometheus",
    "prometheus-blac": "prometheus-blackbox-exporter",  # o ps corta em 15 letras
    "exportar-nft": "exportar-nft",
}

diferencas = []


def diferenca(maquina, texto):
    diferencas.append(f"{maquina}: {texto}")


def docker(*args):
    r = subprocess.run(["docker", *args], capture_output=True, text=True)
    return r.returncode, r.stdout


def na_maquina(nome, comando):
    return docker("exec", nome, "sh", "-c", comando)


def comparar_maquina(m):
    nome = m["nome"]

    # Redes Docker às quais o contêiner está ligado.
    _, saida = docker("inspect", nome)
    redes_reais = {r.removeprefix(PROJETO + "_")
                   for r in json.loads(saida)[0]["NetworkSettings"]["Networks"]}
    redes_inv = {i["rede"] for i in m["interfaces"]}
    for r in sorted(redes_inv - redes_reais):
        diferenca(nome, f"rede {r} está no inventário, mas a máquina não está ligada a ela")
    for r in sorted(redes_reais - redes_inv):
        diferenca(nome, f"ligada à rede {r}, que não está no inventário")

    # Interfaces e endereços IPv4 (sem a lo).
    _, saida = na_maquina(nome, "ip -j -4 addr show")
    reais = {}
    for itf in json.loads(saida):
        if itf["ifname"] != "lo":
            reais[itf["ifname"]] = {f'{a["local"]}/{a["prefixlen"]}' for a in itf["addr_info"]}
    inventario = {i["nome"]: {i["endereco"]} if i["endereco"] else set()
                  for i in m["interfaces"]}
    for itf in sorted(inventario.keys() | reais.keys()):
        esperado, real = inventario.get(itf), reais.get(itf)
        if real is None:
            diferenca(nome, f"interface {itf} está no inventário, mas não existe (ou está sem endereço)")
        elif esperado is None:
            diferenca(nome, f"interface {itf} ({', '.join(sorted(real)) or 'sem endereço'}) não está no inventário")
        elif esperado != real:
            diferenca(nome, f"{itf}: inventário diz {', '.join(sorted(esperado)) or 'sem endereço'}, "
                            f"a máquina tem {', '.join(sorted(real)) or 'sem endereço'}")

    # Software: está rodando? A versão confere?
    for s in m["software"]:
        prog = PROGRAMAS.get(s["nome"])
        if prog is None:
            diferenca(nome, f"não sei verificar o software {s['nome']} (falta em PROGRAMAS)")
            continue
        codigo, _ = na_maquina(nome, prog["rodando"] + " > /dev/null")
        if codigo != 0:
            diferenca(nome, f"{s['nome']} está no inventário, mas não está em execução")
        if "versao" in prog:
            comando, padrao = prog["versao"]
            _, saida = na_maquina(nome, comando)
            achado = re.search(padrao, saida)
            versao = achado.group(1) if achado else "desconhecida"
            if s["versao"] not in versao and versao not in s["versao"]:
                diferenca(nome, f"{s['nome']}: inventário diz versão {s['versao']}, a máquina tem {versao}")

    # Processos em execução que não estão no inventário.
    _, saida = na_maquina(nome, "ps -eo comm=,args=")
    declarados = {s["nome"] for s in m["software"]}
    for linha in saida.splitlines():
        comm, _, args = linha.strip().partition(" ")
        if "exportar-nft" in args:
            comm = "exportar-nft"
        if comm in PROCESSOS_BASE or comm.startswith("runc"):
            continue
        software = PROCESSO_PARA_SOFTWARE.get(comm, comm)
        if software not in declarados:
            diferenca(nome, f"processo {comm} em execução, mas não está no inventário")
            declarados.add(software)   # avisa uma vez só


def main():
    inventario = tomllib.loads(INVENTARIO.read_text(encoding="utf-8"))["maquina"]

    _, saida = docker("ps", "-a", "--filter", f"label=com.docker.compose.project={PROJETO}",
                      "--format", "{{.Names}} {{.State}}")
    estado = dict(linha.split() for linha in saida.splitlines())

    for m in inventario:
        if m["nome"] not in estado:
            diferenca(m["nome"], "está no inventário, mas o contêiner não existe")
        elif estado[m["nome"]] != "running":
            diferenca(m["nome"], f"está no inventário, mas o contêiner está {estado[m['nome']]}")
        else:
            comparar_maquina(m)
    for nome in sorted(estado.keys() - {m["nome"] for m in inventario}):
        diferenca(nome, "contêiner em execução que não está no inventário")

    print(f"Inventário: {len(inventario)} máquinas; rede: {len(estado)} contêineres.")
    if diferencas:
        print(f"{len(diferencas)} diferença(s):")
        for d in diferencas:
            print("  -", d)
        return 1
    print("Nenhuma diferença: o inventário confere com a rede.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
