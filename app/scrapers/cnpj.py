import asyncio
from ..config import CNPJ_URL, CNPJ_QSA_URL, CNPJ_HCAPTCHA_SITEKEY, NOPECHA_API_KEY
from ..captcha import resolver_hcaptcha
from .utils import capturar_alertas
from .parsers import (
    data_br_para_iso, parse_cnae, parse_natureza_juridica,
    parse_capital_social, parse_telefone, parse_cep, parse_nome_empresarial,
)

_NULOS = {"", "********", "*****"}


def _limpar(valor) -> str | None:
    if not valor:
        return None
    v = str(valor).strip()
    return None if v in _NULOS else v


_JS_EXTRAI_COMPROVANTE = """() => {
    const findTd = (label, exact = false) => {
        for (const font of document.querySelectorAll('font[style]')) {
            const style = font.getAttribute('style') || '';
            if (!style.includes('6pt')) continue;
            const text = font.textContent.trim();
            if (exact ? text === label : text.includes(label)) {
                return font.closest('td');
            }
        }
        return null;
    };

    const getVal = (label, exact = false) => {
        const td = findTd(label, exact);
        if (!td) return '';
        const b = td.querySelector('font[style*="8pt"] b, b');
        return b ? b.textContent.trim() : '';
    };

    const IGNORAR = ['********', 'não informada', 'nao informada', 'nenhuma'];
    const getCnaes = (label) => {
        const td = findTd(label);
        if (!td) return [];
        return Array.from(td.querySelectorAll('font[style*="8pt"] b, b'))
            .map(b => b.textContent.trim())
            .filter(v => v && !IGNORAR.includes(v.toLowerCase()));
    };

    const inscricaoTd = findTd('NÚMERO DE INSCRIÇÃO');
    let tipo_estabelecimento = '';
    if (inscricaoTd) {
        const bolds = inscricaoTd.querySelectorAll('b');
        if (bolds.length >= 2) tipo_estabelecimento = bolds[1].textContent.trim();
    }

    return {
        nome_empresarial:          getVal('NOME EMPRESARIAL'),
        nome_fantasia:             getVal('TÍTULO DO ESTABELECIMENTO'),
        tipo_estabelecimento:      tipo_estabelecimento,
        data_abertura:             getVal('DATA DE ABERTURA'),
        porte:                     getVal('PORTE'),
        atividade_principal:       getVal('ATIVIDADE ECONÔMICA PRINCIPAL'),
        atividades_secundarias:    getCnaes('ATIVIDADES ECONÔMICAS SECUNDÁRIAS'),
        natureza_juridica:         getVal('NATUREZA JURÍDICA'),
        ente_federativo:           getVal('ENTE FEDERATIVO'),
        logradouro:                getVal('LOGRADOURO'),
        numero:                    getVal('NÚMERO', true),
        complemento:               getVal('COMPLEMENTO'),
        cep:                       getVal('CEP'),
        bairro:                    getVal('BAIRRO/DISTRITO'),
        municipio:                 getVal('MUNICÍPIO'),
        uf:                        getVal('UF'),
        email:                     getVal('ENDEREÇO ELETRÔNICO'),
        telefone:                  getVal('TELEFONE'),
        situacao_cadastral:        getVal('SITUAÇÃO CADASTRAL'),
        data_situacao_cadastral:   getVal('DATA DA SITUAÇÃO CADASTRAL'),
        motivo_situacao_cadastral: getVal('MOTIVO DE SITUAÇÃO CADASTRAL'),
        situacao_especial:         getVal('SITUAÇÃO ESPECIAL'),
        data_situacao_especial:    getVal('DATA DA SITUAÇÃO ESPECIAL'),
    };
}"""

_JS_EXTRAI_QSA = """() => {
    let capital_social = null;
    const capitalDiv = document.querySelector('#capital');
    if (capitalDiv) {
        const rows = capitalDiv.querySelectorAll('.row');
        for (const row of rows) {
            const label = row.querySelector('.col-md-3');
            const value = row.querySelector('.col-md-9');
            if (label && value && label.textContent.includes('CAPITAL SOCIAL')) {
                capital_social = value.textContent.trim();
                break;
            }
        }
    }

    const socios = [];
    for (const card of document.querySelectorAll('.alert.alert-warning')) {
        let nome = null, qualificacao = null;
        for (const row of card.querySelectorAll('.row')) {
            const label = row.querySelector('.col-md-3');
            const value = row.querySelector('.col-md-9, .col-md-5');
            if (!label || !value) continue;
            const lbl = label.textContent.trim();
            const val = value.textContent.trim();
            if (lbl.includes('Nome')) nome = val;
            else if (lbl.includes('Qualifica')) qualificacao = val;
        }
        if (nome) socios.push({ nome, qualificacao });
    }

    return { capital_social, socios };
}"""


_JS_INJETAR_HCAPTCHA = """(token) => {
    document.querySelectorAll(
        '[name="h-captcha-response"], [name="g-recaptcha-response"]'
    ).forEach(el => { el.value = token; });

    if (window.hcaptcha) {
        try {
            const ids = window.hcaptcha.getAllIds ? window.hcaptcha.getAllIds() : [];
            for (const id of ids) {
                if (!window.hcaptcha.getResponse(id)) {
                    if (window.hcaptcha.setResponse) window.hcaptcha.setResponse(id, token);
                }
            }
        } catch (_) {}
    }

    const iframe = document.querySelector('iframe[data-hcaptcha-widget-id]');
    if (iframe) iframe.setAttribute('data-hcaptcha-response', token);
}"""


async def consultar_cnpj(page, cnpj_limpo: str, max_retries: int = 3) -> dict:
    page_url = f"{CNPJ_URL}?cnpj={cnpj_limpo}"

    for attempt in range(max_retries):
        await page.goto(page_url, wait_until="domcontentloaded")
        await page.wait_for_selector('iframe[title*="Widget contendo"]', timeout=10000)

        captcha_resolved = False

        # 1) NoPeCHA primeiro (mais confiavel que click)
        if NOPECHA_API_KEY and not captcha_resolved:
            try:
                token = await asyncio.to_thread(
                    resolver_hcaptcha, page_url, CNPJ_HCAPTCHA_SITEKEY
                )
                await page.evaluate(_JS_INJETAR_HCAPTCHA, token)
                captcha_resolved = True
            except Exception as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"CNPJ - Captcha solver falhou: {e}")

        # 2) Fallback: click no checkbox (funciona se hCaptcha nao pedir desafio)
        if not captcha_resolved:
            try:
                captcha_frame = page.frame_locator('iframe[title*="Widget contendo"]')
                checkbox = captcha_frame.locator("#checkbox")
                await checkbox.wait_for(timeout=5000)
                await checkbox.click()
                checked = captcha_frame.locator('[aria-checked="true"]')
                await checked.wait_for(timeout=8000)
                captcha_resolved = True
            except Exception:
                pass

        if not captcha_resolved:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 + attempt * 2)
                continue
            raise RuntimeError("CNPJ - Captcha nao resolvido (configure NOPECHA_API_KEY)")

        await page.locator("button:has-text('Consultar')").click(force=True)
        try:
            await page.wait_for_url("**/Cnpjreva_Comprovante*", timeout=30000)
            break
        except Exception:
            alertas = await capturar_alertas(page)
            if attempt < max_retries - 1:
                await asyncio.sleep(2 + attempt * 2)
                continue
            detalhe = " | ".join(alertas) if alertas else await page.evaluate("() => document.body.innerText.substring(0, 300)")
            raise RuntimeError(f"CNPJ - Falha apos captcha: {detalhe[:300]}")

    dados = await page.evaluate(_JS_EXTRAI_COMPROVANTE)
    alertas = await capturar_alertas(page)

    # Navegar para QSA na mesma sessao (sem novo captcha)
    capital_social = None
    socios = []
    try:
        await page.goto(CNPJ_QSA_URL, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_selector("#capital", timeout=10000)
        qsa = await page.evaluate(_JS_EXTRAI_QSA)
        capital_social = _limpar(qsa.get("capital_social"))
        socios = [
            {"nome": s["nome"].strip(), "qualificacao": _limpar(s.get("qualificacao"))}
            for s in qsa.get("socios", [])
            if s.get("nome")
        ]
    except Exception:
        pass

    email_raw = _limpar(dados.get("email"))
    tipo_estab = (_limpar(dados.get("tipo_estabelecimento")) or "").upper()
    sit_raw = (_limpar(dados.get("situacao_cadastral")) or "").upper()

    resultado = {
        "nome_empresarial":       parse_nome_empresarial(_limpar(dados.get("nome_empresarial"))),
        "nome_fantasia":          _limpar(dados.get("nome_fantasia")),
        "matriz":                 tipo_estab != "FILIAL",
        "data_abertura":          data_br_para_iso(_limpar(dados.get("data_abertura"))),
        "porte":                  _limpar(dados.get("porte")),
        "atividade_principal":    parse_cnae(_limpar(dados.get("atividade_principal"))),
        "atividades_secundarias": [parse_cnae(c) for c in (dados.get("atividades_secundarias") or []) if c],
        "natureza_juridica":      parse_natureza_juridica(_limpar(dados.get("natureza_juridica"))),
        "ente_federativo":        _limpar(dados.get("ente_federativo")),
        "endereco": {
            "logradouro":  _limpar(dados.get("logradouro")),
            "numero":      _limpar(dados.get("numero")),
            "complemento": _limpar(dados.get("complemento")),
            "bairro":      _limpar(dados.get("bairro")),
            "municipio":   _limpar(dados.get("municipio")),
            "uf":          _limpar(dados.get("uf")),
            "cep":         parse_cep(_limpar(dados.get("cep"))),
        },
        "contato": {
            "email":    email_raw.lower() if email_raw else None,
            "telefone": parse_telefone(_limpar(dados.get("telefone"))),
        },
        "situacao_cadastral": {
            "ativa":    sit_raw == "ATIVA",
            "baixada":  sit_raw == "BAIXADA",
            "suspensa": sit_raw == "SUSPENSA",
            "inapta":   sit_raw == "INAPTA",
            "nula":     sit_raw == "NULA",
            "data":     data_br_para_iso(_limpar(dados.get("data_situacao_cadastral"))),
            "motivo":   _limpar(dados.get("motivo_situacao_cadastral")),
        },
        "situacao_especial":      _limpar(dados.get("situacao_especial")),
        "data_situacao_especial": data_br_para_iso(_limpar(dados.get("data_situacao_especial"))),
        "capital_social":         parse_capital_social(capital_social),
        "socios":                 socios,
        "alertas":                alertas,
    }

    campos_criticos = ["nome_empresarial", "situacao_cadastral", "data_abertura"]
    if all(resultado.get(c) is None for c in campos_criticos):
        page_text = await page.evaluate("() => document.body.innerText.substring(0, 500)")
        detalhe = " | ".join(alertas) if alertas else page_text[:300]
        raise RuntimeError(f"CNPJ - Pagina carregou mas dados nao extraidos: {detalhe}")

    return resultado
