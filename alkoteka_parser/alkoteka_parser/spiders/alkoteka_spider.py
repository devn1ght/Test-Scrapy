import scrapy
import json
from datetime import datetime

class AlkotekaApiSpider(scrapy.Spider):
    name = "alkoteka"
    allowed_domains = ["alkoteka.com"]
    start_urls = [
        "https://alkoteka.com/catalog/krepkiy-alkogol",
        "https://alkoteka.com/catalog/vino",
        "https://alkoteka.com/catalog/slaboalkogolnye-napitki-2"
    ]

    CITY_UUID = "4a70f9e0-46ae-11e7-83ff-00155d026416" # Краснодар

    categories = []
    for category in start_urls:
        categories.append(category[29:])

    def start_requests(self):
        for category in self.categories:
            url = f"https://alkoteka.com/web-api/v1/product?city_uuid=4a70f9e0-46ae-11e7-83ff-00155d026416&page=1&per_page=100&root_category_slug={category}"
            yield scrapy.Request(url, callback=self.parse, meta={"category": category})

    def parse(self, response):
        data = json.loads(response.text)

        for item in data.get("results", []):
            current_price = float(item.get("price", 0))
            original_price = float(item.get("prev_price", current_price))
            discount_percentage = round((1 - current_price / original_price) * 100) if original_price > current_price else None

            category_hierarchy = []
            category = item.get("category")
            while category:
                category_hierarchy.insert(0, category["name"])
                category = category.get("parent")


            metadata = {}

            for label in item.get("filter_labels", []):
                key = label["title"]
                value = None

                if "values" in label and "min" in label["values"]:
                    value = str(label["values"]["min"])

                    if "Л" in key or any(char.isdigit() for char in key):
                        metadata["volume"] = f"{value} Л" if "Л" not in value else value
                    else:
                        metadata[key] = value

                elif "value" in label:
                    metadata[label["value"]] = key
            yield {
                "timestamp": int(datetime.now().timestamp()),
                "RPC": item.get("uuid", ""),
                "url": response.urljoin(item.get("product_url", "")),
                "title": item.get("name"),
                "marketing_tags": [label["title"] for label in item.get("action_labels", [])],
                "brand": item.get("subname", ""),
                "section": category_hierarchy,
                "price_data": {
                    "current": current_price,
                    "original": original_price,
                    "sale_tag": f"Скидка {discount_percentage}%" if discount_percentage else "",
                },
                "stock": {
                    "in_stock": item.get("available", False),
                    "count": item.get("quantity_total", 0),
                },
                "assets": {
                    "main_image": item.get("image_url", ""),
                    "set_images": [item.get("image_url", "")],
                    "view360": [],
                    "video": [],
                },
                "metadata": metadata,
                "variants": 0,
            }
