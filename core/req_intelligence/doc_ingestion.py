"""
Motor de ingesta de documentos para conversión a BDD.

Soporta:
  - Word (.docx): chunking semántico por encabezados H1/H2 y palabras clave en negrita.
  - Excel (.xlsx): chunking fila por fila con detección automática de columnas relevantes.

Produce objetos DocChunk que alimentan BDDDocConverter.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DocChunk:
    """Unidad mínima de contenido extraído de un documento."""
    id: str
    source_file: str
    title: str
    content: str
    chunk_type: str  # "user_story" | "test_matrix"
    row_data: Optional[Dict[str, Any]] = field(default=None)


# ---------------------------------------------------------------------------
# Palabras clave que indican el inicio de una historia de usuario en Word
# ---------------------------------------------------------------------------
_STORY_KEYWORDS = re.compile(
    r"historia\s+de\s+usuario|user\s+story|criterios?\s+de\s+aceptaci[oó]n|"
    r"acceptance\s+criteria|caso\s+de\s+(prueba|uso)|test\s+case|escenario",
    re.IGNORECASE,
)

# Nombres de columnas que suelen contener contenido relevante en matrices Excel
_COLUMN_CANDIDATES = {
    "id": ["id", "id del caso", "caso id", "case id", "num", "número", "n°"],
    "description": [
        "descripci[oó]n", "description", "titulo", "título", "title",
        "historia", "story", "caso", "case",
    ],
    "steps": [
        "pasos", "steps", "procedimiento", "procedure", "precondici[oó]n",
        "precondition", "dado", "given", "acci[oó]n", "action",
    ],
    "expected": [
        "resultado esperado", "expected result", "resultado", "result",
        "validaci[oó]n", "validation", "entonces", "then",
    ],
}


def _match_column(col_name: str, candidates: List[str]) -> bool:
    col_lower = col_name.lower().strip()
    for pattern in candidates:
        if re.search(pattern, col_lower, re.IGNORECASE):
            return True
    return False


def _detect_columns(df_columns: List[str]) -> Dict[str, Optional[str]]:
    """Detecta automáticamente qué columna del DataFrame corresponde a cada rol."""
    mapping: Dict[str, Optional[str]] = {
        "id": None, "description": None, "steps": None, "expected": None,
    }
    for col in df_columns:
        for role, patterns in _COLUMN_CANDIDATES.items():
            if mapping[role] is None and _match_column(col, patterns):
                mapping[role] = col
    return mapping


# ---------------------------------------------------------------------------
# WordIngester
# ---------------------------------------------------------------------------

class WordIngester:
    """
    Extrae chunks de un documento Word (.docx).

    Estrategia:
    1. Itera párrafos del documento.
    2. Cuando encuentra un encabezado (H1/H2) o un párrafo en negrita que coincide
       con palabras clave de historias, inicia un nuevo chunk.
    3. Acumula el texto hasta el siguiente encabezado clave.
    4. Cada chunk representa una historia de usuario o criterio de aceptación.
    """

    def ingest(self, file_path: str) -> List[DocChunk]:
        try:
            from docx import Document  # type: ignore
        except ImportError as e:
            raise ImportError(
                "python-docx no está instalado. Ejecuta: pip install python-docx"
            ) from e

        doc = Document(file_path)
        basename = os.path.basename(file_path)
        chunks: List[DocChunk] = []
        current_title = ""
        current_lines: List[str] = []
        chunk_index = 0

        def _flush() -> None:
            nonlocal chunk_index
            content = "\n".join(current_lines).strip()
            if content and current_title:
                chunks.append(DocChunk(
                    id=f"{basename}_{chunk_index}",
                    source_file=file_path,
                    title=current_title,
                    content=content,
                    chunk_type="user_story",
                ))
                chunk_index += 1

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            is_heading = para.style.name.startswith("Heading") and int(
                para.style.name.split()[-1]
            ) <= 2 if para.style.name.startswith("Heading") else False
            is_bold_keyword = (
                any(run.bold for run in para.runs if run.text.strip())
                and _STORY_KEYWORDS.search(text)
            )

            if is_heading or is_bold_keyword:
                _flush()
                current_title = text
                current_lines = []
            else:
                current_lines.append(text)

        _flush()

        # Si no se detectaron chunks con headings, tratar todo el documento como un único chunk
        if not chunks:
            full_text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
            if full_text:
                chunks.append(DocChunk(
                    id=f"{basename}_0",
                    source_file=file_path,
                    title=basename,
                    content=full_text,
                    chunk_type="user_story",
                ))

        return chunks


# ---------------------------------------------------------------------------
# ExcelIngester
# ---------------------------------------------------------------------------

class ExcelIngester:
    """
    Extrae chunks de un archivo Excel (.xlsx).

    Estrategia:
    1. Lee el archivo con pandas + python-calamine (ya instalados).
    2. Detecta automáticamente las columnas de ID, descripción, pasos y resultado esperado.
    3. Genera un DocChunk por cada fila, formateando el contenido para el LLM.
    """

    def ingest(self, file_path: str) -> List[DocChunk]:
        try:
            import pandas as pd  # type: ignore
        except ImportError as e:
            raise ImportError("pandas no está instalado.") from e

        basename = os.path.basename(file_path)

        # Leer con calamine si disponible, fallback a openpyxl
        try:
            df = pd.read_excel(file_path, engine="calamine")
        except Exception:
            try:
                df = pd.read_excel(file_path, engine="openpyxl")
            except Exception:
                df = pd.read_excel(file_path)

        if df.empty:
            return []

        col_map = _detect_columns(list(df.columns))
        chunks: List[DocChunk] = []

        for index, row in df.iterrows():
            row_id = str(row[col_map["id"]]).strip() if col_map["id"] else str(index + 1)
            description = str(row[col_map["description"]]).strip() if col_map["description"] else ""
            steps = str(row[col_map["steps"]]).strip() if col_map["steps"] else ""
            expected = str(row[col_map["expected"]]).strip() if col_map["expected"] else ""

            # Saltar filas sin contenido útil
            if not any([description, steps, expected]):
                continue
            # Saltar filas que son encabezados repetidos
            if description.lower() in ("nan", "none", "") and steps.lower() in ("nan", "none", ""):
                continue

            # Limpiar NaN de pandas
            description = description if description not in ("nan", "None") else ""
            steps = steps if steps not in ("nan", "None") else ""
            expected = expected if expected not in ("nan", "None") else ""

            content_parts: List[str] = []
            if description:
                content_parts.append(f"Descripción: {description}")
            if steps:
                content_parts.append(f"Pasos: {steps}")
            if expected:
                content_parts.append(f"Resultado esperado: {expected}")

            title = f"Caso {row_id}" + (f": {description[:60]}" if description else "")

            chunks.append(DocChunk(
                id=f"{basename}_{index}",
                source_file=file_path,
                title=title,
                content="\n".join(content_parts),
                chunk_type="test_matrix",
                row_data={
                    "id": row_id,
                    "description": description,
                    "steps": steps,
                    "expected": expected,
                },
            ))

        return chunks
