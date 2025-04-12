import json
import logging
import requests
from rapidfuzz import fuzz
from models import db
from models import Category

def load_categories():
    """Load categories from the database."""
    categories = {}
    for category in Category.query.all():
        categories[category.id] = {
            'name': category.name,
            'keywords': json.loads(category.keywords) if category.keywords else []
        }
    return categories

def load_user_learned_items(user_id):
    """Load learned items from the JSON file."""
    try:
        with open('user_learned_items.json', 'r') as f:
            learned_items = json.load(f)
            return learned_items
    except (FileNotFoundError, json.JSONDecodeError):
        with open('user_learned_items.json', 'w') as f:
            json.dump({}, f)
        return {}

def categorize_item(description, categories, user_learned_items):
    """Categorize an item based on its description."""

    # Normalize and skip irrelevant lines
    desc_lower = description.lower().strip()
    skip_words = ['total', 'subtotal', 'tax', 'amount due', 'change due', 'balance']
    if any(skip in desc_lower for skip in skip_words):
        return None

    # Check if user already corrected it
    if desc_lower in user_learned_items:
        category_name = user_learned_items[desc_lower]
        for category_id, category_data in categories.items():
            if category_data['name'] == category_name:
                return category_id

    # Fuzzy match to keywords
    best_match = None
    best_score = 0
    for category_id, category_data in categories.items():
        for keyword in category_data['keywords']:
            score = fuzz.partial_ratio(desc_lower, keyword.lower())
            if score > best_score:
                best_score = score
                best_match = category_id

    if best_score >= 80:
        return best_match

    # Try Open Food Facts
    try:
        category = get_open_food_facts_category(description)
        if category:
            mapped_category_id = map_off_category_to_internal(category, categories)
            if mapped_category_id:
                return mapped_category_id
    except Exception as e:
        logging.error(f"Error looking up category in Open Food Facts: {e}")

    # Default to first category if needed
    return list(categories.keys())[0]

def get_open_food_facts_category(product_name):
    """Query the Open Food Facts API to get product category."""
    try:
        query = product_name.replace(' ', '+')
        url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('products') and len(data['products']) > 0:
                categories = data['products'][0].get('categories', '')
                if categories:
                    return categories.split(',')[0].strip()
        return None
    except Exception as e:
        logging.error(f"Error in Open Food Facts API: {e}")
        return None

def map_off_category_to_internal(off_category, internal_categories):
    """Map an Open Food Facts category to our internal categories."""
    off_mappings = {
        'Beverages': 'Groceries',
        'Snacks': 'Snacks',
        'Breakfasts': 'Groceries',
        'Dairies': 'Groceries',
        'Frozen foods': 'Groceries',
        'Meals': 'Groceries',
        'Fruits': 'Fruits',
        'Vegetables': 'Groceries',
        'Chips': 'Snacks',
        'Chocolates': 'Snacks',
        'Candies': 'Snacks',
        'Desserts': 'Snacks',
        'Fast foods': 'Dining Out',
        'Restaurants': 'Dining Out',
        'Canned foods': 'Groceries'
    }

    for key, value in off_mappings.items():
        if key.lower() in off_category.lower():
            for category_id, category_data in internal_categories.items():
                if category_data['name'] == value:
                    return category_id

    best_match = None
    best_score = 0
    for category_id, category_data in internal_categories.items():
        score = fuzz.partial_ratio(off_category.lower(), category_data['name'].lower())
        if score > best_score:
            best_score = score
            best_match = category_id

    if best_score >= 60:
        return best_match

    for category_id, category_data in internal_categories.items():
        if category_data['name'] == 'Groceries':
            return category_id

    return list(internal_categories.keys())[0]

def categorize_expense_items(text, user_id):
    """Extract and categorize expense items from OCR text."""
    from ocr_processor import extract_items, extract_date, extract_amounts

    categories = load_categories()
    user_learned_items = load_user_learned_items(user_id)
    date = extract_date(text)
    items = extract_items(text)

    if not items:
        amounts = extract_amounts(text)
        if amounts:
            for i, amount in enumerate(amounts):
                items.append({
                    'description': f"Item {i+1}",
                    'amount': amount
                })

    categorized_items = []
    for item in items:
        # Skip irrelevant lines again at this level
        if any(skip in item['description'].lower() for skip in ['total', 'subtotal', 'tax', 'amount due', 'change due']):
            continue

        category_id = categorize_item(item['description'], categories, user_learned_items)
        if category_id is None:
            continue  # Item was skipped (irrelevant)

        category_name = categories[category_id]['name']
        categorized_items.append({
            'description': item['description'],
            'amount': item['amount'],
            'category_id': category_id,
            'category': category_name,
            'date': date
        })

    return categorized_items
