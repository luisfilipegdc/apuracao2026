"""
ETL dos Dados Abertos do TSE -> JSON estáticos para o app.

Fontes (Portal de Dados Abertos do TSE, https://dadosabertos.tse.jus.br):
  - votacao_candidato_munzona_<ANO>.zip  (votos por candidato, município e zona)
  - detalhe_votacao_munzona_<ANO>.zip    (aptos, comparecimento, brancos, nulos)

Saída (pasta data/):
  data/index.json                               anos, turnos, cargos e UFs disponíveis
  data/<ano>/t<turno>/c<cargo>/<uf>.json        resultado da UF (e por município quando aplicável)
  data/<ano>/t1/c1/br.json                      presidente: total Brasil com quebra por UF

Granularidade escolhida:
  - por município: Presidente(1), Governador(3), Senador(5), Prefeito(11), Vereador(13)
  - só por UF:     Dep. Federal(6), Dep. Estadual(7), Dep. Distrital(8)

Uso: python scripts/etl_tse.py 2022 2024 ...   (sem argumentos: todos os anos de 2000 a 2024)
"""
import csv, io, json, os, sys, time, zipfile, urllib.request
from collections import defaultdict

BASE = "https://cdn.tse.jus.br/estatistica/sead/odsele"
OUT = os.path.join(os.path.dirname(__file__), "..", "data")
TMP = os.environ.get("ETL_TMP", "/tmp/tse_etl")
ANOS = list(range(2000, 2025, 2))
CARGOS = {1: "Presidente", 3: "Governador", 5: "Senador", 6: "Deputado Federal",
          7: "Deputado Estadual", 8: "Deputado Distrital", 11: "Prefeito", 13: "Vereador"}
POR_MUNICIPIO = {1, 3, 5, 11, 13}

csv.field_size_limit(10**9)


def baixar(nome, ano):
    os.makedirs(TMP, exist_ok=True)
    url = f"{BASE}/{nome}/{nome}_{ano}.zip"
    dest = os.path.join(TMP, f"{nome}_{ano}.zip")
    if os.path.exists(dest) and zipfile.is_zipfile(dest):
        return dest, url
    for tent in range(4):
        try:
            with urllib.request.urlopen(url, timeout=600) as r, open(dest, "wb") as f:
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    f.write(b)
            if zipfile.is_zipfile(dest):
                return dest, url
            raise RuntimeError("arquivo baixado não é zip (bloqueio ou erro do servidor)")
        except Exception as e:
            print(f"  falha ao baixar {url}: {e}; tentativa {tent + 1}/4", flush=True)
            time.sleep(30 * (tent + 1))
    raise RuntimeError(f"não consegui baixar {url}")


def linhas(zpath):
    """Lê os CSVs do zip. Usa o arquivo _BRASIL quando existe; senão, todos os de UF."""
    z = zipfile.ZipFile(zpath)
    nomes = [n for n in z.namelist() if n.lower().endswith((".csv", ".txt"))]
    brasil = [n for n in nomes if "_BRASIL" in n.upper()]
    usar = brasil or [n for n in nomes if not n.upper().endswith("_BR.CSV")] or nomes
    for nome in usar:
        with z.open(nome) as fh:
            txt = io.TextIOWrapper(fh, encoding="latin-1", newline="")
            rd = csv.reader(txt, delimiter=";")
            cab = next(rd)
            if "ANO_ELEICAO" not in cab:
                raise RuntimeError(f"{nome}: arquivo sem cabeçalho; leiaute antigo não suportado")
            idx = {c: i for i, c in enumerate(cab)}
            for row in rd:
                yield idx, row


def col(idx, *opcoes):
    for o in opcoes:
        if o in idx:
            return idx[o]
    return None


def num(v):
    try:
        return int(v)
    except (ValueError, TypeError):
        try:
            return int(float(str(v).replace(",", ".")))
        except Exception:
            return 0


def processar_ano(ano):
    print(f"== {ano}", flush=True)
    zc, url_c = baixar("votacao_candidato_munzona", ano)
    try:
        zd, url_d = baixar("detalhe_votacao_munzona", ano)
    except RuntimeError as e:
        print(f"  sem detalhe de votação: {e}", flush=True)
        zd, url_d = None, None

    # votos[(turno, cargo, uf)][sq] = {...}; mun[(turno,cargo,uf)][cd_mun][sq] = votos
    cand = defaultdict(dict)
    mun = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    nomes_mun = {}
    uf_mun = {}
    pmun = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))  # votos por partido em cada município, todos os cargos
    tipo_eleicao = {}
    for idx, r in linhas(zc):
        cargo = num(r[idx["CD_CARGO"]])
        if cargo not in CARGOS:
            continue
        ic_tipo = col(idx, "CD_TIPO_ELEICAO")
        if ic_tipo is not None and r[ic_tipo] not in ("2",):  # 2 = eleição ordinária
            continue
        turno = num(r[idx["NR_TURNO"]])
        uf = r[idx["SG_UF"]].lower()
        cdm = r[idx["CD_MUNICIPIO"]]
        nomes_mun[cdm] = r[idx["NM_MUNICIPIO"]]
        sq = r[idx["SQ_CANDIDATO"]]
        iv = col(idx, "QT_VOTOS_NOMINAIS_VALIDOS", "QT_VOTOS_NOMINAIS")
        v = num(r[iv])
        k = (turno, cargo, uf)
        c = cand[k].get(sq)
        if c is None:
            c = cand[k][sq] = {
                "n": r[idx["NR_CANDIDATO"]],
                "nm": r[col(idx, "NM_URNA_CANDIDATO", "NM_CANDIDATO")],
                "p": r[idx["SG_PARTIDO"]],
                "sit": r[col(idx, "DS_SIT_TOT_TURNO")] if col(idx, "DS_SIT_TOT_TURNO") is not None else "",
                "v": 0,
            }
            if cargo in (11, 13):
                c["m"] = cdm  # prefeito/vereador: candidatura é municipal
        c["v"] += v
        if cargo in POR_MUNICIPIO:
            mun[k][cdm][sq] += v
        pmun[(turno, cargo, uf)][cdm][r[idx["SG_PARTIDO"]]] += v
        uf_mun[cdm] = uf
        tipo_eleicao[(turno, cargo)] = True

    # detalhe: comparecimento etc. por (turno, cargo, uf, municipio)
    det = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0, 0]))
    if zd:
        for idx, r in linhas(zd):
            cargo = num(r[idx["CD_CARGO"]])
            if cargo not in CARGOS:
                continue
            ic_tipo = col(idx, "CD_TIPO_ELEICAO")
            if ic_tipo is not None and r[ic_tipo] != "2":
                continue
            k = (num(r[idx["NR_TURNO"]]), cargo, r[idx["SG_UF"]].lower())
            d = det[k][r[idx["CD_MUNICIPIO"]]]
            for i, opcoes in enumerate([("QT_APTOS",), ("QT_COMPARECIMENTO",), ("QT_ABSTENCOES",),
                                        ("QT_VOTOS_BRANCOS",), ("QT_TOTAL_VOTOS_NULOS", "QT_VOTOS_NULOS")]):
                ic = col(idx, *opcoes)
                if ic is not None:
                    d[i] += num(r[ic])

    fonte = {"candidatos": url_c, "detalhe": url_d, "gerado_em": time.strftime("%Y-%m-%d")}
    resumo = defaultdict(lambda: defaultdict(list))
    for (turno, cargo, uf), cs in cand.items():
        lista = sorted(cs.items(), key=lambda kv: -kv[1]["v"])
        sqs = [sq for sq, _ in lista]
        pos = {sq: i for i, sq in enumerate(sqs)}
        tot_det = [0, 0, 0, 0, 0]
        for dm in det[(turno, cargo, uf)].values():
            tot_det = [a + b for a, b in zip(tot_det, dm)]
        doc = {
            "ano": ano, "turno": turno, "cargo": cargo, "nm_cargo": CARGOS[cargo], "uf": uf,
            "fonte": fonte,
            "det_campos": ["aptos", "comparecimento", "abstencoes", "brancos", "nulos"],
            "det": tot_det,
            "cands": [c for _, c in lista],
        }
        if cargo in POR_MUNICIPIO:
            ms = {}
            for cdm, votos in mun[(turno, cargo, uf)].items():
                arr = [[pos[sq], v] for sq, v in votos.items() if v]
                ms[cdm] = {"nm": nomes_mun.get(cdm, cdm), "v": arr, "det": det[(turno, cargo, uf)].get(cdm, [0] * 5)}
            doc["mun"] = ms
        caminho = os.path.join(OUT, str(ano), f"t{turno}", f"c{cargo}")
        os.makedirs(caminho, exist_ok=True)
        with open(os.path.join(caminho, f"{uf}.json"), "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
        resumo[f"t{turno}"][f"c{cargo}"].append(uf)

    # presidente: arquivo Brasil com quebra por UF
    for turno in (1, 2):
        ks = [k for k in cand if k[0] == turno and k[1] == 1]
        if not ks:
            continue
        agg, por_uf, det_br = {}, {}, [0] * 5
        for (_, _, uf) in ks:
            por_uf[uf] = {}
            for sq, c in cand[(turno, 1, uf)].items():
                a = agg.setdefault(c["n"], {"n": c["n"], "nm": c["nm"], "p": c["p"], "sit": c["sit"], "v": 0})
                a["v"] += c["v"]
                por_uf[uf][c["n"]] = c["v"]
            for dm in det[(turno, 1, uf)].values():
                det_br = [x + y for x, y in zip(det_br, dm)]
        lista = sorted(agg.values(), key=lambda c: -c["v"])
        ordem = [c["n"] for c in lista]
        doc = {"ano": ano, "turno": turno, "cargo": 1, "nm_cargo": "Presidente", "uf": "br", "fonte": fonte,
               "det_campos": ["aptos", "comparecimento", "abstencoes", "brancos", "nulos"], "det": det_br,
               "cands": lista,
               "ufs": {uf: {"v": [[i, por_uf[uf].get(n, 0)] for i, n in enumerate(ordem) if por_uf[uf].get(n, 0)],
                            "det": [sum(dm[i] for dm in det[(turno, 1, uf)].values()) for i in range(5)]}
                       for uf in por_uf}}
        caminho = os.path.join(OUT, str(ano), f"t{turno}", "c1")
        with open(os.path.join(caminho, "br.json"), "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
        resumo[f"t{turno}"]["c1"].append("br")

    escrever_municipios(ano, cand, mun, pmun, det, nomes_mun, uf_mun, fonte)

    for p in (zc, zd):
        if p and os.environ.get("ETL_KEEP_ZIP") != "1":
            os.remove(p)
    return {t: {c: sorted(u) for c, u in cs.items()} for t, cs in resumo.items()}


TOP = {1: 6, 3: 6, 5: 6, 11: 6, 13: 15}


def escrever_municipios(ano, cand, mun, pmun, det, nomes_mun, uf_mun, fonte):
    """Um arquivo por município com todas as eleições dele: data/mun/<uf>/<cd>.json.
    Cada ano reprocessado substitui só as chaves daquele ano."""
    por_mun = defaultdict(dict)
    for (turno, cargo, uf), ms in pmun.items():
        for cdm, partidos in ms.items():
            chave = f"{ano}-t{turno}-c{cargo}"
            e = {"partidos": dict(sorted(partidos.items(), key=lambda kv: -kv[1])),
                 "det": det[(turno, cargo, uf)].get(cdm, [0] * 5)}
            if cargo in POR_MUNICIPIO:
                cs = cand[(turno, cargo, uf)]
                votos = sorted(mun[(turno, cargo, uf)][cdm].items(), key=lambda kv: -kv[1])[:TOP[cargo]]
                e["cands"] = [{"n": cs[sq]["n"], "nm": cs[sq]["nm"], "p": cs[sq]["p"], "sit": cs[sq]["sit"], "v": v} for sq, v in votos if v]
            por_mun[cdm][chave] = e
    base = os.path.join(OUT, "mun")
    idx_path = os.path.join(base, "index.json")
    indice = json.load(open(idx_path, encoding="utf-8")) if os.path.exists(idx_path) else {}
    for cdm, eleicoes in por_mun.items():
        uf = uf_mun[cdm]
        caminho = os.path.join(base, uf)
        os.makedirs(caminho, exist_ok=True)
        arq = os.path.join(caminho, f"{cdm}.json")
        doc = json.load(open(arq, encoding="utf-8")) if os.path.exists(arq) else {"cd": cdm, "uf": uf, "eleicoes": {}}
        doc["nm"] = nomes_mun.get(cdm, cdm)
        doc["eleicoes"] = {k: v for k, v in doc["eleicoes"].items() if not k.startswith(f"{ano}-")}
        doc["eleicoes"].update(eleicoes)
        doc.setdefault("fontes", {})[str(ano)] = fonte
        with open(arq, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
        indice[cdm] = [doc["nm"], uf]
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(indice, f, ensure_ascii=False, separators=(",", ":"))


def main():
    anos = [int(a) for a in sys.argv[1:]] or ANOS
    os.makedirs(OUT, exist_ok=True)
    ipath = os.path.join(OUT, "index.json")
    index = json.load(open(ipath, encoding="utf-8")) if os.path.exists(ipath) else {"anos": {}}
    index["cargos"] = {str(k): v for k, v in CARGOS.items()}
    falhas = []
    for ano in anos:
        try:
            index["anos"][str(ano)] = processar_ano(ano)
        except Exception as e:
            print(f"!! {ano}: {e}", flush=True)
            falhas.append(ano)
        index["atualizado_em"] = time.strftime("%Y-%m-%d %H:%M")
        with open(ipath, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=1, sort_keys=True)
    if falhas:
        print("Anos com falha:", falhas)
        sys.exit(1 if len(falhas) == len(anos) else 0)


if __name__ == "__main__":
    main()
