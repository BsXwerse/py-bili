import json
import re
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
import time
import base64
from cv2 import imread
from pyzbar.pyzbar import decode

Config = None
WebDriver = None

def Init():
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
                print(f"json解析错误: {e}")
                exit()
    except IOError as e:
        print(f"配置文件读取错误: {e}")
        exit()

def Login():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument('--ignore-certificate-errors')

    global WebDriver
    WebDriver = webdriver.Chrome(options=chrome_options)
    WebDriver.get(Config["target"])

    WebDriver.find_element(By.CLASS_NAME, "nav-header-register").click()
    
    time.sleep(1)
    base64str = WebDriver.find_element(By.XPATH, "//img[@alt='Scan me!']").get_attribute("src").split(",")[1]
    imgData = base64.b64decode(base64str)
    with open('qr.jpg', 'wb') as file:
        file.write(imgData)
    qrImg = imread('qr.jpg')
    qrUrl = decode(qrImg)[0].data.decode("utf-8")
    os.remove('qr.jpg')
    print(qrUrl)


if __name__ == '__main__':
    Init()
    Login()