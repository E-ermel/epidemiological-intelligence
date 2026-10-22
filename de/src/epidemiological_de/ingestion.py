"""
Utilitários compartilhados pela ingestão automática (fonte -> bronze).

Layout de fontes snapshot (IBGE, SIDRA, MapBiomas...):

    <BRONZE_ROOT>/<fonte>/ingestion_date=YYYY-MM-DD/<arquivo>
    <BRONZE_ROOT>/<fonte>/ingestion_date=YYYY-MM-DD/<arquivo>.manifest.json

Cada arquivo tem um manifesto ao lado, com origem, tipo de fonte e hash,
para auditar de onde veio cada dado. Um snapshot novo só é gravado
quando o conteúdo mudou em relação ao último (sha256), então rodar a
ingestão de novo sem mudança na fonte não acumula cópias.
"""

import hashlib
import json
import time
from datetime import date, datetime, timezone

import fsspec
import requests

from epidemiological_de import config

# 🟢 oficial: órgão público produtor do dado (IBGE, DATASUS, INMET, INPE...)
# 🟡 institucional: instituição pública/multilateral em parceria (Atlas/PNUD)
# 🟠 relacionada: rede técnico-científica, não oficial (MapBiomas)
# 🔵 espelho: cópia curada de fonte oficial por terceiros (Base dos Dados)
SOURCE_TYPES = {"oficial", "institucional", "relacionada", "espelho"}

MANIFEST_SUFFIX = ".manifest.json"

RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# Alguns portais do governo cortam a conexão de clientes sem cara de
# navegador (o INMET derruba o User-Agent padrão do curl, por exemplo).
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    )
}

DOWNLOAD_CHUNK_BYTES = 8 * 1024 * 1024


def new_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    return session


def _with_retry(url: str, request, *, retries: int, backoff_seconds: float):
    """
    Executa `request()` com retry e backoff exponencial para falhas
    transitórias (rede, 429, 5xx). Erros 4xx que não sejam 429 falham
    na hora: URL errada não melhora tentando de novo.
    """

    last_error: Exception | None = None

    for attempt in range(retries):
        try:
            response = request()

            if response.status_code in RETRYABLE_STATUS:
                last_error = requests.HTTPError(
                    f"HTTP {response.status_code} em {url}", response=response
                )
            else:
                response.raise_for_status()
                return response

        except (requests.ConnectionError, requests.Timeout) as error:
            last_error = error

        if attempt < retries - 1:
            time.sleep(backoff_seconds * 2**attempt)

    raise RuntimeError(
        f"Falha ao baixar {url} após {retries} tentativas: {last_error}"
    ) from last_error


def http_get(
    url: str,
    *,
    session: requests.Session | None = None,
    timeout: int = 120,
    retries: int = 4,
    backoff_seconds: float = 5.0,
) -> bytes:
    """
    GET com a resposta inteira em memória -- para respostas de API
    (alguns MB). Arquivos grandes vão por download_if_changed().
    """

    session = session or new_session()
    response = _with_retry(
        url,
        lambda: session.get(url, timeout=timeout),
        retries=retries,
        backoff_seconds=backoff_seconds,
    )
    return response.content


def snapshot_dir(source: str, ingestion_date: date, root: str | None = None) -> str:
    root = (root or config.BRONZE_ROOT).rstrip("/")
    return f"{root}/{source}/ingestion_date={ingestion_date.isoformat()}"


def _snapshot_dates(source: str, root: str | None = None) -> list[str]:
    root = (root or config.BRONZE_ROOT).rstrip("/")
    fs, base = fsspec.core.url_to_fs(f"{root}/{source}")

    if not fs.exists(base):
        return []

    return sorted(
        entry.rstrip("/").split("ingestion_date=")[-1]
        for entry in fs.ls(base, detail=False)
        if "ingestion_date=" in entry
    )


def latest_file(source: str, filename: str, root: str | None = None) -> str | None:
    """
    Caminho da versão mais recente de `filename` no bronze da fonte, ou
    None se nunca foi ingerido. Procura snapshot a snapshot, do mais
    novo para o mais antigo, porque um snapshot só contém os arquivos
    que mudaram naquela ingestão.
    """

    for ingestion_date in reversed(_snapshot_dates(source, root)):
        candidate = f"{snapshot_dir(source, date.fromisoformat(ingestion_date), root)}/{filename}"
        fs, path = fsspec.core.url_to_fs(candidate)
        if fs.exists(path):
            return candidate

    return None


def read_manifest(file_path: str) -> dict | None:
    fs, path = fsspec.core.url_to_fs(file_path + MANIFEST_SUFFIX)
    if not fs.exists(path):
        return None

    with fs.open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_snapshot(
    content: bytes,
    *,
    source: str,
    filename: str,
    url: str,
    source_type: str,
    ingestion_date: date | None = None,
    root: str | None = None,
) -> str | None:
    """
    Grava `content` como `filename` no snapshot do dia, com manifesto.
    Retorna o caminho gravado, ou None se o conteúdo é idêntico à última
    versão ingerida (nada é gravado nesse caso).
    """

    if source_type not in SOURCE_TYPES:
        raise ValueError(
            f"source_type inválido: {source_type!r} (use um de {sorted(SOURCE_TYPES)})"
        )

    sha256 = hashlib.sha256(content).hexdigest()

    previous = latest_file(source, filename, root)
    if previous is not None:
        previous_manifest = read_manifest(previous)
        if previous_manifest is not None and previous_manifest.get("sha256") == sha256:
            return None

    ingestion_date = ingestion_date or datetime.now(timezone.utc).date()
    dest = f"{snapshot_dir(source, ingestion_date, root)}/{filename}"

    manifest = {
        "source": source,
        "source_type": source_type,
        "url": url,
        "filename": filename,
        "size_bytes": len(content),
        "sha256": sha256,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
    }

    # Dados primeiro, manifesto depois: um manifesto só existe para um
    # arquivo que foi gravado por inteiro.
    with fsspec.open(dest, "wb", auto_mkdir=True) as f:
        f.write(content)

    with fsspec.open(dest + MANIFEST_SUFFIX, "w", encoding="utf-8", auto_mkdir=True) as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return dest


def _remote_version(headers) -> dict:
    """O que identifica a versão de um arquivo remoto, pelos cabeçalhos HTTP."""

    return {
        "etag": headers.get("ETag"),
        "last_modified": headers.get("Last-Modified"),
        "content_length": headers.get("Content-Length"),
    }


def download_if_changed(
    url: str,
    dest: str,
    *,
    source: str,
    source_type: str,
    session: requests.Session | None = None,
    timeout: int = 300,
    retries: int = 4,
    backoff_seconds: float = 5.0,
) -> str | None:
    """
    Download em streaming de um arquivo grande para `dest` (caminho fixo
    na partição natural da fonte, ex.: bronze/inmet/year=2024/2024.zip),
    com manifesto ao lado.

    Antes de baixar, um HEAD compara ETag/Last-Modified/tamanho com o
    manifesto da versão atual: se a fonte não mudou, nada é baixado e a
    função retorna None. Assim anos "fechados" custam um HEAD por
    rodada, mas revisões tardias da fonte ainda são captadas.
    """

    if source_type not in SOURCE_TYPES:
        raise ValueError(
            f"source_type inválido: {source_type!r} (use um de {sorted(SOURCE_TYPES)})"
        )

    session = session or new_session()

    head = _with_retry(
        url,
        lambda: session.head(url, timeout=timeout, allow_redirects=True),
        retries=retries,
        backoff_seconds=backoff_seconds,
    )
    remote = _remote_version(head.headers)

    current = read_manifest(dest)
    if current is not None and current.get("remote") == remote and remote["etag"]:
        return None

    response = _with_retry(
        url,
        lambda: session.get(url, timeout=timeout, stream=True),
        retries=retries,
        backoff_seconds=backoff_seconds,
    )

    # Grava num temporário e só move para `dest` no fim: uma queda no
    # meio do download não deixa um arquivo truncado no lugar da versão
    # anterior, que continua válida.
    tmp_dest = dest + ".partial"
    digest = hashlib.sha256()
    size = 0

    with response, fsspec.open(tmp_dest, "wb", auto_mkdir=True) as f:
        for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_BYTES):
            digest.update(chunk)
            size += len(chunk)
            f.write(chunk)

    expected = remote["content_length"]
    if expected is not None and int(expected) != size:
        fs, tmp_path = fsspec.core.url_to_fs(tmp_dest)
        fs.rm(tmp_path)
        raise RuntimeError(
            f"Download incompleto de {url}: esperado {expected} bytes, recebido {size}"
        )

    fs, tmp_path = fsspec.core.url_to_fs(tmp_dest)
    _, dest_path = fsspec.core.url_to_fs(dest)
    fs.mv(tmp_path, dest_path)

    manifest = {
        "source": source,
        "source_type": source_type,
        "url": url,
        "filename": dest.rstrip("/").split("/")[-1],
        "size_bytes": size,
        "sha256": digest.hexdigest(),
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "remote": remote,
    }

    with fsspec.open(dest + MANIFEST_SUFFIX, "w", encoding="utf-8", auto_mkdir=True) as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return dest
