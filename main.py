import json
import re
import qrcode
import os
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
import time
import base64
from cv2 import imread
from pyzbar.pyzbar import decode

Config = None
WebDriver = None

def init():
    print("读取配置文件...")
    try:
        with open('Config.json', 'r') as cfgFile:
            try:
                global Config  
                Config = json.load(cfgFile)
                pattern = re.compile(r'(https?|ftp|file)://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]')
                if not bool(pattern.match(Config.get("target"))):
                    print("请使用合法url")
                    exit()
                if not Config["userinfo"]["name"] or not Config["userinfo"]["phone"]:
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
    global WebDriver
    WebDriver = webdriver.Chrome(options=chrome_options)

def login():
    while(not try_login()):
        pass

def try_login():
    WebDriver.get(Config["target"])
    WebDriver.find_element(By.CLASS_NAME, "nav-header-register").click()
    time.sleep(1)
    get_QR()

    input("扫码登录确认后，按enter继续...")
    time.sleep(1)
    try:
        WebDriver.find_element(By.CLASS_NAME, "profile-img")
    except NoSuchElementException as e:
        print(f"登录失败：\n{e.msg}\n")
        input("按enter重试...")
        return False
    else:
        print("登录成功")
        return True

def get_QR():
    try:
        base64str = WebDriver.find_element(By.XPATH, "//img[@alt='Scan me!']").get_attribute("src").split(",")[1]
    except NoSuchElementException as e:
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



if __name__ == '__main__':
    init()
    login()