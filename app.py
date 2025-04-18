import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Import models and db
from models import db, User, Expense, Category
# Import custom modules
from categorizer import categorize_expense_items, get_open_food_facts_category
from ocr_processor import process_uploaded_file
from utils import allowed_file, create_default_categories

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Add datetime to template context
@app.context_processor
def inject_datetime():
    return dict(datetime=datetime)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///expenses.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["ALLOWED_EXTENSIONS"] = {"pdf", "png", "jpg", "jpeg"}
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # Limit file size to 16MB

# Initialize the database
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Make sure the upload folder exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Import necessary modules after app initialization to avoid circular imports
with app.app_context():
    # Import models
    from models import User, Expense, Category
    
    # Import custom modules
    from ocr_processor import process_uploaded_file
    from categorizer import categorize_expense_items, get_open_food_facts_category
    from utils import allowed_file, create_default_categories
    
    # Import Google Auth blueprint
    from google_auth import google_auth
    
    # Register blueprints
    app.register_blueprint(google_auth)
    
    # Create database tables
    db.create_all()
    
    # Create default categories if they don't exist
    create_default_categories()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('upload'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('upload'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists. Please login or use a different email.', 'danger')
            return redirect(url_for('register'))
        
        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('upload'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('upload'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        
        if user:
            # In a real application, send an email with a reset link
            # For this demo, just show a success message
            flash('If your email exists in our system, a password reset link has been sent.', 'info')
        else:
            # Don't reveal that the email doesn't exist for security reasons
            flash('If your email exists in our system, a password reset link has been sent.', 'info')
        
        return redirect(url_for('login'))
    
    return render_template('reset_password.html')

# Replace the upload route with this improved version

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        # Check if file is present in the request
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        # Check if file is selected
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        # Check if file is allowed
        if file and allowed_file(file.filename, app.config["ALLOWED_EXTENSIONS"]):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            try:
                # Check if Tesseract is installed
                from ocr_processor import check_tesseract
                if not check_tesseract():
                    flash('Tesseract OCR is not installed or not configured properly. Please install Tesseract OCR to process images and PDFs.', 'danger')
                    return redirect(request.url)
                
                # Process the file with OCR
                from ocr_processor import process_uploaded_file
                extracted_text = process_uploaded_file(file_path)
                
                if not extracted_text or not extracted_text.strip():
                    flash('No text could be extracted from the file. Please try another file or ensure the image has clear text.', 'warning')
                    return redirect(request.url)
                
                if extracted_text.startswith("ERROR:"):
                    flash(f'OCR Error: {extracted_text[7:]}', 'danger')
                    return redirect(request.url)
                
                # Log a sample of the extracted text for debugging
                logging.debug(f"Extracted text sample: {extracted_text[:200]}...")
                
                # Save the extracted text to a debug file (temporary for troubleshooting)
                debug_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{filename}_debug.txt")
                with open(debug_path, 'w') as f:
                    f.write(extracted_text)
                
                # Categorize the expenses
                categorized_items = categorize_expense_items(extracted_text, current_user.id)
                
                if not categorized_items:
                    flash('No expense items were found in the extracted text. Please upload a receipt or invoice.', 'warning')
                    return redirect(request.url)
                
                # Store in session for results page
                session['categorized_items'] = categorized_items
                
                # Save expenses to database
                for item in categorized_items:
                    expense = Expense(
                        user_id=current_user.id,
                        description=item['description'],
                        amount=item['amount'],
                        category_id=item['category_id'],
                        date=datetime.strptime(item['date'], '%Y-%m-%d') if item.get('date') else datetime.now()
                    )
                    db.session.add(expense)
                
                db.session.commit()
                
                # Redirect to results page
                return redirect(url_for('results'))
            
            except Exception as e:
                logging.error(f"Error processing file: {str(e)}", exc_info=True)
                flash(f'Error processing file: {str(e)}', 'danger')
                return redirect(request.url)
            finally:
                # Clean up the files
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                # Remove debug file if it exists
                debug_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{filename}_debug.txt")
                if os.path.exists(debug_path):
                    os.remove(debug_path)
        else:
            flash('File type not allowed. Please upload a PDF or image file.', 'danger')
            return redirect(request.url)
    
    return render_template('upload.html')
@app.route('/results')
@login_required
def results():
    # Get the categorized items from the session
    categorized_items = session.get('categorized_items', [])
    
    if not categorized_items:
        flash('No expense data available. Please upload a file first.', 'warning')
        return redirect(url_for('upload'))
    
    # Calculate totals by category
    category_totals = {}
    for item in categorized_items:
        category = item['category']
        amount = item['amount']
        if category in category_totals:
            category_totals[category] += amount
        else:
            category_totals[category] = amount
    
    # Get all available categories for the dropdown
    categories = Category.query.all()
    
    return render_template('results.html', 
                          expenses=categorized_items, 
                          category_totals=category_totals,
                          categories=categories)

@app.route('/update_category', methods=['POST'])
@login_required
def update_category():
    expense_id = request.form.get('expense_id')
    new_category_id = request.form.get('new_category_id')
    item_description = request.form.get('item_description')
    
    if expense_id and new_category_id:
        # Update the expense category in the database
        expense = Expense.query.get(expense_id)
        if expense and expense.user_id == current_user.id:
            expense.category_id = new_category_id
            db.session.commit()
            
            # Learn this categorization for future use
            from utils import save_learned_item
            save_learned_item(current_user.id, item_description, new_category_id)
            
            flash('Category updated successfully!', 'success')
        else:
            flash('Expense not found or not authorized', 'danger')
    else:
        flash('Invalid request', 'danger')
    
    return redirect(url_for('results'))

@app.route('/update_multiple_categories', methods=['POST'])
@login_required
def update_multiple_categories():
    """Update multiple item categories at once and save them to the learned items."""
    if request.is_json:
        data = request.get_json()
        corrections = data.get('corrections', [])
        
        if corrections:
            success_count = 0
            
            # Update each expense in the database
            for correction in corrections:
                expense_id = correction.get('expense_id')
                new_category_id = correction.get('new_category_id')
                
                if expense_id and new_category_id:
                    expense = Expense.query.get(expense_id)
                    if expense and expense.user_id == current_user.id:
                        expense.category_id = new_category_id
                        success_count += 1
            
            if success_count > 0:
                db.session.commit()
                
                # Process corrections for learning
                from utils import save_batch_learned_items
                
                # Convert category IDs to names for the learned items
                learned_corrections = []
                for correction in corrections:
                    description = correction.get('description')
                    category_id = correction.get('new_category_id')
                    
                    if description and category_id:
                        category = Category.query.get(category_id)
                        if category:
                            learned_corrections.append({
                                'description': description,
                                'category_name': category.name
                            })
                
                save_batch_learned_items(learned_corrections)
                
                return jsonify({
                    'success': True,
                    'message': f'Successfully updated {success_count} categories.',
                    'updated_count': success_count
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'No valid expenses found to update.'
                }), 400
        else:
            return jsonify({
                'success': False,
                'message': 'No corrections provided.'
            }), 400
    else:
        return jsonify({
            'success': False,
            'message': 'Invalid request format. JSON expected.'
        }), 400
@app.route('/apply_changes', methods=['POST'])
@login_required
def apply_changes():
    categorized_items = session.get('categorized_items', [])
    updated_items = []

    for i, item in enumerate(categorized_items):
        description = request.form.get(f'description_{i}')
        amount = float(request.form.get(f'amount_{i}', 0))
        category_id = int(request.form.get(f'category_{i}'))
        date = request.form.get(f'date_{i}')
        delete_flag = request.form.get(f'delete_{i}')

        if delete_flag:
            continue  # Skip deleted items

        from utils import save_learned_item
        category = Category.query.get(category_id)
        if category:
            save_learned_item(current_user.id, description, category.name)

        updated_items.append({
            'description': description,
            'amount': amount,
            'category_id': category_id,
            'category': category.name,
            'date': date
        })

        expense = Expense(
            user_id=current_user.id,
            description=description,
            amount=amount,
            category_id=category_id,
            date=datetime.strptime(date, '%Y-%m-%d') if date else datetime.now()
        )
        db.session.add(expense)

    db.session.commit()
    session['categorized_items'] = updated_items
    flash('Changes applied successfully!', 'success')
    return redirect(url_for('results'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8501, debug=True)
