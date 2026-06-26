# Guía de scripts API (JavaScript tipo Postman)

ELIA ejecuta un **subconjunto** de la API de scripts de Postman en escenarios API (`pre_request_script` / `post_request_script`).

## Objetos disponibles

| Objeto | Uso |
|--------|-----|
| `pm.environment` | Variables del entorno activo (`get`, `set`) |
| `pm.variables` | Alias de entorno en pre-request |
| `pm.request.headers` | Cabeceras de la petición (`add({key, value})`) |
| `pm.response` | Respuesta HTTP (post-request): `code`, `json()`, `text()` |
| `pm.test(nombre, fn)` | Aserciones en post-request |

## Ejemplos

### Pre-request: token dinámico

```javascript
const token = pm.environment.get("token");
pm.request.headers.add({ key: "Authorization", value: "Bearer " + token });
```

### Post-request: extraer ID y validar status

```javascript
const data = pm.response.json();
pm.environment.set("order_id", data.id);
pm.test("HTTP 200", function () {
  pm.response.to.have.status(200);
});
```

## Limitaciones

- No hay `pm.sendRequest`, colecciones anidadas ni `require`.
- Las variables persisten en el entorno de la ejecución actual (suite o petición única).
- En **carga Locust**, los scripts de escenario no se re-ejecutan por usuario; use extractores y variables de entorno/CSV.

## Buenas prácticas

1. Mantenga scripts cortos y deterministas.
2. Prefiera extractores declarativos para correlación en suites.
3. Para carga con datos externos, use CSV en la pestaña **Pruebas de carga** (perfil *Volumen*).

## gRPC y carga distribuida (ELIA Architect)

- **gRPC**: nodos en flujos con reflexión del servidor (`grpcio`, `grpcio-reflection`, `protobuf`). Use «Validar reflexión» antes de ejecutar la suite.
- **Master/worker**: lance master en la máquina coordinadora y workers en generadores con el mismo proyecto API. Puerto por defecto `5557`. No combine `--processes` con modo red.
