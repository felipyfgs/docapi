import time
import requests
from .config import NOPECHA_API_KEY

API_TOKEN_URL = "https://api.nopecha.com/token"


def _submit_job(captcha_type: str, website_url: str, site_key: str, enterprise: bool = False) -> str:
    """Submete job ao NoPeCHA e retorna o job_id."""
    if not NOPECHA_API_KEY:
        raise RuntimeError("NOPECHA_API_KEY nao configurada")

    payload = {
        "key": NOPECHA_API_KEY,
        "type": captcha_type,
        "sitekey": site_key,
        "url": website_url,
    }
    if enterprise:
        payload["enterprise"] = True

    r = requests.post(API_TOKEN_URL, json=payload, timeout=30)

    if not r.text.strip():
        raise RuntimeError(f"NoPeCHA retornou resposta vazia (HTTP {r.status_code})")

    resp = r.json()
    if "data" not in resp:
        raise RuntimeError(f"NoPeCHA submit erro: {resp.get('message', r.text[:200])}")
    return resp["data"]


def _poll_token(job_id: str, timeout_s: int = 180) -> str:
    """Aguarda resolucao do token pelo NoPeCHA."""
    for _ in range(timeout_s):
        time.sleep(1)
        r = requests.get(API_TOKEN_URL, params={
            "key": NOPECHA_API_KEY,
            "id": job_id,
        }, timeout=30)

        if not r.text.strip():
            continue

        data = r.json()
        if r.status_code == 200 and isinstance(data.get("data"), str) and len(data["data"]) > 100:
            return data["data"]
        if r.status_code == 409 or data.get("error") == 14:
            continue
        raise RuntimeError(f"NoPeCHA solve erro: {data.get('message', r.text[:200])}")
    raise RuntimeError(f"NoPeCHA timeout ({timeout_s}s)")


def _resolver_token(captcha_type: str, website_url: str, site_key: str,
                    enterprise: bool = False, timeout_s: int = 180) -> str:
    job_id = _submit_job(captcha_type, website_url, site_key, enterprise=enterprise)
    return _poll_token(job_id, timeout_s)


def submit_recaptcha_v2(website_url: str, site_key: str, enterprise: bool = False) -> str:
    """Submete job reCAPTCHA v2 e retorna job_id (nao-bloqueante)."""
    return _submit_job("recaptcha2", website_url, site_key, enterprise=enterprise)


def poll_recaptcha_token(job_id: str, timeout_s: int = 180) -> str:
    """Aguarda token do job reCAPTCHA (bloqueante)."""
    return _poll_token(job_id, timeout_s)


def resolver_hcaptcha(website_url: str, site_key: str) -> str:
    return _resolver_token("hcaptcha", website_url, site_key)


def resolver_recaptcha_v2(website_url: str, site_key: str, enterprise: bool = False) -> str:
    return _resolver_token("recaptcha2", website_url, site_key, enterprise=enterprise)
