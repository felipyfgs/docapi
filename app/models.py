from pydantic import BaseModel, field_validator


class ConsultaRequest(BaseModel):
    cnpj: str

    @field_validator("cnpj")
    @classmethod
    def validar_cnpj(cls, v: str) -> str:
        limpo = v.replace(".", "").replace("/", "").replace("-", "")
        if len(limpo) != 14 or not limpo.isdigit():
            raise ValueError("CNPJ invalido")
        return v


# --- CNPJ ---

class Cnae(BaseModel):
    codigo: str | None = None
    descricao: str | None = None


class NaturezaJuridica(BaseModel):
    codigo: str | None = None
    descricao: str | None = None


class Telefone(BaseModel):
    ddd: str | None = None
    numero: str | None = None


class Endereco(BaseModel):
    logradouro: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    municipio: str | None = None
    uf: str | None = None
    cep: str | None = None


class Contato(BaseModel):
    email: str | None = None
    telefone: Telefone = Telefone()


class SituacaoCadastral(BaseModel):
    ativa: bool = False
    baixada: bool = False
    suspensa: bool = False
    inapta: bool = False
    nula: bool = False
    data: str | None = None
    motivo: str | None = None


class Socio(BaseModel):
    nome: str
    qualificacao: str | None = None


class CadastroResponse(BaseModel):
    nome_empresarial: str | None = None
    nome_fantasia: str | None = None
    matriz: bool = True
    data_abertura: str | None = None
    porte: str | None = None
    atividade_principal: Cnae | None = None
    atividades_secundarias: list[Cnae] = []
    natureza_juridica: NaturezaJuridica | None = None
    ente_federativo: str | None = None
    endereco: Endereco
    contato: Contato
    situacao_cadastral: SituacaoCadastral = SituacaoCadastral()
    situacao_especial: str | None = None
    data_situacao_especial: str | None = None
    capital_social: int | None = None
    socios: list[Socio] = []
    alertas: list[str] = []


# --- DASN ---

class Declaracao(BaseModel):
    ano: int
    retificadora: bool = False
    status: str | None = None
    data_apresentacao: str | None = None
    pendente: bool = False
    baixada: bool = False
    situacao_especial: str | None = None
    data_baixa: str | None = None


class DasnResponse(BaseModel):
    razao_social: str | None = None
    mei_baixada: bool = False
    data_baixa: str | None = None
    declaracoes: list[Declaracao] = []
    pendentes: list[int] = []
    alertas: list[str] = []


# --- Optantes ---

class Periodo(BaseModel):
    data_inicial: str | None = None
    data_final: str | None = None
    detalhamento: str | None = None


class SimplesInfo(BaseModel):
    optante: bool = False
    data_desde: str | None = None
    periodos_anteriores: list[Periodo] = []
    eventos_futuros: str | None = None


class SimeiInfo(BaseModel):
    enquadrado: bool = False
    data_desde: str | None = None
    periodos_anteriores: list[Periodo] = []
    eventos_futuros: str | None = None


class OptantesResponse(BaseModel):
    simples_nacional: SimplesInfo
    simei: SimeiInfo
    alertas: list[str] = []


class ConsultaResponse(BaseModel):
    cnpj: str
    cadastro: CadastroResponse
    dasn: DasnResponse
    optantes: OptantesResponse
