#!/usr/bin/env python3
"""Gera os gráficos e as tabelas do artigo a partir dos dados brutos em medicoes/dados/.

Uso:  python3 medicoes/graficos.py
Saída: medicoes/graficos/*.pdf (para o LaTeX), *.png (para olhar) e resumo.txt.

Os dados brutos nunca são alterados: este programa só lê. Para cada medição usa o
arquivo mais recente que tenha pelo menos uma linha de dados.
"""
import csv
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

AQUI = Path(__file__).resolve().parent
DADOS = AQUI / "dados"
SAIDA = AQUI / "graficos"

# Uma cor e um marcador por critério (o marcador garante a leitura em preto e branco).
ESTILO = {
    "C1": {"color": "#2a78d6", "marker": "o"},
    "C2": {"color": "#eb6834", "marker": "s"},
    "C3": {"color": "#1baf7a", "marker": "^"},
}
TINTA, TINTA_FRACA, GRADE = "#222222", "#666666", "#dddddd"

plt.rcParams.update({
    "font.size": 9, "axes.edgecolor": TINTA_FRACA, "axes.labelcolor": TINTA,
    "xtick.color": TINTA_FRACA, "ytick.color": TINTA_FRACA, "axes.grid": True,
    "grid.color": GRADE, "grid.linewidth": 0.6, "axes.spines.top": False,
    "axes.spines.right": False, "legend.frameon": False, "savefig.bbox": "tight",
})


def ler(prefixo):
    """Linhas do CSV mais recente 'prefixo-AAAAmmdd-HHMMSS.csv' que não esteja vazio."""
    for arq in sorted(DADOS.glob(f"{prefixo}-2*.csv"), reverse=True):
        with open(arq, newline="") as f:
            linhas = list(csv.DictReader(f))
        if linhas:
            return arq, linhas
    raise SystemExit(f"Nenhum arquivo com dados para '{prefixo}' em {DADOS}")


def resumo(valores):
    v = list(valores)
    dp = statistics.stdev(v) if len(v) > 1 else 0.0
    return f"{len(v):3}  {statistics.mean(v):7.2f}  {dp:6.2f}  {min(v):7.2f}  {max(v):7.2f}"


def salvar(fig, nome):
    for ext in ("pdf", "png"):
        fig.savefig(SAIDA / f"{nome}.{ext}", dpi=200)
    plt.close(fig)


# ------------------------------------------------------------------ operação normal

def operacao(texto):
    arq, linhas = ler("operacao")
    serie = defaultdict(list)       # critério -> [(instante, ms)]
    sucesso = defaultdict(list)
    for l in linhas:
        if l["metrica"] == "probe_duration_seconds":
            serie[l["criterio"]].append((float(l["instante"]), 1000 * float(l["valor"])))
        elif l["metrica"] == "probe_success":
            sucesso[l["criterio"]].append(float(l["valor"]))
    inicio = min(t for pts in serie.values() for t, _ in pts)

    fig, ax = plt.subplots(figsize=(6, 2.8))
    for c in sorted(serie):
        pts = sorted(serie[c])
        ax.plot([(t - inicio) / 60 for t, _ in pts], [ms for _, ms in pts], label=c,
                linewidth=1.2, markersize=3, markevery=6, **ESTILO[c])
    ax.axhline(50, color=TINTA_FRACA, linestyle="--", linewidth=1)
    ax.text(0, 51, "limite do C2 (50 ms)", color=TINTA_FRACA, fontsize=8, va="bottom")
    ax.set_xlabel("tempo (min)")
    ax.set_ylabel("duração da verificação (ms)")
    ax.set_ylim(0, 60)
    ax.legend(loc="upper right", ncol=3)
    salvar(fig, "operacao")

    texto.append(f"OPERAÇÃO NORMAL  ({arq.name})")
    texto.append("critério   n    média      dp   mínimo   máximo   (ms)   sucesso")
    for c in sorted(serie):
        s = sucesso[c]
        texto.append(f"{c:8} {resumo(ms for _, ms in serie[c])}   {100 * sum(s) / len(s):6.1f}%")


# ------------------------------------------------------------------ falhas

def falhas(texto):
    grupos = []                      # (rótulo, critério, [falha→alerta], [correção→fim])
    for prefixo, nome in (("falha-servico", "serviço"), ("falha-enlace", "enlace")):
        arq, linhas = ler(prefixo)
        por_alerta = defaultdict(lambda: ([], []))
        for l in linhas:
            a, b = por_alerta[l["alerta"]]
            if l["falha_ate_disparo_s"]:
                a.append(float(l["falha_ate_disparo_s"]))
            if l["correcao_ate_fim_s"]:
                b.append(float(l["correcao_ate_fim_s"]))
        for alerta in sorted(por_alerta):
            grupos.append((f"falha do {nome}\n{alerta}", alerta[:2], *por_alerta[alerta], arq.name))

    fig, eixos = plt.subplots(1, 2, figsize=(6.5, 2.8), sharey=True)
    paineis = (("falha → alerta disparado (s)", 2, 20), ("correção → fim do alerta (s)", 3, 10))
    for ax, (titulo, col, teto) in zip(eixos, paineis):
        ax.axvspan(0, teto, color=GRADE, alpha=0.5, linewidth=0)
        ax.text(teto, len(grupos) - 0.45, f" máx. teórico {teto} s", fontsize=7,
                color=TINTA_FRACA, ha="right", va="bottom")
        for y, g in enumerate(grupos):
            valores = g[col]
            ax.scatter(valores, [y] * len(valores), s=22, alpha=0.8,
                       edgecolors="white", linewidths=0.6, **ESTILO[g[1]], zorder=3)
            m = statistics.mean(valores)
            ax.plot([m, m], [y - 0.3, y + 0.3], color=TINTA, linewidth=1.5, zorder=4)
        ax.set_xlabel(titulo)
        ax.set_xlim(0, 25)
        ax.grid(axis="y", visible=False)
    eixos[0].set_yticks(range(len(grupos)), [g[0] for g in grupos])
    eixos[0].set_ylim(-0.6, len(grupos) - 0.1)
    eixos[0].invert_yaxis()
    salvar(fig, "falhas")

    texto.append("")
    texto.append("FALHAS  (traço preto no gráfico = média)")
    texto.append("grupo                                    n    média      dp   mínimo   máximo   (s)")
    for rotulo, _, ida, volta, arq in grupos:
        r = rotulo.replace("\n", " ")
        texto.append(f"{r:38} falha→alerta    {resumo(ida)}")
        texto.append(f"{'':38} correção→fim    {resumo(volta)}   ({arq})")


# ------------------------------------------------------------------ mudança

def mudanca(texto):
    arq, linhas = ler("mudanca-resumo")
    texto.append("")
    texto.append(f"MUDANÇA DA GAMA  ({arq.name})")
    texto.append("fase       sonda           url                         reps  amostras  falhas  sem resposta máx (s)")
    grupos = defaultdict(list)
    for l in linhas:
        grupos[(l["fase"], l["sonda"], l["url"])].append(l)
    for (fase, sonda, url), ls in grupos.items():
        texto.append(f"{fase:10} {sonda:15} {url:27} {len(ls):4}  "
                     f"{sum(int(l['amostras']) for l in ls):8}  {sum(int(l['falhas']) for l in ls):6}  "
                     f"{max(float(l['sem_resposta_s']) for l in ls):8.2f}")
    duracoes = [float(l["duracao_s"]) for l in {(l["repeticao"], l["fase"]): l for l in linhas}.values()]
    texto.append(f"duração de cada fase (s): n, média, dp, mín, máx = {resumo(duracoes)}")


# ------------------------------------------------------------------ filtragem

def filtragem(texto):
    arq, linhas = ler("filtragem")
    texto.append("")
    texto.append(f"FILTRAGEM  ({arq.name}; só regras cujo contador mudou)")
    vistos = set()
    for l in linhas:
        if l["servidor"] not in vistos:
            vistos.add(l["servidor"])
            texto.append(f"{l['servidor']}: portas abertas = {l['portas_abertas'] or 'nenhuma'}")
        if l["diferenca"] != "0":
            texto.append(f"    {l['roteador']} {l['regra']}: {l['antes']} → {l['depois']} (+{l['diferenca']})")


def main():
    SAIDA.mkdir(exist_ok=True)
    texto = []
    operacao(texto)
    falhas(texto)
    mudanca(texto)
    filtragem(texto)
    (SAIDA / "resumo.txt").write_text("\n".join(texto) + "\n")
    print("\n".join(texto))
    print(f"\nGráficos e resumo em {SAIDA}")


if __name__ == "__main__":
    main()
