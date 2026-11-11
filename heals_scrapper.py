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

                    if len(seen_barcodes) >= 850:
                        for product in products:
                            print(product)
                        return products

    for product in products:
        print(product)

    return products




    # if max_pages>1:  # we need to make sure that Κολοστομία edge case is handled
    #     for page in range(1, max_pages + 1):
    #         url = build_page_url(cat_link, page)
    #         print(url)


    # url = cat_link # this is EDGE CASE REMOVE THIS

def main():

    # andras cat
    # healspharmacy_category(None, "https://www.heals.gr/%CE%B3%CE%B9%CE%B1-%CF%84%CE%BF%CE%BD-%CE%B1%CE%BD%CF%84%CF%81%CE%B1/1.htm")

    # kolostomia case
    healspharmacy_category(None, "https://www.heals.gr/%CE%B3%CE%B7%CF%81%CE%B9%CE%B1%CF%84%CF%81%CE%B9%CE%BA%CE%B1-3%CE%B7-%CE%B7%CE%BB%CE%B9%CE%BA%CE%B9%CE%B1/%CF%83%CF%84%CE%BF%CE%BC%CE%B9%CE%B5%CF%83.htm")


if __name__ == "__main__":
    main()