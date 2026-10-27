"""Відгуки): форма для відвідувачів + перегляд і видалення в адмінці.
"""
from flask import Blueprint, render_template

bp = Blueprint('feedback', __name__)


@bp.route('/feedback')
def feedback_form():
    return render_template('placeholder.html', title='Зворотний зв’язок', owner='...')


@bp.route('/admin/feedback')
def admin_list():
    return render_template('admin/placeholder.html', title='Відгуки', owner='...')
