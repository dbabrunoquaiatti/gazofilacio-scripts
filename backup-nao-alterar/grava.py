from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# ================= CONFIG =================
URL = "https://docs.google.com/forms/d/e/1FAIpQLSdrmloMUmOhCU2RgmUF5_K_8RE86JEeLwT7FeU6U9X2fqvtHw/viewform"
# ==========================================

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 20)

driver.get(URL)

time.sleep(3)

# ==========================================
# ABRIR O CAMPO "Direcionado para"
# ==========================================
campo_direcionado = wait.until(
    EC.element_to_be_clickable((
        By.XPATH,
        "//label[contains(., 'Direcionado para')]/following::div[1]"
    ))
)

driver.execute_script("arguments[0].scrollIntoView({block:'center'});", campo_direcionado)
time.sleep(1)
campo_direcionado.click()

time.sleep(2)

# ==========================================
# CLICAR NA OPÇÃO "Dízimo"
# ==========================================
opcao_dizimo = wait.until(
    EC.element_to_be_clickable((
        By.XPATH,
        "//*[normalize-space(text())='Dízimo']"
    ))
)

driver.execute_script("arguments[0].scrollIntoView({block:'center'});", opcao_dizimo)
time.sleep(1)

# clique forçado (resolve 99% dos casos)
driver.execute_script("arguments[0].click();", opcao_dizimo)

time.sleep(2)

print("✅ Dízimo selecionado com sucesso")

# ==========================================
# DEBUG VISUAL (opcional)
# ==========================================
time.sleep(5)

# driver.quit()
