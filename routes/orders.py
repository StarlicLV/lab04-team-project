"""Замовлення: оформлення з кошика, статуси, промокоди (рівень 3), адмінка.

Кошик читається з session['cart'] = {product_id: quantity}. Статуси — models.ORDER_STATUSES.
"""
import re
import sqlite3

from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, session, url_for)
from werkzeug.routing import BuildError

from models import ORDER_STATUSES, execute_db, get_db, query_db

bp = Blueprint('orders', __name__)


# ---------------------------------------------------------------------------
# Допоміжні функції
# ---------------------------------------------------------------------------

def menu_url():
    """Посилання на меню: працює і до, і після того, як частина Б перенесе меню в shop.menu."""
    try:
        return url_for('shop.menu')
    except BuildError:
        return url_for('menu')


def get_cart_lines():
    """Перетворює session['cart'] на список позицій із даними товарів із БД.

    Ключі в сесії — рядки, тому їх перетворюємо на int. Товари, яких уже немає
    або які вимкнені (is_available = 0), пропускаємо й повідомляємо про це.
    """
    cart = session.get('cart') or {}
    lines = []
    dropped = False
    for raw_id, raw_qty in cart.items():
        try:
            product_id = int(raw_id)
            quantity = int(raw_qty)
        except (TypeError, ValueError):
            dropped = True
            continue
        if quantity <= 0:
            dropped = True
            continue
        product = query_db(
            'SELECT * FROM products WHERE id = ? AND is_available = 1',
            (product_id,), one=True)
        if product is None:
            dropped = True
            continue
        lines.append({
            'product': product,
            'quantity': quantity,
            'line_total': round(product['price'] * quantity, 2),
        })
    return lines, dropped


def find_active_promo(code):
    """Повертає рядок активного промокоду або None."""
    return query_db(
        'SELECT * FROM promo_codes WHERE code = ? AND is_active = 1',
        (code.strip().upper(),), one=True)


def calc_totals(lines, promo):
    """Повертає (сума без знижки, знижка в грн, підсумок)."""
    subtotal = round(sum(line['line_total'] for line in lines), 2)
    discount = 0.0
    if promo is not None:
        discount = round(subtotal * promo['discount_percent'] / 100, 2)
    total = round(subtotal - discount, 2)
    return subtotal, discount, total


def normalize_phone(phone):
    """Прибирає пробіли, дефіси та дужки: '+380 (50) 111-22-33' -> '+380501112233'."""
    return re.sub(r'[\s\-()]', '', phone)


# ---------------------------------------------------------------------------
# Оформлення замовлення (публічна частина)
# ---------------------------------------------------------------------------

@bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    lines, dropped = get_cart_lines()
    if dropped:
        # Прибираємо з сесії позиції, яких більше не можна замовити
        session['cart'] = {str(line['product']['id']): line['quantity'] for line in lines}
        flash('Деякі товари стали недоступні й були прибрані з кошика.')

    if not lines:
        flash('Ваш кошик порожній. Оберіть щось із меню.')
        return redirect(menu_url())

    form = {'name': '', 'phone': '', 'email': '', 'address': '', 'comment': '', 'promo_code': ''}
    errors = {}
    promo = None

    if request.method == 'POST':
        for key in form:
            form[key] = request.form.get(key, '').strip()

        # Промокод перевіряємо завжди, коли його введено
        if form['promo_code']:
            promo = find_active_promo(form['promo_code'])
            if promo is None:
                errors['promo_code'] = 'Такого активного промокоду немає.'

        action = request.form.get('action', 'order')

        if action == 'apply':
            # Кнопка «Застосувати»: лише показуємо знижку, нічого не зберігаємо
            if promo is not None:
                flash(f'Промокод {promo["code"]} застосовано: знижка {promo["discount_percent"]}%.')
        else:
            phone = normalize_phone(form['phone'])
            if not form['name']:
                errors['name'] = 'Вкажіть ім’я.'
            if not phone:
                errors['phone'] = 'Вкажіть телефон.'
            elif not re.fullmatch(r'\+?\d{9,15}', phone):
                errors['phone'] = 'Телефон має містити від 9 до 15 цифр (можна з +).'
            if form['email'] and '@' not in form['email']:
                errors['email'] = 'Email має містити @.'
            if not form['address']:
                errors['address'] = 'Вкажіть адресу доставки.'

            if not errors:
                subtotal, discount, total = calc_totals(lines, promo)
                order_id = save_order(form, phone, lines, promo, discount, total)
                if order_id is not None:
                    session['cart'] = {}
                    session['last_order_id'] = order_id
                    flash('Дякуємо! Замовлення оформлено.')
                    return redirect(url_for('orders.confirmation', order_id=order_id))
                errors['general'] = 'Не вдалося зберегти замовлення. Спробуйте ще раз.'

    subtotal, discount, total = calc_totals(lines, promo)
    return render_template(
        'orders/checkout.html', lines=lines, form=form, errors=errors, promo=promo,
        subtotal=subtotal, discount=discount, total=total, menu_url=menu_url())


def save_order(form, phone, lines, promo, discount, total):
    """Зберігає клієнта, замовлення та позиції в ОДНІЙ транзакції.

    Жоден INSERT не робить commit сам: commit відбувається один раз наприкінці.
    Якщо щось іде не так — rollback, і в БД не лишається напівстворене замовлення.
    Повертає id замовлення або None.
    """
    db = get_db()
    try:
        # 1. Клієнт: шукаємо за телефоном (phone UNIQUE) або створюємо нового
        customer = db.execute(
            'SELECT id, email FROM customers WHERE phone = ?', (phone,)).fetchone()
        if customer is not None:
            customer_id = customer['id']
            if form['email'] and not customer['email']:
                db.execute('UPDATE customers SET email = ? WHERE id = ?',
                           (form['email'], customer_id))
        else:
            cursor = db.execute(
                'INSERT INTO customers (name, phone, email) VALUES (?, ?, ?)',
                (form['name'], phone, form['email'] or None))
            customer_id = cursor.lastrowid

        # 2. Замовлення
        cursor = db.execute(
            'INSERT INTO orders (customer_id, status, address, comment, total, promo_code, discount) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            (customer_id, 'new', form['address'], form['comment'], total,
             promo['code'] if promo else None, discount))
        order_id = cursor.lastrowid

        # 3. Позиції з фіксацією ціни на момент замовлення
        db.executemany(
            'INSERT INTO order_items (order_id, product_id, quantity, price_at_order) '
            'VALUES (?, ?, ?, ?)',
            [(order_id, line['product']['id'], line['quantity'], line['product']['price'])
             for line in lines])

        db.commit()
        return order_id
    except sqlite3.Error:
        db.rollback()
        current_app.logger.exception('Помилка при збереженні замовлення')
        return None


@bp.route('/order/<int:order_id>/confirmation')
def confirmation(order_id):
    # Показуємо підтвердження лише тому, хто щойно оформив це замовлення
    if session.get('last_order_id') != order_id:
        return redirect(menu_url())
    order = query_db(
        'SELECT o.*, c.name AS customer_name, c.phone AS customer_phone '
        'FROM orders o JOIN customers c ON c.id = o.customer_id WHERE o.id = ?',
        (order_id,), one=True)
    if order is None:
        abort(404)
    items = get_order_items(order_id)
    return render_template('orders/confirmation.html', order=order, items=items,
                           statuses=ORDER_STATUSES, menu_url=menu_url())


# ---------------------------------------------------------------------------
# Адмінка: замовлення
# ---------------------------------------------------------------------------

def get_order_items(order_id):
    """Позиції замовлення: JOIN між order_items і products."""
    return query_db(
        'SELECT oi.quantity, oi.price_at_order, p.name, '
        '       ROUND(oi.quantity * oi.price_at_order, 2) AS line_total '
        'FROM order_items oi '
        'JOIN products p ON p.id = oi.product_id '
        'WHERE oi.order_id = ? '
        'ORDER BY oi.id',
        (order_id,))


@bp.route('/admin/orders')
def admin_orders():
    status = request.args.get('status', '')
    sql = ('SELECT o.id, o.status, o.total, o.created_at, '
           '       c.name AS customer_name, c.phone AS customer_phone '
           'FROM orders o JOIN customers c ON c.id = o.customer_id ')
    args = ()
    if status in ORDER_STATUSES:
        sql += 'WHERE o.status = ? '
        args = (status,)
    else:
        status = ''
    sql += 'ORDER BY o.created_at DESC, o.id DESC'
    orders = query_db(sql, args)
    return render_template('admin/orders.html', orders=orders, statuses=ORDER_STATUSES,
                           current_status=status)


@bp.route('/admin/orders/<int:order_id>')
def admin_order_detail(order_id):
    order = query_db(
        'SELECT o.*, c.name AS customer_name, c.phone AS customer_phone, '
        '       c.email AS customer_email '
        'FROM orders o JOIN customers c ON c.id = o.customer_id WHERE o.id = ?',
        (order_id,), one=True)
    if order is None:
        abort(404)
    items = get_order_items(order_id)
    return render_template('admin/order_detail.html', order=order, items=items,
                           statuses=ORDER_STATUSES)


@bp.route('/admin/orders/<int:order_id>/status', methods=['POST'])
def update_status(order_id):
    new_status = request.form.get('status', '')
    if new_status not in ORDER_STATUSES:
        flash('Невідомий статус замовлення.')
        return redirect(url_for('orders.admin_order_detail', order_id=order_id))
    if query_db('SELECT id FROM orders WHERE id = ?', (order_id,), one=True) is None:
        abort(404)
    execute_db('UPDATE orders SET status = ? WHERE id = ?', (new_status, order_id))
    flash(f'Статус замовлення №{order_id} змінено на «{ORDER_STATUSES[new_status]}».')
    return redirect(url_for('orders.admin_order_detail', order_id=order_id))


# ---------------------------------------------------------------------------
# Адмінка: промокоди (рівень 3)
# ---------------------------------------------------------------------------

@bp.route('/admin/promos')
def admin_promos():
    promos = query_db('SELECT * FROM promo_codes ORDER BY id DESC')
    return render_template('admin/promos.html', promos=promos,
                           form={'code': '', 'discount_percent': ''}, errors={})


@bp.route('/admin/promos/add', methods=['POST'])
def add_promo():
    code = request.form.get('code', '').strip().upper()
    percent_raw = request.form.get('discount_percent', '').strip()
    errors = {}

    if not code:
        errors['code'] = 'Вкажіть код.'
    elif not re.fullmatch(r'[A-Z0-9_-]{3,30}', code):
        errors['code'] = 'Код: 3–30 символів, лише латиниця, цифри, - та _.'

    percent = None
    try:
        percent = int(percent_raw)
        if not 1 <= percent <= 100:
            raise ValueError
    except ValueError:
        errors['discount_percent'] = 'Знижка — ціле число від 1 до 100.'

    if not errors:
        try:
            execute_db('INSERT INTO promo_codes (code, discount_percent) VALUES (?, ?)',
                       (code, percent))
            flash(f'Промокод {code} додано.')
            return redirect(url_for('orders.admin_promos'))
        except sqlite3.IntegrityError:
            errors['code'] = 'Такий промокод уже існує.'

    promos = query_db('SELECT * FROM promo_codes ORDER BY id DESC')
    return render_template('admin/promos.html', promos=promos,
                           form={'code': code, 'discount_percent': percent_raw}, errors=errors)


@bp.route('/admin/promos/<int:promo_id>/toggle', methods=['POST'])
def toggle_promo(promo_id):
    promo = query_db('SELECT * FROM promo_codes WHERE id = ?', (promo_id,), one=True)
    if promo is None:
        abort(404)
    new_value = 0 if promo['is_active'] else 1
    execute_db('UPDATE promo_codes SET is_active = ? WHERE id = ?', (new_value, promo_id))
    flash(f'Промокод {promo["code"]} {"увімкнено" if new_value else "вимкнено"}.')
    return redirect(url_for('orders.admin_promos'))


# ---------------------------------------------------------------------------
# ТИМЧАСОВО (для перевірки без частини А): наповнює кошик тестовими товарами.
# Працює лише в режимі debug. ВИДАЛІТЬ цей маршрут, коли кошик (частина А) буде готовий.
# ---------------------------------------------------------------------------

@bp.route('/dev/fill-cart')
def dev_fill_cart():
    if not current_app.debug:
        abort(404)
    session['cart'] = {'1': 2, '4': 1}
    flash('Тестовий кошик заповнено (тимчасовий маршрут).')
    return redirect(url_for('orders.checkout'))
