import json
import random
import uuid
from datetime import datetime, timezone

categories = ["Dresses", "Tops", "Trousers", "Jackets", "Shoes", "Accessories"]
brands = ["Zara", "H&M", "Mango", "Uniqlo", "Marks & Spencer"]
colors = ["red", "blue", "black", "white", "green", "navy", "grey", "pink"]
occasions = ["casual", "formal", "wedding", "office", "party", "beach"]
materials = ["cotton", "linen", "silk", "wool", "polyester"]

def generate_product():
    category  = random.choice(categories)
    color     = random.choice(colors)
    occasion  = random.choice(occasions)
    material  = random.choice(materials)
    brand     = random.choice(brands)
    price     = round(random.uniform(499, 8999), 2)
    inventory = random.choice([0, 0, 5, 12, 24, 48, 100])

    title = f"{color.capitalize()} {material} {category[:-1]} for {occasion}"
    description = (
        f"A stunning {color} {material} {category[:-1].lower()} "
        f"perfect for {occasion} occasions. This {brand} piece features "
        f"premium {material} fabric with modern styling. "
        f"Ideal for {occasion} events and everyday wear."
    )
    now = datetime.now(timezone.utc).isoformat()
    return {
        "sku_id":          str(uuid.uuid4())[:8].upper(),
        "title":           title,
        "description":     description,
        "category":        category,
        "price":           price,
        "inventory_count": inventory,
        "image_url":       f"https://images.example.com/{uuid.uuid4()}.jpg",
        "brand":           brand,
        "created_at":      now,
        "updated_at":      now
    }

products = [generate_product() for _ in range(500)]

with open("catalog.jsonl", "w") as f:
    for p in products:
        f.write(json.dumps(p) + "\n")

in_stock    = sum(1 for p in products if p["inventory_count"] > 0)
out_of_stock = sum(1 for p in products if p["inventory_count"] == 0)

print(f"Generated {len(products)} products")
print(f"In stock:     {in_stock}")
print(f"Out of stock: {out_of_stock}")
print(f"File saved:   catalog.jsonl")