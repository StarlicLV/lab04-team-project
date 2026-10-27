"""Замовлення: оформлення з кошика, статуси, промокоди (рівень 3), адмінка.

Кошик читається з session['cart'] = {product_id: quantity}. Статуси — models.ORDER_STATUSES.
"""
from flask import Blueprint, render_template

bp = Blueprint('orders', __name__)


@bp.route('/checkout')
def checkout():
    return render_template('placeholder.html', title='Оформлення замовлення', owner='...')


@bp.route('/admin/orders')
def admin_orders():
    return render_template('admin/placeholder.html', title='Замовлення', owner='...')
