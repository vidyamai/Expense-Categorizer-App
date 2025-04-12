import os
import json
from models import db, Category

def allowed_file(filename, allowed_extensions):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def create_default_categories():
    """Create default categories from categories.json if they don't exist."""
    # Check if categories already exist
    if Category.query.first() is not None:
        return
    
    # Load categories from JSON file
    with open('categories.json', 'r') as f:
        categories_data = json.load(f)
    
    # Create category entries in the database
    for category_name, keywords in categories_data.items():
        category = Category(name=category_name, keywords=json.dumps(keywords))
        db.session.add(category)
    
    db.session.commit()

def save_learned_item(user_id, item_description, category_id):
    """Save a user-corrected item to the learned items JSON."""
    # Make sure the file exists
    if not os.path.exists('user_learned_items.json'):
        with open('user_learned_items.json', 'w') as f:
            json.dump({}, f)
    
    # Get the category name from ID
    from models import Category
    category = Category.query.get(category_id)
    if not category:
        return False
    
    # Load existing learned items
    with open('user_learned_items.json', 'r+') as f:
        try:
            learned_items = json.load(f)
        except json.JSONDecodeError:
            learned_items = {}
        
        # Store the item with its category name for easier readability
        # Use the item description in lowercase for case-insensitive matching
        learned_items[item_description.lower()] = category.name
        
        # Write back to file
        f.seek(0)
        json.dump(learned_items, f, indent=4)
        f.truncate()
    
    return True

def get_learned_category(user_id, item_description):
    """Get the category ID for an item based on learned items.
    Returns the category ID or None if not found."""
    if not os.path.exists('user_learned_items.json'):
        return None
    
    with open('user_learned_items.json', 'r') as f:
        try:
            learned_items = json.load(f)
        except json.JSONDecodeError:
            return None
        
        # Check if the item exists in learned items (case-insensitive)
        item_key = item_description.lower()
        if item_key in learned_items:
            # Get the category name
            category_name = learned_items[item_key]
            
            # Find the category ID from the name
            from models import Category
            category = Category.query.filter_by(name=category_name).first()
            if category:
                return category.id
    
    return None

def save_batch_learned_items(corrections):
    """Save multiple corrected items to the learned items JSON.
    
    Args:
        corrections: List of dictionaries with 'description' and 'category_name' keys
    
    Returns:
        bool: Success status
    """
    # Make sure the file exists
    if not os.path.exists('user_learned_items.json'):
        with open('user_learned_items.json', 'w') as f:
            json.dump({}, f)
    
    # Load existing learned items
    with open('user_learned_items.json', 'r+') as f:
        try:
            learned_items = json.load(f)
        except json.JSONDecodeError:
            learned_items = {}
        
        # Add each correction to the learned items
        for correction in corrections:
            description = correction.get('description', '').lower()
            category_name = correction.get('category_name', '')
            
            if description and category_name:
                learned_items[description] = category_name
        
        # Write back to file
        f.seek(0)
        json.dump(learned_items, f, indent=4)
        f.truncate()
    
    return True

def find_duplicates(expenses, new_expenses):
    """Find duplicate transactions between existing expenses and new ones."""
    duplicates = []
    non_duplicates = []
    
    for new_expense in new_expenses:
        is_duplicate = False
        for expense in expenses:
            # Check for same date and amount
            if (expense.date.date() == new_expense['date'].date() and 
                abs(expense.amount - new_expense['amount']) < 0.01):
                duplicates.append(new_expense)
                is_duplicate = True
                break
        
        if not is_duplicate:
            non_duplicates.append(new_expense)
    
    return duplicates, non_duplicates
