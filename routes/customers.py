"""Клієнти (рівень 2): CRUD у адмін-панелі."""
from flask import Blueprint, render_template

bp = Blueprint('customers', __name__)


@bp.route('/admin/customers')
def admin_customers():
    return render_template('admin/placeholder.html', title='Клієнти', owner='...')
