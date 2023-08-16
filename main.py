import json
import inquirer
import re
import qrcode
import os
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver
import base64
from cv2 import imread
from pyzbar.pyzbar import decode

def init():
    print("读取配置文件...")
    try:
        with open('Config.json', 'r', encoding='utf-8') as cfgFile:
            try:
                global config  
                config = json.load(cfgFile)
                pattern = re.compile(r'(https?|ftp|file)://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]')
                if not bool(pattern.match(config.get("target"))):
                    print("请使用合法url")
                    exit()
                if not config["userinfo"]["name"] or not config["userinfo"]["phone"]:
                    print("姓名或手机号不能为空")
                    exit()
            except json.JSONDecodeError as e:
                print(f"json解析错误: {e.msg}")
                exit()
    except IOError as e:
        print(f"配置文件读取错误: {e}")
        exit()

    print("配置文件读取成功")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    global web_driver
    web_driver = webdriver.Chrome(options=chrome_options)

def login():
    while(not try_login()):
        pass

def try_login():
    web_driver.get(config["target"])
    web_driver.find_element(By.CLASS_NAME, "nav-header-register").click()
    get_QR()
    print('请在1分钟内扫码确认')
    try:
        wait = WebDriverWait(web_driver, 60) 
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "profile-img")))
    except TimeoutException as e:
        print(f"登录失败：\n{e.msg}\n")
        input("按enter重试...")
        return False
    else:
        print("登录成功")
        return True

def get_QR():
    try:
        wait = WebDriverWait(web_driver, 10) 
        s = wait.until(EC.presence_of_element_located((By.XPATH, "//img[@alt='Scan me!']")))
        base64str = s.get_attribute("src").split(",")[1]
    except TimeoutException as e:
        print(f"获取登录二维码失败:{e.msg}")
        exit()
    
    imgData = base64.b64decode(base64str)
    with open('qr.jpg', 'wb') as file:
        file.write(imgData)
    qrImg = imread('qr.jpg')
    qrUrl = decode(qrImg)[0].data.decode("utf-8")
    os.remove('qr.jpg')
    qr = qrcode.QRCode()
    qr.add_data(qrUrl)
    qr.print_ascii(invert=True)

def select():
    select_box = web_driver.find_element(By.CLASS_NAME, "login-show-wrapper")
    l1 = select_box.find_elements(By.XPATH, "./ul[1]/li[2]/div")
    l1 = [div for div in l1 if 'unable' not in div.get_attribute('class')]
    sessions = [x.text for x in l1];
    options = [inquirer.List('choice',
                            message="选择场次",
                            choices=sessions)]
    answers = inquirer.prompt(options)['choice']
    index = [index for index, value in enumerate(l1) if value.text == answers][0]
    l1[index].click()
    l2 = select_box.find_elements(By.XPATH, "./ul[2]/li[2]/div")
    l2 = [div for div in l2 if 'unable' not in div.get_attribute('class')]
    prices = [x.text for x in l2];
    options = [inquirer.List('choice',
                            message="选择价格",
                            choices=prices)]
    answers = inquirer.prompt(options)['choice']
    index = [index for index, value in enumerate(l2) if value.text == answers][0]
    l2[index].click()
    num = input('输入购票数量：')
    try:
        num = int(num)
        if (num <= 0):
            print('请输入大于零的数')
            exit()
    except ValueError:
        print("无效输入，请输入一个整数。")
        exit()
    plus = select_box.find_element(By.XPATH, ".//div[contains(@class, 'ticket-count')]/div[contains(@class, 'count-plus')]")
    while num > 1:
        plus.click()
        num-=1
    buy = select_box.find_element(By.XPATH, ".//div[contains(@class, 'product-buy-wrapper')]/div[1]/div[1]")
    buy.click()
    wait = WebDriverWait(web_driver, 10) 
    wait.until(EC.presence_of_element_located((By.XPATH, "//section[contains(@class, 'contact-block')]")))
    iss = web_driver.find_elements(By.XPATH, "//section[contains(@class, 'contact-block')]//input")
    iss[0].clear()
    iss[0].send_keys(config['userinfo']['name'])
    iss[1].clear()
    iss[1].send_keys(config['userinfo']['phone'])
    c = web_driver.find_element(By.XPATH, "//div[contains(@class, 'service-term')]/span[1]")
    if 'checked' not in c.get_attribute('class'):
        c.click()
    c = web_driver.find_element(By.XPATH, "//div[contains(@class, 'confirm-paybtn')]")
    c.click()
    print('订单已生成')


if __name__ == '__main__':
    init()
    login()
    select()
