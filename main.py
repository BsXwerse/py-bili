import json
from datetime import datetime
import inquirer
import re
import time
import qrcode
import os
import concurrent.futures
import threading
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
    global chrome_options
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
        global cookies
        cookies = web_driver.get_cookies()
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
    web_driver.get(config['target'])
    for cookie in cookies:
        web_driver.add_cookie(cookie)
    web_driver.refresh()

    wait = WebDriverWait(web_driver, 10) 
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "screens")))
    select_box = web_driver.find_element(By.CLASS_NAME, "login-show-wrapper")
    l1 = select_box.find_elements(By.XPATH, "./ul[1]/li[2]/div")
    l1_show = [div for div in l1 if 'unable' not in div.get_attribute('class')]
    sessions = [x.text for x in l1_show]
    options = [inquirer.List('choice',
                            message="选择场次",
                            choices=sessions)]
    answers = inquirer.prompt(options)['choice']
    global choose_session_index
    choose_session_index = [index for index, value in enumerate(l1) if value.text == answers][0]
    index = [index for index, value in enumerate(l1_show) if value.text == answers][0]
    l1[index].click()

    l2 = select_box.find_elements(By.XPATH, "./ul[2]/li[2]/div")
    prices = [x.text for x in l2]
    options = [inquirer.List('choice',
                            message="选择价格",
                            choices=prices)]
    answers = inquirer.prompt(options)['choice']
    global choose_price_index
    choose_price_index = [index for index, value in enumerate(l2) if value.text == answers][0]

    global buy_num
    buy_num = input('输入购票数量：')
    try:
        buy_num = int(buy_num)
        if (buy_num <= 0):
            print('请输入大于零的数')
            exit()
    except ValueError:
        print("无效输入，请输入一个整数。")
        exit()

    def check_date_format(date_string, expected_format):
        try:
            global begin_time
            begin_time = datetime.strptime(date_string, expected_format)
            return True
        except ValueError:
            return False
    
    while True:
        user_input = input("请输入抢票时间（格式为YYYY-MM-DD HH:MM:SS）：")
        
        if check_date_format(user_input, "%Y-%m-%d %H:%M:%S"):
            break
        else:
            print("输入的日期时间格式不正确，请重新输入。")



def check_order():
    time.sleep(2)
    web_driver.get('https://show.bilibili.com/orderlist')
    try:
        wait = WebDriverWait(web_driver, 10)
        item = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'order-item')][1]")))
        id = item.find_element(By.XPATH, ".//div[contains(@class, 'order-header-id')]").text
    except TimeoutException:
        id = ''

    wait_begin()

    while True:
        web_driver.refresh()
        wait = WebDriverWait(web_driver, 5)
        try:
            item = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'order-item')][1]")))
            if (id == ''):
                print('订单已生成')
                os._exit(0)
            new_id = item.find_element(By.XPATH, ".//div[contains(@class, 'order-header-id')]").text
            if (new_id == id):
                print('wait...')
                continue
            print('订单已生成')
            os._exit(0)
        except TimeoutException:
            print('wait...')

def wait_begin():
    print('等待抢票...')
    gap = 0.05
    cur = 0
    btime = begin_time.strftime("%Y-%m-%d %H:%M:%S")
    while True:
        if (datetime.now() >= begin_time):
            with condition:
                condition.notify_all()
            print('\n')
            break
        if (cur >= 1):
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print('\r' + now + ' -------> ' + btime, end='')
            cur = 0
        time.sleep(gap)
        cur += gap

condition = threading.Condition()

def worker(thread_id):
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(config['target'])
    for cookie in cookies:
        driver.add_cookie(cookie)
    driver.refresh()

    with condition:
        condition.wait()
    print(f'线程{thread_id}开始工作')

    while True:
        driver.get(config['target'])
        try:
            wait = WebDriverWait(driver, 10) 
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "screens")))
            select_box = driver.find_element(By.CLASS_NAME, "login-show-wrapper")
            l1 = select_box.find_elements(By.XPATH, "./ul[1]/li[2]/div")
            l1[choose_session_index].click()
            l2 = select_box.find_elements(By.XPATH, "./ul[2]/li[2]/div")
            l2[choose_price_index].click()
            plus = select_box.find_element(By.XPATH, ".//div[contains(@class, 'ticket-count')]/div[contains(@class, 'count-plus')]")
            num = buy_num
            while num > 1:
                plus.click()
                num-=1
            buy = select_box.find_element(By.XPATH, ".//div[contains(@class, 'product-buy-wrapper')]/div[1]/div[1]")
            buy.click()
            wait = WebDriverWait(driver, 10) 
            wait.until(EC.presence_of_element_located((By.XPATH, "//section[contains(@class, 'contact-block')]")))
            iss = driver.find_elements(By.XPATH, "//section[contains(@class, 'contact-block')]//input")
            iss[0].clear()
            iss[0].send_keys(config['userinfo']['name'])
            iss[1].clear()
            iss[1].send_keys(config['userinfo']['phone'])
            c = driver.find_element(By.XPATH, "//div[contains(@class, 'service-term')]/span[1]")
            if 'checked' not in c.get_attribute('class'):
                c.click()
            c = driver.find_element(By.XPATH, "//div[contains(@class, 'confirm-paybtn')]")
            c.click()
        except Exception:
            continue


def executeWorker():
    thread_num = config['threadNum']
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=thread_num)
    for i in range(thread_num):
        pool.submit(worker, i)

if __name__ == '__main__':
    init()
    login()
    select()
    executeWorker()
    check_order()

