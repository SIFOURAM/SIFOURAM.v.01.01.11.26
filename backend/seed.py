SEED_USERS = [
    {
        "name": "Baazulfikar",
        "username": "baa",
        "email": "baazulfikar@gmail.com",
        "whatsapp": "081283578212",
        "password": "Nai130994",
        "pin": "130994",
        "role": "owner",
    },
]

# name, unit, pack_qty, pack_price, pack_label, category
SEED_MATERIALS = [
    ("Beans", "g", 1000, 150000, "pack", "raw"),
    ("Water", "ml", 19000, 10000, "gallon", "raw"),
    ("Ice Cubes", "g", 18000, 15000, "ball", "raw"),
    ("SPM (Milk Powder)", "g", 1000, 75000, "pack", "raw"),
    ("Premium Palm Sugar", "ml", 5000, 180000, "jerrycan", "raw"),
    ("SKM Dairy Champ", "ml", 2500, 75000, "pack", "raw"),
    ("Premium Vanilla Syrup", "ml", 5000, 180000, "jerrycan", "raw"),
    ("Salted Caramel Syrup", "ml", 5000, 180000, "jerrycan", "raw"),
    ("Premium Butterscotch Syrup", "ml", 5000, 180000, "jerrycan", "raw"),
    ("Royal Chocolate Powder", "g", 1000, 75000, "pack", "raw"),
    ("Matcha Powder", "g", 1000, 75000, "pack", "raw"),
    ("Simple Syrup", "ml", 5000, 22000, "jerrycan", "raw"),
    ("Oslo Tea", "g", 120, 18000, "pack", "raw"),
    ("Plastic Cup", "pcs", 50, 50000, "pack", "packaging"),
    ("Sealed Lid", "pcs", 1800, 45000, "pack", "packaging"),
    ("Lid", "pcs", 1000, 190000, "box", "packaging"),
    ("Straw", "pcs", 500, 20000, "pack", "packaging"),
    ("Takeaway Plastic Bag", "pcs", 100, 10000, "pack", "packaging"),
]

BASE = [("Water", 150), ("Ice Cubes", 222)]
COFFEE = [("Beans", 9), ("SPM (Milk Powder)", 20)]

SEED_MENUS = [
    ("SI AMERICANO", 8000, 30, [("Beans", 9)] + BASE),
    ("SI KOPSU AREN", 10000, 50, COFFEE + [("Premium Palm Sugar", 20)] + BASE),
    ("SI CREAMY LATTE", 12000, 30, COFFEE + [("SKM Dairy Champ", 20)] + BASE),
    ("SI VANILLA LATTE", 12000, 30, COFFEE + [("Premium Vanilla Syrup", 20)] + BASE),
    ("SI SALTED CARAMEL", 12000, 30, COFFEE + [("Salted Caramel Syrup", 20)] + BASE),
    ("SI BUTTERSCOTCH", 12000, 30, COFFEE + [("Premium Butterscotch Syrup", 20)] + BASE),
    ("SI CHOCOLATE", 12000, 30, [("Royal Chocolate Powder", 15), ("SPM (Milk Powder)", 20), ("Simple Syrup", 20)] + BASE),
    ("SI MATCHA", 12000, 30, [("Matcha Powder", 15), ("SPM (Milk Powder)", 20), ("Simple Syrup", 20)] + BASE),
    ("SI TEH MANIS", 5000, 30, [("Oslo Tea", 3), ("Simple Syrup", 20)] + BASE),
]

MENU_PHOTOS = {
    "SI AMERICANO": "https://images.unsplash.com/photo-1551030173-122aabc4489c?w=400&q=80",
    "SI KOPSU AREN": "https://images.unsplash.com/photo-1559496417-e7f25cb247f3?w=400&q=80",
    "SI CREAMY LATTE": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=400&q=80",
    "SI VANILLA LATTE": "https://images.unsplash.com/photo-1461023058943-07fcbe16d735?w=400&q=80",
    "SI SALTED CARAMEL": "https://images.unsplash.com/photo-1485808191679-5f86510681a2?w=400&q=80",
    "SI BUTTERSCOTCH": "https://images.unsplash.com/photo-1517701550927-30cf4ba1dba5?w=400&q=80",
    "SI CHOCOLATE": "https://images.unsplash.com/photo-1542990253-a781e04c0082?w=400&q=80",
    "SI MATCHA": "https://images.unsplash.com/photo-1515823064-d6e0c04616a7?w=400&q=80",
    "SI TEH MANIS": "https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=400&q=80",
}
