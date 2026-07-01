Feature: Smoke API demo
  Validación HTTP mínima contra JSONPlaceholder (requiere entorno dev).

  Scenario: Consultar post 1
    Given el entorno API esta configurado
    When realizo GET a "{{base_url}}/posts/1"
    Then la respuesta HTTP es 200
