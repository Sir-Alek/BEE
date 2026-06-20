"""Paso SQL para suites API ("JDBC" nativo en Python).

Permite preparar/validar datos contra una base de datos como parte de un flujo:
ejecutar una query, extraer valores a variables de sesión (correlación con BD)
y/o aplicar aserciones simples (número de filas, primer valor).

Diseño y seguridad:
- Los drivers nativos son OPCIONALES y se importan de forma perezosa. Solo
  ``sqlite`` está disponible siempre (stdlib). Para el resto se requiere instalar
  el driver correspondiente; si falta, el paso falla con un mensaje claro y NO
  rompe el resto de ELIA.
- Las credenciales NUNCA se guardan en el flujo: se leen desde variables de
  entorno cuyos NOMBRES se indican en la config (``user_env`` / ``password_env``).
- Las credenciales se redactan en cualquier representación devuelta.

Config (dict ``sql`` del nodo)::

    {
      "driver": "sqlite" | "postgres" | "mysql" | "sqlserver",
      "dsn": "ruta.db | DSN nativo",        # alternativa a host/port/db
      "host": "...", "port": 5432, "database": "...",
      "user_env": "ELIA_DB_USER",            # nombre de la variable de entorno
      "password_env": "ELIA_DB_PASSWORD",
      "query": "SELECT id FROM users WHERE email = :email",
      "params": {"email": "{{email}}"},      # parámetros (interpolados)
      "extract": [{"column": "id", "target_var": "user_id", "row": 0}],
      "assert": {"min_rows": 1, "max_rows": 100,
                 "value": {"column": "id", "row": 0, "equals": "{{user_id}}"}}
    }
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from core.api_automation.runtime.interpolation import interpolate_text

_SUPPORTED_DRIVERS = ("sqlite", "postgres", "mysql", "sqlserver")


def run_sql_step(
    config: Dict[str, Any],
    *,
    variables: Dict[str, str],
) -> Dict[str, Any]:
    """Ejecuta un paso SQL y devuelve un resultado JSON-serializable."""
    driver = str(config.get("driver") or "sqlite").lower()
    query = interpolate_text(str(config.get("query") or ""), variables)
    if not query.strip():
        return _fail("Query SQL vacía")
    if driver not in _SUPPORTED_DRIVERS:
        return _fail(f"Driver SQL no soportado: {driver!r}")

    params = _interpolate_params(config.get("params"), variables)

    try:
        rows, columns = _execute(driver, config, query, params, variables)
    except _SqlDriverMissing as exc:
        return _fail(str(exc))
    except _SqlCredentialMissing as exc:
        return _fail(str(exc))
    except Exception as exc:  # noqa: BLE001 — el detalle del error de BD es útil
        return _fail(f"Error SQL: {exc}")

    extract_results = _apply_extract(config.get("extract") or [], rows, columns, variables)
    assert_ok, assert_msgs = _apply_assert(config.get("assert") or {}, rows, columns, variables)

    return {
        "ok": assert_ok,
        "driver": driver,
        "row_count": len(rows),
        "columns": columns,
        # Limitamos las filas devueltas para no inflar el reporte.
        "rows_preview": [list(r) for r in rows[:20]],
        "extractors": extract_results,
        "assertions": assert_msgs,
        "query": query,
    }


# --------------------------------------------------------------------------- #
# Conexión / ejecución por driver (lazy import)
# --------------------------------------------------------------------------- #
class _SqlDriverMissing(RuntimeError):
    pass


class _SqlCredentialMissing(RuntimeError):
    pass


def _execute(
    driver: str,
    config: Dict[str, Any],
    query: str,
    params: Dict[str, Any],
    variables: Dict[str, str],
) -> Tuple[List[Tuple[Any, ...]], List[str]]:
    if driver == "sqlite":
        return _execute_sqlite(config, query, params, variables)
    if driver == "postgres":
        return _execute_postgres(config, query, params, variables)
    if driver == "mysql":
        return _execute_mysql(config, query, params, variables)
    if driver == "sqlserver":
        return _execute_sqlserver(config, query, params, variables)
    raise _SqlDriverMissing(f"Driver no soportado: {driver}")


def _execute_sqlite(config, query, params, variables):
    import sqlite3  # stdlib

    dsn = interpolate_text(str(config.get("dsn") or config.get("database") or ":memory:"), variables)
    conn = sqlite3.connect(dsn)
    try:
        cur = conn.cursor()
        # sqlite usa parámetros nombrados :name
        cur.execute(query, params or {})
        if cur.description:
            columns = [c[0] for c in cur.description]
            rows = cur.fetchall()
        else:
            columns, rows = [], []
        conn.commit()
        return rows, columns
    finally:
        conn.close()


def _execute_postgres(config, query, params, variables):
    try:
        import psycopg2  # type: ignore
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise _SqlDriverMissing(
            "Driver PostgreSQL no instalado. Ejecuta: pip install psycopg2-binary"
        ) from exc
    user = _resolve_secret(config.get("user_env"), variables, required=True, label="usuario")
    password = _resolve_secret(config.get("password_env"), variables, required=True, label="contraseña")
    conn = psycopg2.connect(
        host=config.get("host"),
        port=int(config.get("port") or 5432),
        dbname=config.get("database"),
        user=user,
        password=password,
    )
    try:
        cur = conn.cursor()
        cur.execute(query, params or {})
        columns = [c[0] for c in cur.description] if cur.description else []
        rows = cur.fetchall() if cur.description else []
        conn.commit()
        return rows, columns
    finally:
        conn.close()


def _execute_mysql(config, query, params, variables):
    try:
        import mysql.connector  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise _SqlDriverMissing(
            "Driver MySQL no instalado. Ejecuta: pip install mysql-connector-python"
        ) from exc
    user = _resolve_secret(config.get("user_env"), variables, required=True, label="usuario")
    password = _resolve_secret(config.get("password_env"), variables, required=True, label="contraseña")
    conn = mysql.connector.connect(
        host=config.get("host"),
        port=int(config.get("port") or 3306),
        database=config.get("database"),
        user=user,
        password=password,
    )
    try:
        cur = conn.cursor()
        cur.execute(query, params or {})
        columns = [c[0] for c in cur.description] if cur.description else []
        rows = cur.fetchall() if cur.description else []
        conn.commit()
        return rows, columns
    finally:
        conn.close()


def _execute_sqlserver(config, query, params, variables):
    try:
        import pyodbc  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise _SqlDriverMissing(
            "Driver SQL Server no instalado. Ejecuta: pip install pyodbc (requiere ODBC Driver)"
        ) from exc
    dsn = interpolate_text(str(config.get("dsn") or ""), variables)
    if not dsn:
        user = _resolve_secret(config.get("user_env"), variables, required=True, label="usuario")
        password = _resolve_secret(config.get("password_env"), variables, required=True, label="contraseña")
        driver_name = config.get("odbc_driver") or "ODBC Driver 17 for SQL Server"
        dsn = (
            f"DRIVER={{{driver_name}}};SERVER={config.get('host')},{config.get('port') or 1433};"
            f"DATABASE={config.get('database')};UID={user};PWD={password}"
        )
    conn = pyodbc.connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute(query, *([params] if params else []))
        columns = [c[0] for c in cur.description] if cur.description else []
        rows = [tuple(r) for r in cur.fetchall()] if cur.description else []
        conn.commit()
        return rows, columns
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Extracción y aserciones
# --------------------------------------------------------------------------- #
def _apply_extract(extract_specs, rows, columns, variables) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for spec in extract_specs:
        if not isinstance(spec, dict):
            continue
        target = str(spec.get("target_var") or "").strip()
        row_idx = int(spec.get("row") or 0)
        col = spec.get("column")
        ok, value = _cell(rows, columns, row_idx, col)
        if ok and target:
            variables[target] = str(value)
        out.append(
            {
                "target_var": target,
                "column": col,
                "row": row_idx,
                "passed": ok,
                "value": value if ok else None,
            }
        )
    return out


def _apply_assert(assert_spec, rows, columns, variables) -> Tuple[bool, List[Dict[str, Any]]]:
    if not assert_spec:
        return True, []
    msgs: List[Dict[str, Any]] = []
    ok_all = True

    if "min_rows" in assert_spec:
        passed = len(rows) >= int(assert_spec.get("min_rows") or 0)
        ok_all = ok_all and passed
        msgs.append({"kind": "min_rows", "expected": assert_spec.get("min_rows"), "passed": passed})
    if "max_rows" in assert_spec:
        passed = len(rows) <= int(assert_spec.get("max_rows") or 0)
        ok_all = ok_all and passed
        msgs.append({"kind": "max_rows", "expected": assert_spec.get("max_rows"), "passed": passed})

    value_spec = assert_spec.get("value")
    if isinstance(value_spec, dict):
        ok, value = _cell(rows, columns, int(value_spec.get("row") or 0), value_spec.get("column"))
        expected = interpolate_text(str(value_spec.get("equals") or ""), variables)
        passed = ok and str(value) == expected
        ok_all = ok_all and passed
        msgs.append(
            {
                "kind": "value_equals",
                "column": value_spec.get("column"),
                "expected": expected,
                "actual": value if ok else None,
                "passed": passed,
            }
        )

    return ok_all, msgs


def _cell(rows, columns, row_idx, col) -> Tuple[bool, Any]:
    if row_idx < 0 or row_idx >= len(rows):
        return False, None
    row = rows[row_idx]
    if isinstance(col, int):
        if 0 <= col < len(row):
            return True, row[col]
        return False, None
    if isinstance(col, str) and col in columns:
        return True, row[columns.index(col)]
    # Sin columna especificada: primera celda.
    if col in (None, "") and row:
        return True, row[0]
    return False, None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _interpolate_params(params: Optional[Dict[str, Any]], variables: Dict[str, str]) -> Dict[str, Any]:
    if not isinstance(params, dict):
        return {}
    return {k: interpolate_text(str(v), variables) for k, v in params.items()}


def _resolve_secret(
    var_name: Optional[str],
    variables: Dict[str, str],
    *,
    required: bool = False,
    label: str = "credencial",
) -> str:
    """Resuelve secretos: primero entorno API (variables de sesión), luego OS env."""
    if not var_name:
        if required:
            raise _SqlCredentialMissing(f"Falta nombre de variable para {label} SQL")
        return ""
    key = str(var_name).strip()
    if not key:
        if required:
            raise _SqlCredentialMissing(f"Nombre de variable {label} vacío")
        return ""
    if key in variables and str(variables[key]).strip():
        return str(variables[key])
    os_val = os.environ.get(key, "")
    if os_val.strip():
        return os_val
    if required:
        raise _SqlCredentialMissing(
            f"Falta {label} SQL: define la clave {key!r} en el entorno API activo "
            f"(p. ej. dev.json) o como variable de entorno del sistema ({key})."
        )
    return ""


def _env(var_name: Optional[str]) -> str:
    if not var_name:
        return ""
    return os.environ.get(str(var_name), "")


def sql_preflight(config: Dict[str, Any], *, variables: Dict[str, str]) -> Dict[str, Any]:
    """Ejecuta SELECT 1 (o equivalente) para validar conexión sin modificar datos."""
    probe = dict(config)
    driver = str(probe.get("driver") or "sqlite").lower()
    if driver == "sqlite":
        probe["query"] = "SELECT 1 AS ok"
    else:
        probe["query"] = "SELECT 1 AS ok"
    probe.pop("extract", None)
    probe.pop("assert", None)
    return run_sql_step(probe, variables=variables)


def _fail(message: str) -> Dict[str, Any]:
    return {"ok": False, "row_count": 0, "columns": [], "rows_preview": [], "error": message}
