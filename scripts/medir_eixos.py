#!/usr/bin/env python3
"""Mede a viabilidade dos eixos de pesquisa a partir dos dados já coletados.

Lê apenas arquivos locais (não acessa a rede). Reporta os números que decidem
qual eixo sustenta as conclusões centrais da dissertação. Ver docs/plano-grafos.md.
"""
import json
import glob
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "dados" / "18-legislatura"

EDU_TERMS = [
    "educa", "escola", "escolar", "ensino", "creche", "professor", "aluno",
    "merenda", "alfabetiza", "universidad", "pedagog", "estudante", "magistério",
]


def load(path):
    p = OUT / path
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def councilmember_names():
    """Names of the 49 councilmembers, used to match authorship (the list has no id)."""
    ver = load("vereadores/_index.json") or {"items": []}
    names = set()
    for v in ver["items"]:
        names.add(v.get("title"))
        names.add(v.get("description"))
    names.discard(None)
    return names


def authors_of(item, names=None):
    """Return the set of author NAMES of a matéria (the list carries names, not ids).

    If `names` is given, keep only authors that are councilmembers (drops
    institutional authors like 'Comissão Executiva', 'Prefeito')."""
    out = set()
    for a in (item.get("authorship") or item.get("autoria") or []):
        title = a.get("title")
        if title and (names is None or title in names):
            out.add(title)
    return out


def eixo1_coautoria(materias):
    items = materias.get("items", [])
    names = councilmember_names()
    com_autor = [it for it in items if authors_of(it)]
    com_2mais = [it for it in items if len(authors_of(it, names)) >= 2]
    pares = Counter()
    graus = defaultdict(set)
    for it in com_2mais:
        aut = sorted(authors_of(it, names))
        for a, b in combinations(aut, 2):
            pares[(a, b)] += 1
            graus[a].add(b)
            graus[b].add(a)
    n_nos = len(graus)
    n_arestas = len(pares)
    dens = (2 * n_arestas) / (n_nos * (n_nos - 1)) if n_nos > 1 else 0
    grau_medio = (2 * n_arestas / n_nos) if n_nos else 0
    print("== EIXO 1 — Co-autoria ==")
    print(f"  matérias total: {len(items)}")
    print(f"  com autoria identificada: {len(com_autor)}")
    print(f"  com >=2 autores (geram co-autoria): {len(com_2mais)}")
    print(f"  grafo co-autoria: {n_nos} nós, {n_arestas} arestas, densidade {dens:.3f}, grau médio {grau_medio:.1f}")
    print(f"  pares mais frequentes: {pares.most_common(5)}")


def eixo3_sucesso(materias, normas):
    print("== EIXO 3 — Sucesso legislativo (matéria -> norma) ==")
    det = sorted(glob.glob(str(OUT / "normas" / "detalhe" / "*.json")))
    if not det:
        print(f"  matérias: {len(materias.get('items', []))} | normas: {len(normas.get('items', [])) if normas else 'N/A'}")
        print("  NOTA: coletar normas/detalhe/{id}.json (/@@normas/{id}) para o vínculo matéria->norma.")
        return
    names = councilmember_names()
    tipo = Counter()
    origem = Counter()
    por_vereador = Counter()
    for f in det:
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        tipo[d.get("title", "").split(" nº")[0]] += 1
        for mat in (d.get("materia") or []):
            for a in (mat.get("autoria") or []):
                nome = a.get("title")
                origem[nome] += 1
                if nome in names:
                    por_vereador[nome] += 1
    print(f"  normas detalhadas: {len(det)} | por tipo: {dict(tipo)}")
    print(f"  leis de matéria de VEREADOR: {sum(por_vereador.values())} | de vereadores distintos: {len(por_vereador)}")
    print(f"  top sucesso legislativo: {por_vereador.most_common(6)}")
    print(f"  top origens no geral (inclui Executivo/Comissão): {origem.most_common(4)}")


def educacao(materias, normas):
    items = materias.get("items", [])
    def is_edu(texto):
        t = (texto or "").lower()
        return any(term in t for term in EDU_TERMS)
    edu = [it for it in items if is_edu(it.get("description")) or is_edu(it.get("title"))]
    print("== Recorte EDUCAÇÃO ==")
    print(f"  matérias de educação (match na ementa/título): {len(edu)} de {len(items)}")
    por_tipo = Counter(it.get("title", "").split(" nº")[0] for it in edu)
    print(f"  por tipo: {dict(por_tipo)}")
    if normas:
        edu_norm = [n for n in normas.get("items", []) if is_edu(n.get("description")) or is_edu(n.get("title"))]
        print(f"  normas de educação: {len(edu_norm)}")


def presenca():
    fs = sorted(glob.glob(str(OUT / "sessoes" / "*_presenca.json")))
    presenca_ord = Counter()
    co_ausencia = Counter()
    sess_com = 0
    for f in fs:
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        def ids(momento, campo):
            out = set()
            for bloco in (d.get(momento) or []):
                for v in (bloco.get(campo) or []):
                    if isinstance(v, dict) and v.get("id"):
                        out.add(str(v["id"]))
            return out
        # chamadaRegimental == ordemDia em todas as 303 sessões (verificado):
        # presença é um rol único por sessão. Usamos a ordem do dia.
        pres_od = ids("ordemDia", "presentes") or ids("chamadaRegimental", "presentes")
        aus_od = ids("ordemDia", "ausentes") or ids("chamadaRegimental", "ausentes")
        if not (pres_od or aus_od):
            continue
        sess_com += 1
        for i in pres_od:
            presenca_ord[i] += 1
        # co-ausência: vereadores que faltaram na mesma sessão
        for a, b in combinations(sorted(aus_od), 2):
            co_ausencia[(a, b)] += 1
    print("== PRESENÇA ==")
    print(f"  sessões com presença nominal: {sess_com}")
    print(f"  top presença: {presenca_ord.most_common(3)}")
    print(f"  pares com mais co-ausência: {co_ausencia.most_common(5)}")


def main():
    materias = load("materias/_index.json")
    normas = load("normas/_index.json")
    if not materias:
        print("materias/_index.json ainda não existe — coleta de matérias não terminou.")
    else:
        eixo1_coautoria(materias)
        print()
        eixo3_sucesso(materias, normas)
        print()
        educacao(materias, normas)
        print()
    presenca()


if __name__ == "__main__":
    main()
