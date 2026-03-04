ALERT_SELECTORS = [
    # Bootstrap alerts (Optantes, CNPJ antigo)
    ".alert",
    ".alert-danger",
    ".alert-warning",
    ".alert-info",
    # Design System do Governo (DSGOV - DASN, novos sistemas Receita)
    ".br-message",
    ".br-notification",
    # Feedback generico Receita
    ".feedback:not(.d-none)",
    ".feedback-danger",
    ".feedback-warning",
    # Elementos acessiveis
    "[role='alert']",
    "[role='alertdialog']",
    # Classes customizadas governo
    ".mensagem",
    ".mensagem-erro",
    ".mensagem-aviso",
    ".aviso",
    ".erro",
]

_JS_CAPTURAR = """(selectors) => {
    const seen = new Set();
    const alertas = [];
    for (const sel of selectors) {
        for (const el of document.querySelectorAll(sel)) {
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden') continue;
            const text = el.innerText ? el.innerText.trim() : el.textContent.trim();
            if (text && !seen.has(text)) {
                seen.add(text);
                alertas.push(text);
            }
        }
    }
    return alertas;
}"""


async def capturar_alertas(page) -> list[str]:
    try:
        return await page.evaluate(_JS_CAPTURAR, ALERT_SELECTORS)
    except Exception:
        return []
