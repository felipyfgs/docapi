from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from .models import (
    ConsultaRequest, ConsultaResponse,
    CadastroResponse, DasnResponse, OptantesResponse,
)
from .consultar import (
    consultar_mei,
    consultar_apenas_cnpj,
    consultar_apenas_dasn,
    consultar_apenas_optantes,
)

app = FastAPI(title="Simplix", description="API de consulta MEI/CNPJ")


class ErrorResponse(BaseModel):
    detail: str


_ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "CNPJ invalido"},
    500: {"model": ErrorResponse, "description": "Erro interno"},
    502: {"model": ErrorResponse, "description": "Falha no servico externo (Receita/SEFAZ)"},
    504: {"model": ErrorResponse, "description": "Timeout no servico externo"},
}


async def _safe_call(fn, *args):
    try:
        return await fn(*args)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PlaywrightTimeoutError as e:
        raise HTTPException(status_code=504, detail=f"Timeout no servico externo: {e}")
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=f"Timeout no servico externo: {e}")
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/consultar", response_model=ConsultaResponse, responses=_ERROR_RESPONSES)
async def consultar(req: ConsultaRequest):
    return await _safe_call(consultar_mei, req.cnpj)


@app.post("/consultar/cnpj", response_model=CadastroResponse, responses=_ERROR_RESPONSES)
async def consultar_cnpj(req: ConsultaRequest):
    return await _safe_call(consultar_apenas_cnpj, req.cnpj)


@app.post("/consultar/dasn", response_model=DasnResponse, responses=_ERROR_RESPONSES)
async def consultar_dasn(req: ConsultaRequest):
    return await _safe_call(consultar_apenas_dasn, req.cnpj)


@app.post("/consultar/optantes", response_model=OptantesResponse, responses=_ERROR_RESPONSES)
async def consultar_optantes(req: ConsultaRequest):
    return await _safe_call(consultar_apenas_optantes, req.cnpj)


@app.get("/health")
async def health():
    return {"status": "ok"}
