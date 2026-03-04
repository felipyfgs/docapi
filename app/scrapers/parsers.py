import re
from datetime import datetime


def data_br_para_iso(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip()
    try:
        return datetime.strptime(s, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse_cnae(s: str | None) -> dict | None:
    if not s:
        return None
    s = s.strip()
    # "10.31-7-00 - Fabricação de conservas de frutas"
    m = re.match(r'^([\d.]+[-/][\d.-]+)\s*-\s*(.+)$', s)
    if m:
        return {"codigo": m.group(1).strip(), "descricao": m.group(2).strip()}
    return {"codigo": None, "descricao": s}


def parse_natureza_juridica(s: str | None) -> dict | None:
    if not s:
        return None
    s = s.strip()
    # "213-5 - Empresário (Individual)" ou "206-2 - Sociedade Empresária Limitada"
    m = re.match(r'^(\d{3}-\d)\s*-\s*(.+)$', s)
    if m:
        return {"codigo": m.group(1).strip(), "descricao": m.group(2).strip()}
    return {"codigo": None, "descricao": s}


def parse_capital_social(s: str | None) -> int | None:
    """Retorna valor em centavos. R$5.000,00 -> 500000"""
    if not s:
        return None
    m = re.search(r'R\$\s*([\d.]+),([\d]{2})', s.replace('\xa0', ''))
    if m:
        inteiro = m.group(1).replace('.', '')
        centavos = m.group(2)
        return int(inteiro) * 100 + int(centavos)
    return None


def parse_telefone(s: str | None) -> dict:
    if not s:
        return {"ddd": None, "numero": None}
    m = re.match(r'\((\d{2})\)\s*([\d\s-]+)', s.strip())
    if m:
        ddd = m.group(1)
        numero = re.sub(r'[\s-]', '', m.group(2))
        return {"ddd": ddd, "numero": numero if numero else None}
    digits = re.sub(r'\D', '', s)
    return {"ddd": None, "numero": digits if digits else None}


def parse_cep(s: str | None) -> str | None:
    if not s:
        return None
    digits = re.sub(r'\D', '', s)
    return digits if len(digits) == 8 else None


def parse_nome_empresarial(s: str | None) -> str | None:
    if not s:
        return None
    # Remove prefixo CNPJ que o site coloca: "64.184.902 NOME" -> "NOME"
    cleaned = re.sub(r'^\d{2}\.\d{3}\.\d{3}\s+', '', s.strip())
    return cleaned.strip() or None


def parse_status_declaracao(status: str | None) -> tuple[str | None, str | None]:
    """
    Separa status de data_apresentacao.
    "apresentada em 09/01/2026" -> ("apresentada", "2026-01-09")
    "não apresentada" -> ("não apresentada", None)
    "Não Optante" -> ("não optante", None)
    """
    if not status:
        return None, None
    s = status.strip()
    m = re.search(r'\bem\s+(\d{2}/\d{2}/\d{4})', s, re.IGNORECASE)
    if m:
        data_iso = data_br_para_iso(m.group(1))
        texto = s[:m.start()].strip()
        return texto.lower() or None, data_iso
    return s.lower(), None


def normalizar_situacao(situacao: str | None) -> str | None:
    """Normaliza case de strings de situacao do site da Receita."""
    if not situacao:
        return None
    # "NÃO enquadrado no SIMEI" -> "Não enquadrado no SIMEI"
    return re.sub(r'\bNÃO\b', 'Não', situacao)


def parse_data_desde_situacao(situacao: str | None) -> tuple[str | None, str | None]:
    """
    Extrai data de strings como 'Optante pelo Simples Nacional desde 29/12/2025'.
    Retorna (situacao_sem_data, data_iso) ou (original, None).
    """
    if not situacao:
        return None, None
    m = re.search(r'desde\s+(\d{2}/\d{2}/\d{4})', situacao, re.IGNORECASE)
    if m:
        data_iso = data_br_para_iso(m.group(1))
        texto = situacao[:m.start()].strip().rstrip(',').strip()
        return texto, data_iso
    return situacao, None
