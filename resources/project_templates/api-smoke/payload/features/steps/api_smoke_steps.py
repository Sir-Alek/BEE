from behave import given, then, when


@given("el entorno API esta configurado")
def step_api_env(context):
    assert getattr(context, "http", None) is not None, "Cliente HTTP no inicializado (environment.py)"


@when('realizo GET a "{url}"')
def step_get(context, url):
    interpolated = url.replace("{{base_url}}", "https://jsonplaceholder.typicode.com")
    context.last_response = context.http.get(interpolated)
    context.last_url = interpolated

@then("la respuesta HTTP es {status:d}")
def step_status(context, status):
    assert context.last_response is not None, "Sin respuesta HTTP"
    assert context.last_response.status_code == status, (
        f"Esperado {status}, recibido {context.last_response.status_code}"
    )
