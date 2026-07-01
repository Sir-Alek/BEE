"""Page object demo — Sauce Demo login."""


class LoginPage:
    URL = "https://www.saucedemo.com/"
    USER_XPATH = "//input[@id='user-name']"
    PASSWORD_XPATH = "//input[@id='password']"
    SUBMIT_XPATH = "//input[@id='login-button']"
    INVENTORY_XPATH = "//div[contains(@class,'inventory_list')]"
