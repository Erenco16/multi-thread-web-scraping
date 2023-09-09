import time
import concurrent.futures
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import os
from dotenv import load_dotenv
import send_mail

load_dotenv()

login_url = "https://online.hafele.live/login?logout=true"

payload = {
    "username": os.getenv("hafele_online_username"),
    "password": os.getenv("hafele_online_password")
}

headers = {
    "Referer": "https://online.hafele.live/login?logout=true",
    "Origin": "https://online.hafele.live",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15"
}


def read_excel(file_path):
    excel_data = pd.read_excel(file_path)
    data = pd.DataFrame(excel_data, columns=["stockCode"])
    stock_code_list = list()
    for code in data.values:
        stock_code_list.append(str(code[0]))
    return stock_code_list


def extract_integer(string):
    integers = re.findall(r'\d+', string)
    integers = [int(i) for i in integers]
    merged_string = ''.join(map(str, integers))
    return merged_string


def extract_string(string):
    # Use regular expressions to find and capture non-integer parts of the string
    non_integer_parts = re.findall(r'\D+', string)

    # Remove any empty strings from the result
    non_integer_parts = [part.strip() for part in non_integer_parts if part.strip()]

    non_integer_parts = ''.join(map(str, non_integer_parts))

    if "." in non_integer_parts:
        non_integer_parts = non_integer_parts.replace(".", "")

    return non_integer_parts


def extract_stock_info_from_page(product_soup):
    content_panels = product_soup.find_all("div", class_="content panel")
    for panel in content_panels:
        if panel.find("legend"):
            if "Stok" in panel.find("legend").text:
                find_tds = panel.find_all("td")
                package_quantity = extract_integer(find_tds[0].text)
                package_type = extract_string(find_tds[0].text)
                stock_quantity = extract_integer(find_tds[1].text)
                stock_type = extract_string(find_tds[1].text)

                return [package_quantity, package_type, stock_quantity, stock_type]


def extract_price_info(product_soup):
    find_span = product_soup.find("span", class_="price price").text
    first_price = find_span.replace(".", "")
    sec_price = first_price.replace(",", ".")
    final_price = sec_price.replace("TRY", "")
    return final_price.strip()

def scrape_each_product(product_code):
    session = requests.session()

    login_response = session.post(
        login_url,
        headers=headers,
        data=payload
    )


    if login_response.status_code == 200:
        if "Kullancı Bilgileriniz Hatalıdır" not in login_response.text:
            count = 0
            content_url = f"https://online.hafele.live/product-p-{product_code}"
            content_response = session.get(content_url)

            if "Internal Server Error" not in content_response.text:
                content_soup = BeautifulSoup(content_response.text, "html.parser")
                product_stock_list = extract_stock_info_from_page(content_soup)
                product_price = extract_price_info(content_soup)
                row_list = [product_code, product_stock_list[0], product_stock_list[1], product_stock_list[2], product_stock_list[3], product_price]
                print(f"{product_code} done.")
                count = count + 1
            else:
                row_list = [product_code, "yok", "yok", "yok", "yok", "yok"]
                print(f"{product_code} does not exist on hafele online but done.")

            return row_list


if __name__ == "__main__":

    st = time.time()
    stock_codes = read_excel("excel-file-to-be-read.xlsx")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        data_to_be_extracted = executor.map(scrape_each_product, stock_codes)

    dataframe_extract = list(data_to_be_extracted)

    # creating the headers of the dataframe
    hd = ["stockCode", "paketIciMiktari", "paketIciTuru", "stockAmount", "stockType", "price"]
    
    # create the dataframe
    df = pd.DataFrame(dataframe_extract, columns=hd)
    
    # extract the dataframe
    df.to_excel("multi-threading-test.xlsx", sheet_name="Urunler")

    # send mail with the excel attachment to the relevant mail address
    send_mail.send_mail_with_excel

    et = time.time()

    print(f"Time past to scrape {len(dataframe_extract)} products is {round(((et-st)/60), 2)} minutes")
