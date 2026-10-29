"""
Make the n8n workflow exports readable.

n8n exports are long JSON files meant for n8n, not for people. This script reads every
`*_Recall@K.json` in 05_rag_pipeline/n8n/ and writes a plain-English summary to
05_rag_pipeline/n8n/WORKFLOWS.md:

  - one overview table (report ID, embedding model, chat model, collections, input file, settings)
  - for each workflow: the nodes in the order they run, the AI sub-nodes, and unused nodes

Usage (from the project root):

    python tools/n8n_summary.py
"""

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
N8N_DIR = ROOT / "05_rag_pipeline" / "n8n"
OUT = N8N_DIR / "WORKFLOWS.md"

EMBEDDING = {
    "embeddingsOpenAi": "text-embedding-3-large",
    "embeddingsGoogleGemini": "gemini-embedding-001",
    "embeddingsCohere": "embed-english-v3.0",
}
CHAT_NAME = {
    "claude-sonnet-4-6": "Claude 4.6 Sonnet",
    "models/gemini-3.1-pro-preview": "Gemini 3.1 Pro",
    "gpt-4.1": "GPT-4.1",
    "gpt-5.4": "GPT-5.4",
}
# report Table 5.4 / 5.5: (embedding, chat) -> ID
REPORT_ID = {
    ("embed-english-v3.0", "Claude 4.6 Sonnet"): 1, ("embed-english-v3.0", "Gemini 3.1 Pro"): 2,
    ("embed-english-v3.0", "GPT-4.1"): 3, ("embed-english-v3.0", "GPT-5.4"): 4,
    ("gemini-embedding-001", "Claude 4.6 Sonnet"): 5, ("gemini-embedding-001", "Gemini 3.1 Pro"): 6,
    ("gemini-embedding-001", "GPT-4.1"): 7, ("gemini-embedding-001", "GPT-5.4"): 8,
    ("text-embedding-3-large", "Gemini 3.1 Pro"): 9, ("text-embedding-3-large", "GPT-4.1"): 10,
    ("text-embedding-3-large", "GPT-5.4"): 11, ("text-embedding-3-large", "Claude 4.6 Sonnet"): 12,
}
# short plain-English description per node type
DESCRIBE = {
    "manualTrigger": "start (manual click)",
    "readWriteFile": "read the test-set file from disk",
    "extractFromFile": "turn the .xlsx into rows",
    "splitInBatches": "loop: one issue at a time",
    "set": "pick / rename fields",
    "code": "JavaScript code",
    "httpRequest": "HTTP API call",
    "agent": "AI agent (LLM + tool)",
    "convertToFile": "write results to .xlsx",
    "vectorStoreQdrant": "Qdrant search tool",
}


def short_type(node):
    return node["type"].split(".")[-1]


def model_value(params):
    m = params.get("model", params.get("modelName"))
    if isinstance(m, dict):
        m = m.get("value")
    return (m or "").lstrip("=")


def analyse(path: Path):
    wf = json.loads(path.read_text(encoding="utf-8"))
    nodes = {n["name"]: n for n in wf["nodes"]}
    conns = wf.get("connections", {})

    info = {"file": path.name, "name": wf["name"], "embedding": "?", "chat": "?",
            "gt_collection": "?", "n_g": "?", "tax_collection": "?", "top_k": "?", "input": "?"}

    for n in wf["nodes"]:
        t, p = short_type(n), n.get("parameters", {})
        if t in EMBEDDING:
            info["embedding"] = EMBEDDING[t]
        elif t.startswith("lmChat"):
            info["chat"] = CHAT_NAME.get(model_value(p), model_value(p))
        elif t == "vectorStoreQdrant":
            info["tax_collection"] = (p.get("qdrantCollection") or {}).get("value", "?")
            info["top_k"] = p.get("topK", "?")
        elif t == "readWriteFile":
            info["input"] = str(p.get("fileSelector", "?")).lstrip("=").split("\\")[-1]
        elif t == "httpRequest":
            url = str(p.get("url", ""))
            m = re.search(r"/collections/([^/]+)/points/search", url)
            if m:
                info["gt_collection"] = m.group(1)
                lim = re.search(r'"limit"\s*:\s*(\d+)', str(p.get("jsonBody", "")))
                info["n_g"] = lim.group(1) if lim else "?"
    info["report_id"] = REPORT_ID.get((info["embedding"], info["chat"]), "?")

    # ---- run order: walk "main" connections from the trigger, split into 3 phases
    trigger = next(n["name"] for n in wf["nodes"] if short_type(n) == "manualTrigger")
    phases = {"before": [], "each": [], "after": []}
    seen, has_error_route = set(), False

    def sub_nodes(name):
        """AI sub-nodes (chat model, tool, embeddings) attached to `name`, recursively."""
        out = []
        for src, c in conns.items():
            for kind, outs in c.items():
                if kind.startswith("ai_") and any(x["node"] == name for lst in outs for x in (lst or [])):
                    seen.add(src)
                    extra = model_value(nodes[src].get("parameters", {}))
                    out.append(f"   - {kind.replace('ai_', '')}: {src}" + (f" (`{extra}`)" if extra else ""))
                    out += ["   " + line for line in sub_nodes(src)]
        return out

    def walk(name, phase):
        nonlocal has_error_route
        if name in seen:
            return
        seen.add(name)
        t = short_type(nodes[name])
        phases[phase].append(f"1. **{name}** - {DESCRIBE.get(t, t)}")
        phases[phase] += sub_nodes(name)
        outs = conns.get(name, {}).get("main", [])
        for i, lst in enumerate(outs):
            for target in lst or []:
                if t == "splitInBatches":
                    walk(target["node"], "after" if i == 0 else "each")
                elif i == 1 and len(outs) > 1:
                    has_error_route = True   # error output -> back to the loop
                else:
                    walk(target["node"], phase)

    walk(trigger, "before")
    lines = ["**Before the loop**", ""] + phases["before"] + [
        "", "**For each issue**", ""] + phases["each"] + [
        "", "**After the last issue**", ""] + phases["after"]
    if has_error_route:
        lines += ["", "_If a step fails for an issue, its error output goes back to the loop and the run continues._"]
    info["flow"] = lines
    info["unused"] = sorted(n for n in nodes if n not in seen)
    info["warning"] = ""
    agents = [n for n in nodes if short_type(nodes[n]) == "agent"]
    if agents and all(a in info["unused"] for a in agents):
        reader = next((n for n in nodes if short_type(nodes[n]) == "readWriteFile"), "?")
        nxt = [t["node"] for lst in conns.get(reader, {}).get("main", []) for t in (lst or [])]
        info["warning"] = (
            f"As saved, the AI agent is **not reachable from the start node**: `{reader}` is connected to "
            f"`{', '.join(nxt) or 'nothing'}` instead of the issue loop, so running this workflow only "
            "re-processes an existing result file. To re-run the experiment, reconnect "
            f"`{reader}` -> `Input_data` in n8n."
        )
    return info


def main():
    files = sorted(N8N_DIR.glob("*_Recall@K.json"))
    if not files:
        raise SystemExit(f"No *_Recall@K.json files in {N8N_DIR}")
    items = sorted((analyse(f) for f in files), key=lambda x: (x["report_id"] if isinstance(x["report_id"], int) else 99))

    common_input = Counter(i["input"] for i in items).most_common(1)[0][0]
    md = [
        "# n8n workflows - readable summary",
        "",
        "_Generated by `python tools/n8n_summary.py` from the JSON files in this folder. "
        "Do not edit by hand - re-run the script after changing a workflow._",
        "",
        "The `.json` files are for **importing into n8n** (see `docs/SETUP_N8N.md`). Read this page instead of the JSON.",
        "",
        "## Overview",
        "",
        "| ID | Workflow | Embedding model | Chat model | Ground-truth collection (N_g) | Taxonomy tool (top-K) | Input file |",
        "|---:|---|---|---|---|---|---|",
    ]
    for i in items:
        inp = i["input"] if i["input"] == common_input else f"**{i['input']}**"
        flag = " ⚠️" if i["warning"] else ""
        md.append(f"| {i['report_id']} | [{i['name']}](#{i['name'].lower().replace('.', '').replace('@', '')}) | {i['embedding']} | {i['chat']}{flag} "
                  f"| `{i['gt_collection']}` ({i['n_g']}) | `{i['tax_collection']}` ({i['top_k']}) | {inp} |")
    md += [
        "",
        "ID = configuration ID in report Tables 5.4 / 5.5. Input files in **bold** differ from the most common one "
        f"(`{common_input}`). ⚠️ = see the warning in that workflow's section.",
        "",
        "## How every workflow runs",
        "",
        "1. Start -> load the taxonomy (code node) -> read the test-set Excel -> loop over the issues.",
        "2. For each issue: embed *title + body* -> find the 10 most similar labelled issues in Qdrant -> "
        "format them as examples -> ask the AI agent.",
        "3. The agent can search the taxonomy in Qdrant with its tool, then answers with JSON "
        "(`is_privacy_issue`, `Ranked_Taxonomy_IDs`, `Reason`).",
        "4. After the last issue: parse all answers, map IDs to labels and write an Excel file.",
        "",
        "Prompt: [`../prompts/identification_prompt.md`](../prompts/identification_prompt.md).",
        "",
        "## Each workflow in detail",
        "",
    ]
    for i in items:
        md += [f"### {i['name']}", "",
               f"Report ID **{i['report_id']}** - {i['embedding']} + {i['chat']} - file `{i['file']}`", ""]
        if i["warning"]:
            md += [f"> ⚠️ {i['warning']}", ""]
        md += i["flow"]
        md += ["", "Unused nodes (left over from earlier tests, never run): "
               + (", ".join(f"`{u}`" for u in i["unused"]) if i["unused"] else "none"), ""]

    OUT.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(items)} workflows)")


if __name__ == "__main__":
    main()
