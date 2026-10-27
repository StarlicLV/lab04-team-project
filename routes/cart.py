"""Кошик. Формат у сесії: session['cart'] = {product_id: quantity}.
"""
from flask import Blueprint, render_template

bp = Blueprint('cart', __name__)


@bp.route('/cart')
def view_cart():
    return render_template('placeholder.html', title='Кошик', owner='...')
