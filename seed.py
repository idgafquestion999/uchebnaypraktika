from app import app, db
from app import User, Category, Product

def seed():
    with app.app_context():
        db.drop_all()
        db.create_all()

        cats = [
            Category(name='Смартфоны'),
            Category(name='Ноутбуки'),
            Category(name='Планшеты'),
            Category(name='Телевизоры'),
            Category(name='Наушники')
        ]
        db.session.add_all(cats)
        db.session.commit()

        products = [
            Product(name='iPhone 15', brand='Apple', category_id=1, price=89990, stock=10),
            Product(name='Samsung S24', brand='Samsung', category_id=1, price=79990, stock=15),
            Product(name='MacBook Air M3', brand='Apple', category_id=2, price=124990, stock=5),
            Product(name='iPad Pro M4', brand='Apple', category_id=3, price=99990, stock=8),
            Product(name='Sony WH-1000XM5', brand='Sony', category_id=5, price=34990, stock=20),
        ]
        db.session.add_all(products)
        db.session.commit()

        admin = User(username='admin', email='admin@shop.ru', is_admin=True)
        admin.set_password('admin123')
        user = User(username='user', email='user@shop.ru')
        user.set_password('user123')
        db.session.add_all([admin, user])
        db.session.commit()

        print('✅ База заполнена!')

if __name__ == '__main__':
    seed()
