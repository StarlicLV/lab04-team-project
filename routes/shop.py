"""Товари (Кубський): сторінка меню з БД, пошук і фільтрація (рівень 3), керування товарами в адмінці.

TODO: замініть заглушку. Товар, який є в замовленнях, видалити не можна (RESTRICT) —
вимикайте його через is_available = 0.
"""
from flask import Blueprint, render_template

bp = Blueprint('shop', __name__)


@bp.route('/admin/products')
def admin_products():
    return render_template('admin/placeholder.html', title='Товари', owner='Кубський')
