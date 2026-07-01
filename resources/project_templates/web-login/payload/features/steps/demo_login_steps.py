from behave import given, then, when

from pages.login_page import LoginPage
from utils.button_functions import ui_interact, ui_navigate


@given("el usuario abre la pagina de login demo")
def step_open_login(context):
    ui_navigate(
        context.driver,
        LoginPage.URL,
        "Login_Demo",
        context.generate_evidence,
        "01",
    )


@when('inicia sesion con usuario "{username}" y contraseña "{password}"')
def step_login(context, username, password):
    ui_interact(
        context.driver,
        LoginPage.USER_XPATH,
        "insertTxt",
        "Usuario",
        username,
        usar_create_screenshot=context.generate_evidence,
        screenshot_step="02",
    )
    ui_interact(
        context.driver,
        LoginPage.PASSWORD_XPATH,
        "insertTxt",
        "Password",
        password,
        usar_create_screenshot=context.generate_evidence,
        screenshot_step="03",
    )
    ui_interact(
        context.driver,
        LoginPage.SUBMIT_XPATH,
        "click",
        "Login",
        usar_create_screenshot=context.generate_evidence,
        screenshot_step="04",
    )


@then("ve el catalogo de productos")
def step_inventory_visible(context):
    ui_interact(
        context.driver,
        LoginPage.INVENTORY_XPATH,
        "highlight",
        "Catalogo_Productos",
        usar_create_screenshot=context.generate_evidence,
        screenshot_step="05",
    )
