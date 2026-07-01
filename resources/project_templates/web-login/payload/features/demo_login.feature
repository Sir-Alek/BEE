Feature: Login demo Sauce Demo
  Escenario de ejemplo incluido en la plantilla ELIA para validar login web.

  Scenario: Login exitoso con usuario estandar
    Given el usuario abre la pagina de login demo
    When inicia sesion con usuario "standard_user" y contraseña "secret_sauce"
    Then ve el catalogo de productos
