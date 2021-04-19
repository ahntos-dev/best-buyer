"""AHNTOS Purchase Bot"""

import requests
import smtplib
import sys
import ssl
import time
from playsound import playsound
import webbrowser
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
import logging

from path import resource_path


# Searches BestBuy for item corresponding to SKU
skuId = input('Enter SKU of item to search for: ')


# arguments for selenium to help speed up chromedriver

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("no-sandbox")
chrome_options.add_argument('--lang=en_US')
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument('window-size=800,600')
chrome_options.add_argument('--blink-settings=imagesEnabled=false')
chrome_options.add_experimental_option("useAutomationExtension", False)
prefs = {"profile.managed_default_content_settings.images": 2}
chrome_options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(resource_path('chromedriver_dir/chromedriver'), options=chrome_options)


# erases a test logger and makes a new one at INFO level

# os.remove(resource_path('test.log'))
FORMAT = f'[%(asctime)-15s][{skuId}] %(message)s'
root = logging.getLogger()
root.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(FORMAT)
handler.setFormatter(formatter)
root.addHandler(handler)


# starts new requests session

s = requests.Session()


# loads config.json file and parses data from it

f = open(resource_path('cfg/config.json'))
data = json.load(f)


# Personal data

smtp_server = data["mail"]["smtp"]
port = data["mail"]["port"]
sender_email = data["mail"]["sender"]
receiver_email = data["mail"]["receiver"]
user = data["best-buy"]["username"]
password = data["best-buy"]["password"]


# Important navigation URLs
# BEST_BUY_ADD_TO_CART_API_URL = "https://www.bestbuy.com/cart/api/v1/addToCart"
# (commented out because link won't work for me)
BEST_BUY_PDP_URL = 'https://api.bestbuy.com/click/5592e2b895800000/{sku}/pdp'
BEST_BUY_ADD_CART = 'https://api.bestbuy.com/click/5592e2b895800000/{sku}/cart'
ITEM_PAGE_URL = "https://www.bestbuy.com/api/tcfb/model.json?paths=%5B%5B%22shop%22%2C%22scds%22%2C%22v2%22%2C%22pag" \
                "e%22%2C%22tenants%22%2C%22bbypres%22%2C%22pages%22%2C%22globalnavigationv5sv%22%2C%22header%22%5D%2C%" \
                "5B%22shop%22%2C%22buttonstate%22%2C%22v5%22%2C%22item%22%2C%22skus%22%2C{sku}%2C%22conditions%22%2C%22" \
                "NONE%22%2C%22destinationZipCode%22%2C%22%2520%22%2C%22storeId%22%2C%22%2520%22%2C%22context%22%2C%22" \
                "cyp%22%2C%22addAll%22%2C%22false%22%5D%5D&method=get"


def main():
    login()
    prod = print_prod_url()
    add_to_cart(prod)
    playsound('Super Mario Bros. - Mushroom Sound Effect.mp3')
    driver.quit()


def login():
    """Logs into BestBuy.com"""
    driver.get("https://www.bestbuy.com/identity/global/signin")

    root.info("Logging into BestBuy...")
    driver.find_element_by_id("fld-e").send_keys(user)
    driver.find_element_by_id("fld-p1").send_keys(password)
    driver.find_element_by_class_name("btn.btn-secondary.btn-lg.btn-block").click()
    # WebDriverWait(driver, 10).until(lambda x: "Official Online Store" in driver.title)
    time.sleep(.5)
    root.info("Logged in successfully!")


DEFAULT_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,"
              "*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/85.0.4183.102 "
                  "Safari/537.36",
    "origin": "https://www.bestbuy.com",
}


def print_prod_url():
    response = s.get(BEST_BUY_PDP_URL.format(sku=skuId), headers=DEFAULT_HEADERS)
    product_url = response.url
    # print(f"PDP Request: {response.status_code}")
    root.info(f"Product URL: {product_url}")
    # print(f"Product URL: {product_url}")
    return product_url


def push_notif(sub, ship, tax, price):
    """This function sends an email to the user as a notification"""

    # String for subject of email
    subject: str = "Notice of Availability"

    # Create a secure SSL context
    context = ssl.create_default_context()
    message = f"""\
    The AHNTOS Best Buy Purchase Bot executed without a hitch!



    Item Purchased!

    Item Subtotal:       {sub}
    Shipping:            {ship}
    Estimated Sales Tax: {tax}

    Total:               {price}



    This message was sent from the AHNTOS Bot Buyer."""
    email = "Subject: {}\n\n{}".format(subject, message)

    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, email)
        root.info(f"Email Notification sent to {receiver_email}")
    server.close()


def in_stock():
    """Checks if item is in stock and can be added to cart or pre-ordered"""

    url = ITEM_PAGE_URL.format(sku=skuId)

    response = s.get(url, headers=DEFAULT_HEADERS)
    if 'ADD_TO_CART' in response.text or 'PRE_ORDER' in response.text:
        return True
    elif 'SOLD_OUT' in response.text:
        return False


def check_stock() -> str:
    """Adds item to cart if in stock, continues to check if not"""

    body = {"items": [{"skuId": skuId}]}
    headers = {
        "accept": "application/json",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "content-length": "31",
        "content-type": "application/json; charset=UTF-8",
        "origin": "https://www.bestbuy.com",
        "referer": BEST_BUY_PDP_URL.format(sku=skuId),
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/"
                      "81.0.4044.92 Safari/537.36"
    }

    while not in_stock():
        logging.warning("Item out of stock. Checking again...")
        time.sleep(1)  # Waits one second before checking again
    root.info("Item in stock!")
    webbrowser.open(BEST_BUY_ADD_CART.format(sku=skuId))

    return BEST_BUY_ADD_CART.format(sku=skuId)


def add_to_cart(product_url):
    """Adds item to the cart"""

    # This commented code was supposed to work, but 'https://www.bestbuy.com/cart/api/v1/addToCart'
    # never gives me any results/doesn't work
    '''
    body = {"items": [{"skuId": skuId}]}
    headers = {
        "Accept": "application/json",
        "authority": "www.bestbuy.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) 
        Chrome/85.0.4183.102 Safari/537.36",
        "Content-Type": "application/json; charset=UTF-8",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "origin": "https://www.bestbuy.com",
        "referer": product_url,
        "Content-Length": str(len(json.dumps(body))),
    }
    r = s.post('https://www.bestbuy.com/cart/api/v1/addToCart', data=body, headers=headers, timeout=10, verify=True)
    root.info(r.status_code)
    root.info(r.json)
    # driver.get(check_stock())
    '''

    check_stock()
    start_time = time.time()

    root.info("Added item to cart!")

    end = checkout()
    root.info(f"--- Bot took {round(end - start_time, 2)}s seconds to purchase ---")


'''
response = s.put(
    "https://www.bestbuy.com/cart/item/{item_id}/fulfillment".format(
        item_id=item_id
    ),
    headers=DEFAULT_HEADERS,
    json=body,
)
'''


def checkout():
    root.info("Heading to checkout...")
    time.sleep(.35)
    driver.get("https://www.bestbuy.com/checkout/c/r/fast-track")

    # requests won't check out with link below, so used selenium instead
    '''
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                  "image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/85.0.4183.102 "
                      "Safari/537.36"
    }
    r = s.get("https://www.bestbuy.com/checkout/r/fufillment", headers=headers)
    print(r.content)
    '''

    check_shipping()

    # Code for actually purchasing. Should not be uncommented unless you are sure you want to purchase.

    purchase_btn = "btn.btn-lg.btn-block.btn-primary.button__fast-track"
    WebDriverWait(driver, 10).until(ec.element_to_be_clickable((By.CLASS_NAME, purchase_btn)))

    root.info("Purchasing item... : %s" % time.ctime())
    driver.find_element_by_class_name(purchase_btn).click()
    root.info("Item Purchased! : %s" % time.ctime())

    end_time = time.time()
    root.info("Bot complete!")

    # Gets info for email notification
    WebDriverWait(driver, 10).until(ec.visibility_of_element_located((By.CLASS_NAME, "order-summary-card__total-line")))
    prices = driver.find_elements_by_class_name("order-summary-card__total-line")
    sub = prices[0].text.replace("Item Subtotal\n", "")
    ship = prices[1].text.replace("Shipping\n", "").replace("Store Pickup\n", "")
    tax = prices[2].text.replace("Estimated Sales Tax\n", "")
    total = driver.find_element_by_class_name("order-summary__total")
    price = total.find_element_by_class_name("order-summary__price").text

    push_notif(sub, ship, tax, price)

    return end_time


def check_shipping():
    """Checks if shipping is selected"""

    WebDriverWait(driver, 10).until(ec.title_contains('Checkout'))
    shipping = driver.find_element_by_xpath('//*[@id="checkoutApp"]/div[2]/div[1]/div[1]/main/div[2]/div[2]/form/'
                                            'section/div/div[1]/div/div/section/div[2]/div[2]/div[2]/div/div/a')

    # This code also does not work, and the only way to retrieve the item id is from checkout page, which
    # also does not work
    """
    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "content-type": "application/json",
        "origin": "https://www.bestbuy.com",
        "referer": "https://www.bestbuy.com/cart",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_1) AppleWebKit/537.36 (KHTML, like Gecko) 
        Chrome/81.0.4044.92 Safari/537.36",
        "x-user-interface": "DotCom-Optimized"
    }
    body = {'selected': "SHIPPING"}

    r = s.put('https://www.bestbuy.com/cart/item/{item_id}/fulfillment'.format(item_id=item_id), 
    headers=headers, json=body)
    print(r.json())
    """

    if shipping.text == 'Switch to Shipping':
        logging.warning("Switching to shipping...")
        shipping.click()
    else:
        pass

    enter_cvv()


def enter_cvv():
    """Inputs the users CVV"""

    try:
        WebDriverWait(driver, .5).until(ec.visibility_of_element_located((By.ID, "credit-card-cvv")))
        driver.find_element_by_id("credit-card-cvv").send_keys(data["best-buy"]["cvv"])
        root.info("CVV entered successfully!")
    except:
        pass
