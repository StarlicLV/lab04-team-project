"""Кошик (Марчук). Формат у сесії: session['cart'] = {product_id: quantity}.

TODO: додавання товару, зміна кількості, видалення, сторінка кошика.
"""
from flask import Blueprint, render_template

bp = Blueprint('cart', __name__)


@bp.route('/cart')
def view_cart():
    return render_template('placeholder.html', title='Кошик', owner='Марчук')
