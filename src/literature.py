"""Adversarial novelty check + Figure 6 literature counts via NCBI E-utilities."""
from __future__ import annotations
import json, ssl, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET
import certifi
CTX=ssl.create_default_context(cafile=certifi.where())

from pathlib import Path
CACHE=Path(__file__).resolve().parent.parent/"audit"/"novelty_raw.json"
BASE="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
import os
# NCBI asks callers to identify themselves. The address comes from the
# environment so it is never committed; set NCBI_EMAIL before a fresh fetch.
TOOL={"tool":"medicare-access-pipeline", **({"email": os.environ["NCBI_EMAIL"]} if os.environ.get("NCBI_EMAIL") else {})}
PAUSE=0.4

def _get(ep:str, **params)->bytes:
    q=urllib.parse.urlencode({**TOOL,**params})
    with urllib.request.urlopen(f"{BASE}{ep}?{q}", timeout=60, context=CTX) as r:
        return r.read()

def esearch(term:str, retmax:int=200, **kw)->dict:
    time.sleep(PAUSE)
    return json.loads(_get("esearch.fcgi", db="pubmed", term=term,
                           retmax=retmax, retmode="json", **kw))["esearchresult"]

def summaries(ids:list[str])->list[dict]:
    if not ids: return []
    time.sleep(PAUSE)
    root=ET.fromstring(_get("esummary.fcgi", db="pubmed", id=",".join(ids), retmode="xml"))
    out=[]
    for doc in root.findall(".//DocSum"):
        d={i.get("Name"):"".join(i.itertext()) for i in doc.findall("Item")}
        out.append({"pmid":doc.findtext("Id"),"title":d.get("Title"),
                    "journal":d.get("Source"),"date":d.get("PubDate"),
                    "authors":d.get("AuthorList","")[:200],"doi":d.get("DOI")})
    return out

NOVELTY_QUERIES={
 "Q1_pns_title_access":'"peripheral nerve stimulation"[Title] AND (Medicare OR access OR disparities OR utilization OR geographic)',
 "Q2_code_64555":'"64555"',
 "Q3_neuromod_geo":'(neuromodulation) AND ("geographic variation" OR county OR "access to care") AND Medicare',
 "Q4_scs_pns_cms_file":'("spinal cord stimulation" OR "peripheral nerve stimulation") AND ("Medicare Provider Utilization" OR "Physician and Other Practitioners")',
 "Q5_gini_lorenz":'(Gini OR Lorenz OR concentration) AND (Medicare) AND (pain OR neuromodulation)',
 "Q6_ivpain_disparities":'"interventional pain" AND (disparities OR "access") AND (rural OR income)',
 "Q7_pns_provider_concentration":'"peripheral nerve stimulation" AND (provider OR physician) AND (concentration OR volume OR supply OR density)',
 "Q8_pns_medicare_any":'"peripheral nerve stimulation" AND Medicare',
}

# Figure 6: matched access/utilization queries, SCS vs PNS, by year.
FIG6={
 "SCS":'("spinal cord stimulation"[Title/Abstract]) AND (access[Title/Abstract] OR utilization[Title/Abstract] OR disparities[Title/Abstract] OR "geographic variation"[Title/Abstract] OR epidemiology[Title/Abstract])',
 "PNS":'("peripheral nerve stimulation"[Title/Abstract]) AND (access[Title/Abstract] OR utilization[Title/Abstract] OR disparities[Title/Abstract] OR "geographic variation"[Title/Abstract] OR epidemiology[Title/Abstract])',
}
YEARS=list(range(2015,2025))

def load_or_fetch()->dict:
    """Return the cached literature payload, fetching it from PubMed if absent."""
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    main()
    return json.loads(CACHE.read_text())


def main()->None:
    result={"novelty":{},"fig6":{"queries":FIG6,"counts":{}}}
    for key,term in NOVELTY_QUERIES.items():
        r=esearch(term, retmax=60)
        ids=r.get("idlist",[])
        result["novelty"][key]={"term":term,"count":int(r["count"]),
                                "records":summaries(ids[:40])}
        print(f"{key}: {r['count']} hits")
    for arm,term in FIG6.items():
        result["fig6"]["counts"][arm]={}
        for y in YEARS:
            r=esearch(f"{term} AND {y}[dp]", retmax=0)
            result["fig6"]["counts"][arm][y]=int(r["count"])
        print(arm, result["fig6"]["counts"][arm])
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(result, indent=1))
    print(f"written {CACHE}")

if __name__=="__main__":
    main()
