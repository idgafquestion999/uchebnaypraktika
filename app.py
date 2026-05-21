Интернет-магазин техники
Учебная практика ПМ.02
Студент: Иванников М.А.
"""

from flask import (
    Flask, render_template, request, redirect, url_for, flash, jsonify
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import os

# ============================================================
# НАСТРОЙКА ПРИЛОЖЕНИЯ
# ============================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///electronics.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Войдите для доступа к этой странице.'
login_manager.login_message_category = 'warning'

# ============================================================
# МОДЕЛИ БАЗЫ ДАННЫХ
# ============================================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    cart_items = db.relationship('CartItem', backref='user', lazy='dynamic')
    orders = db.relationship('Order', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    products = db.relationship('Product', backref='category', lazy='dynamic')

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    brand = db.Column(db.String(100))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(200), default='default.jpg')
    stock = db.Column(db.Integer, default=0)

    def is_available(self):
        return self.stock > 0

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    product = db.relationship('Product', lazy='joined')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Новый')
    total_price = db.Column(db.Float, default=0.0)
    items = db.relationship('OrderItem', backref='order', lazy='dynamic')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    product = db.relationship('Product', lazy='joined')

# ============================================================
# ДЕКОРАТОР ДЛЯ АДМИНИСТРАТОРА
# ============================================================

def admin_required(func):
    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            flash('Доступ запрещен.', 'danger')
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    return wrapper

# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def get_cart_total(user_id):
    items = CartItem.query.filter_by(user_id=user_id).all()
    return sum(item.quantity * item.product.price for item in items)

def get_cart_count(user_id):
    items = CartItem.query.filter_by(user_id=user_id).all()
    return sum(item.quantity for item in items)

# ============================================================
# МАРШРУТЫ: АВТОРИЗАЦИЯ
# ============================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')
        errors = []
        if len(username) < 3:
            errors.append('Имя пользователя должно содержать от 3 символов.')
        if User.query.filter_by(username=username).first():
            errors.append('Имя уже занято.')
        if User.query.filter_by(email=email).first():
            errors.append('Email уже зарегистрирован.')
        if len(password) < 6:
            errors.append('Пароль не менее 6 символов.')
        if password != password2:
            errors.append('Пароли не совпадают.')
        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('register.html')
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Регистрация успешна! Войдите.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f'Добро пожаловать, {user.username}!', 'success')
            return redirect(url_for('index'))
        flash('Неверное имя или пароль.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли.', 'info')
    return redirect(url_for('index'))

# ============================================================
# МАРШРУТЫ: ГЛАВНАЯ И КАТАЛОГ
# ============================================================

@app.route('/')
def index():
    products = Product.query.filter(Product.stock > 0).limit(8).all()
    return render_template('index.html', top_products=products)

@app.route('/catalog')
def catalog():
    category_id = request.args.get('category', type=int)
    brand = request.args.get('brand', '').strip()
    sort = request.args.get('sort', 'name')
    query = Product.query.filter(Product.stock > 0)
    if category_id:
        query = query.filter_by(category_id=category_id)
    if brand:
        query = query.filter_by(brand=brand)
    if sort == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.name.asc())
    products = query.all()
    categories = Category.query.all()
    brands_list = [b[0] for b in db.session.query(Product.brand).distinct().order_by(Product.brand).all()]
    return render_template('catalog.html', products=products, categories=categories,
                           brands=brands_list, current_category=category_id,
                           current_brand=brand, current_sort=sort)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product.html', product=product)

# ============================================================
# МАРШРУТЫ: КОРЗИНА
# ============================================================

@app.route('/cart')
@login_required
def cart():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = get_cart_total(current_user.id)
    return render_template('cart.html', items=items, total=total)

@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))
    if quantity < 1:
        flash('Количество должно быть больше 0.', 'warning')
        return redirect(url_for('product_detail', product_id=product_id))
    existing = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if existing:
        existing.quantity += quantity
    else:
        item = CartItem(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(item)
    db.session.commit()
    flash('Товар добавлен в корзину.', 'success')
    return redirect(request.referrer or url_for('catalog'))

@app.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
        flash('Товар удален.', 'info')
    return redirect(url_for('cart'))

@app.route('/cart/clear', methods=['POST'])
@login_required
def clear_cart():
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('Корзина очищена.', 'info')
    return redirect(url_for('cart'))

# ============================================================
# МАРШРУТЫ: ЗАКАЗЫ
# ============================================================

@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        flash('Корзина пуста.', 'warning')
        return redirect(url_for('cart'))
    total = get_cart_total(current_user.id)
    order = Order(user_id=current_user.id, total_price=total)
    db.session.add(order)
    db.session.flush()
    for item in items:
        order_item = OrderItem(order_id=order.id, product_id=item.product_id,
                               quantity=item.quantity, price=item.product.price)
        db.session.add(order_item)
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash(f'Заказ №{order.id} оформлен на сумму {total:.2f} ₽.', 'success')
    return redirect(url_for('orders'))

@app.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id)\
        .order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=user_orders)

# ============================================================
# МАРШРУТЫ: АДМИН-ПАНЕЛЬ
# ============================================================

@app.route('/admin')
@admin_required
def admin_dashboard():
    products_count = Product.query.count()
    orders_count = Order.query.count()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html', products_count=products_count,
                           orders_count=orders_count, recent_orders=recent_orders)

@app.route('/admin/products')
@admin_required
def admin_products():
    products = Product.query.order_by(Product.name).all()
    categories = Category.query.all()
    return render_template('admin/products.html', products=products, categories=categories)

@app.route('/admin/product/add', methods=['POST'])
@admin_required
def admin_add_product():
    name = request.form.get('name', '').strip()
    brand = request.form.get('brand', '').strip()
    category_id = request.form.get('category_id', type=int)
    price = request.form.get('price', type=float)
    description = request.form.get('description', '').strip()
    stock = request.form.get('stock', type=int, default=0)
    image_url = request.form.get('image_url', 'default.jpg').strip()
    if not name or not category_id or price is None or price <= 0:
        flash('Заполните обязательные поля.', 'danger')
        return redirect(url_for('admin_products'))
    product = Product(name=name, brand=brand, category_id=category_id,
                      price=price, description=description, stock=stock, image_url=image_url)
    db.session.add(product)
    db.session.commit()
    flash('Товар добавлен.', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/product/delete/<int:product_id>', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Товар удален.', 'info')
    return redirect(url_for('admin_products'))

@app.route('/admin/orders')
@admin_required
def admin_orders():
    all_orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=all_orders)

@app.route('/admin/order/status/<int:order_id>', methods=['POST'])
@admin_required
def admin_update_status(order_id):
    order = Order.query.get_or_404(order_id)
    status = request.form.get('status', '')
    if status in ['Новый', 'В обработке', 'Отправлен', 'Выполнен', 'Отменен']:
        order.status = status
        db.session.commit()
        flash(f'Статус заказа №{order.id} изменен на «{status}».', 'success')
    return redirect(url_for('admin_orders'))

# ============================================================
# API ДЛЯ АСИНХРОННОЙ РАБОТЫ
# ============================================================

@app.route('/api/cart/count')
@login_required
def api_cart_count():
    return jsonify({'count': get_cart_count(current_user.id)})

@app.route('/api/cart/add/<int:product_id>', methods=['POST'])
@login_required
def api_add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    existing = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if existing:
        existing.quantity += 1
    else:
        item = CartItem(user_id=current_user.id, product_id=product_id, quantity=1)
        db.session.add(item)
    db.session.commit()
    return jsonify({'success': True, 'cart_count': get_cart_count(current_user.id)})

# ============================================================
# ОБРАБОТКА ОШИБОК
# ============================================================

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
