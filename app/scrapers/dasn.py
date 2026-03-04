from ..config import DASN_URL
from .utils import capturar_alertas
from .parsers import data_br_para_iso, parse_nome_empresarial, parse_status_declaracao


async def consultar_dasn(page, cnpj_limpo: str) -> dict:
    await page.goto(f"{DASN_URL}/Identificacao", wait_until="domcontentloaded")
    await page.wait_for_selector("#identificacao-cnpj", timeout=10000)
    await page.fill("#identificacao-cnpj", cnpj_limpo)

    await page.click("#identificacao-continuar")
    try:
        await page.wait_for_url("**/dasnsimei.app/", timeout=30000)
    except Exception:
        alertas = await capturar_alertas(page)
        detalhe = " | ".join(alertas) if alertas else "Resposta inesperada"
        raise RuntimeError(f"DASN - Falha: {detalhe[:300]}")

    await page.wait_for_selector("#iniciar-ano-calendario", timeout=10000)

    razao_social = await page.evaluate("""() => {
        const ps = document.querySelectorAll('p');
        for (let i = 0; i < ps.length; i++) {
            const strong = ps[i].querySelector('strong');
            if (strong && strong.textContent.includes('Raz') && i + 1 < ps.length)
                return ps[i + 1].textContent.trim();
        }
        return '';
    }""")

    declaracoes = await page.evaluate("""() => {
        const container = document.querySelector('#iniciar-ano-calendario');
        if (!container) return [];
        const radios = container.querySelectorAll('input[type="radio"]');
        return Array.from(radios).map(radio => {
            const parent = radio.parentElement;
            const spans = parent.querySelectorAll('span');
            let statusTexto = '', acao = '';
            spans.forEach(span => {
                const cls = span.className || '';
                const text = span.textContent.trim();
                if (cls.includes('br-tag')) acao = text;
                else if (text) statusTexto = text;
            });
            const baixada = acao.toLowerCase() === 'baixada' || statusTexto.toLowerCase() === 'baixada';
            const pendente = !radio.disabled && statusTexto.toLowerCase().includes('não apresentada');
            return {
                ano: radio.value,
                tipo_declaracao: radio.dataset.tipoDeclaracao || '',
                situacao_especial: radio.dataset.situacaoEspecialTipo || '-',
                data_baixa: radio.dataset.situacaoEspecialEventobaixa || '-',
                status: statusTexto || acao,
                pendente, baixada,
            };
        });
    }""")

    mei_baixada = any(d["baixada"] for d in declaracoes)
    data_baixa_raw = next(
        (d["data_baixa"] for d in declaracoes
         if d["data_baixa"] != "-" and d["situacao_especial"] == "Extinção"),
        None,
    )
    pendentes = [int(d["ano"]) for d in declaracoes if d["pendente"] and d["ano"].isdigit()]

    cleaned = []
    for d in declaracoes:
        sit = d["situacao_especial"] if d["situacao_especial"] != "-" else None
        db_raw = d["data_baixa"] if d["data_baixa"] != "-" else None
        status_norm, data_apresentacao = parse_status_declaracao(d["status"] or None)
        tipo_decl = (d["tipo_declaracao"] or "").strip()
        cleaned.append({
            "ano": int(d["ano"]) if d["ano"].isdigit() else d["ano"],
            "retificadora": tipo_decl.lower() == "retificadora",
            "status": status_norm,
            "data_apresentacao": data_apresentacao,
            "pendente": d["pendente"],
            "baixada": d["baixada"],
            "situacao_especial": sit,
            "data_baixa": data_br_para_iso(db_raw),
        })

    alertas = await capturar_alertas(page)

    return {
        "razao_social": parse_nome_empresarial(razao_social) if razao_social else None,
        "mei_baixada": mei_baixada,
        "data_baixa": data_br_para_iso(data_baixa_raw),
        "declaracoes": cleaned,
        "pendentes": pendentes,
        "alertas": alertas,
    }
