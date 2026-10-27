"""Товари: сторінка меню з БД, пошук і фільтрація (рівень 3), керування товарами в адмінці.
"""
from flask import Blueprint, render_template

bp = Blueprint('shop', __name__)


@bp.route('/admin/products')
def admin_products():
    return render_template('admin/placeholder.html', title='Товари', owner='...')
