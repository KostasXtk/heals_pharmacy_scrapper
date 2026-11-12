import requests
from bs4 import BeautifulSoup
import re
from dataclasses import dataclass
import json

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0"})
TIMEOUT = 15

@dataclass
class HealsPharmacyProduct:
    link : str
    title : str
    price : float # max 2 decimals
    barcode : str
    position : int
    retailer: str #Healspharmacy string class needed?
    cat_depth: int | None = None
    cat_url: str | None = None
    cat_name: str | None = None


def fetch(url, *, method="GET", **kwargs):
    try:
        resp = SESSION.request(method, url, timeout=TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp
    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return None

def get_max_pages(soup):
    max_page_number = soup.find_all("li", class_="page-item")
    if not max_page_number:
        return 1
    return int(max_page_number[-1].find("a").get("data-ci-pagination-page"))


def build_page_url(cat_link, page):
    return re.sub(r"/\d+\.htm$", f"/{page}.htm", cat_link)


def healspharmacy_category(cat_depth, cat_link):
    resp = fetch(cat_link)
    if resp is None:
        return []
    soup = BeautifulSoup(resp.text, "lxml")
    max_pages = get_max_pages(soup)

    if max_pages > 1:  # we need to make sure that Κολοστομία edge case is handled
        urls = [build_page_url(cat_link, page) for page in range(1, max_pages + 1)]
    else:
        urls = [cat_link]

    products = []
    seen_barcodes = set()

    for url in urls:
        if url == cat_link:
            page_soup = soup  # already fetched
        else:
            r = fetch(url)
            if r is None:
                continue
            page_soup = BeautifulSoup(r.text, "lxml")

        for script in page_soup.find_all("script", type="application/ld+json"):
            data = json.loads(script.get_text())
            if isinstance(data, dict) and data.get("@type") == "ItemList":
                for list_item in data["itemListElement"]:
                    item = list_item["item"]
                    barcode = item["sku"]
                    if barcode in seen_barcodes:
                        print("DUPLICATE:", barcode, item["name"]);
                        continue

                    product = HealsPharmacyProduct(
                        link=item["url"],
                        title=item["name"],
                        price=float(item["offers"]["lowPrice"]),
                        barcode=barcode,
                        position=list_item["position"],
                        retailer=item["brand"]["name"],
                    )
                    products.append(product)
                    seen_barcodes.add(barcode)

                    if len(seen_barcodes) >= 50:
                        for product in products:
                            print(product)
                        return products

    for product in products:
        print(product)

    return products

def healspharmacy_product(product_link):
    resp = fetch(product_link)
    if resp is None:
        return []
    soup = BeautifulSoup(resp.text, "lxml")
    images_urls = []
    for script in soup.find_all("script", type="application/ld+json"):
        data = json.loads(script.string)
        items = data if isinstance(data, list) else [data]
        for item in items:
            if item.get("@type") == "Product":
                img = item.get("image", [])
                images_urls = [img] if isinstance(img, str) else img

    # there are 2 desc parts splitted based on BARCODE keyword [0] equals the actual desc || [1] equals to the value of the BARCODE
    description_parts = soup.select_one("div#tab-1.col-12.tab-content.current").text.split('BARCODE')
    product_dict = {
        'title': re.sub(r'(?:\s*[-|]\s*Heals(?:\.gr)?)+$', '', soup.title.get_text(strip=True)),
        'description' : description_parts[0],
        'barcode' : description_parts[1].strip(),
        'sku-product_id': soup.find("adv-product-gallery")[":product-id"],
        'price' : soup.select_one("div.d-flex.w-100.justify-content-between.p-page-product-price span[itemprop='price']").text,
        'imageUrls' : images_urls
    }

    return product_dict
    







def main():

    # andras cat
    # healspharmacy_category(None, "https://www.heals.gr/%CE%B3%CE%B9%CE%B1-%CF%84%CE%BF%CE%BD-%CE%B1%CE%BD%CF%84%CF%81%CE%B1/1.htm")

    # kolostomia case
    # healspharmacy_category(None, "https://www.heals.gr/%CE%B3%CE%B7%CF%81%CE%B9%CE%B1%CF%84%CF%81%CE%B9%CE%BA%CE%B1-3%CE%B7-%CE%B7%CE%BB%CE%B9%CE%BA%CE%B9%CE%B1/%CF%83%CF%84%CE%BF%CE%BC%CE%B9%CE%B5%CF%83.htm")

    healspharmacy_product("https://www.heals.gr/vendors/cerave/cerave-moisturizing-cream-%CE%B5%CE%BD%CF%85%CE%B4%CE%B1%CF%84%CE%B9%CE%BA%CE%B7-%CE%BA%CF%81%CE%B5%CE%BC%CE%B1-454gr.htm")
    healspharmacy_product("https://www.heals.gr/vendors/la-roche-posay/la-roche-posay-effaclar-cleansing-foaming-gel-%CE%BA%CE%B1%CE%B8%CE%B1%CF%81%CE%B9%CF%83%CE%BC%CE%BF%CF%85-%CF%80%CF%81%CE%BF%CF%83%CF%89%CF%80%CE%BF%CF%85-%CE%B3%CE%B9%CE%B1-%CE%B4%CE%B5%CF%81%CE%BC%CE%B1-%CE%BC%CE%B5-%CF%84%CE%B1%CF%83%CE%B7-%CE%B1%CE%BA%CE%BC%CE%B7%CF%83-400ml.htm")





if __name__ == "__main__":
    main()