"""
Well-known packaged-food brands in India: the brands found on quick-commerce apps (Zepto, Blinkit,
Swiggy Instamart) and in most supermarkets. Catalogue browsing, product search and alternatives only
list products from these brands, so obscure or one-off imported records don't appear.

Values are Open Food Facts brand tags (lowercase, punctuation as hyphens: "Haldiram's" ->
"haldiram-s"); several brands have more than one tag in the data. A product looked up by its
barcode is still shown whatever its brand: the visitor is holding it.
"""

KNOWN_BRANDS: tuple[str, ...] = (
    # Dairy
    "amul", "amul-taaza", "mother-dairy", "nandini", "heritage", "milky-mist", "dodla", "epigamia",
    "go", "gowardhan", "akshayakalpa", "country-delight", "aavin", "verka", "hatsun", "arokya",
    # Biscuits & bakery
    "britannia", "britannia-digestive", "good-day", "parle", "sunfeast", "unibic", "priyagold",
    "mcvitie-s", "bisk-farm", "english-oven", "modern", "harvest-gold", "karachi-bakery", "oreo",
    "cremica", "anmol", "dukes", "bonn",
    # Snacks
    "haldiram-s", "haldirams", "haldiram", "bikaji", "bikano", "balaji", "lay-s", "lays", "kurkure",
    "bingo", "pringles", "uncle-chipps", "too-yumm", "act-ii", "cornitos", "doritos", "cheetos",
    "crax", "prabhuji", "chheda-s", "laxminarayan", "happilo", "farmley", "yellow-diamond",
    # Chocolates & sweets
    "cadbury", "cadbury-dairy-milk", "mondelez", "nestle", "kitkat", "munch", "hershey-s", "ferrero",
    "ferrero-rocher", "kinder", "nutella", "snickers", "mars", "lotte", "perfetti", "alpenliebe",
    "center-fresh", "pulse", "lion",
    # Breakfast & health foods
    "kellogg-s", "kelloggs", "quaker", "saffola", "yoga-bar", "yogabar", "bagrry-s", "true-elements",
    "the-whole-truth", "pintola", "myfitness", "soulfull", "tata-soulfull", "gaia", "muscleblaze",
    "muscle-blaze", "protinex", "ensure", "cerelac",
    # Instant foods
    "maggi", "nissin", "top-ramen", "cup-noodles", "ching-s", "ching-s-secret", "yippee",
    "sunfeast-yippee", "knorr", "wai-wai", "mtr", "samyang", "gits", "weikfield", "pillsbury",
    "bambino",
    # Drinks
    "coca-cola", "the-coca-cola-company", "coca-cola-company", "hindustan-coca-cola-beverages-pvt-ltd",
    "coke", "sprite", "thums-up", "limca", "fanta", "maaza", "minute-maid", "kinley", "pepsico",
    "pepsico-inc", "pepsi", "7up", "mountain-dew", "mirinda", "slice", "sting", "tropicana",
    "gatorade", "red-bull", "monster-energy", "paper-boat", "real", "dabur", "frooti", "appy",
    "appy-fizz", "parle-agro", "bisleri", "b-natural", "raw-pressery", "bournvita", "cadbury-bournvita",
    "horlicks", "boost", "complan", "nescafe", "bru", "tata-tea", "red-label", "brooke-bond",
    "taj-mahal", "tetley", "lipton", "glucon-d", "tang", "rasna", "sofit", "so-good", "storia",
    "lahori",
    # Spreads, sauces & condiments
    "kissan", "veeba", "funfoods", "dr-oetker", "dr-oetker-funfood", "del-monte", "catch", "everest",
    "mdh", "tops", "mother-s-recipe", "smith-jones",
    # Staples and household names
    "aashirvaad", "fortune", "tata", "tata-sampann", "patanjali", "india-gate", "daawat", "nutrela",
    "sundrop", "dhara", "parachute", "fresho", "24-mantra", "organic-tattva", "itc",
    "hindustan-unilever-limited", "cavin-s", "abbott",
)

# Search filter: products whose brand tags include any of the brands above.
KNOWN_BRANDS_CLAUSE = "brands_tags:(" + " OR ".join(f'"{b}"' for b in KNOWN_BRANDS) + ")"
