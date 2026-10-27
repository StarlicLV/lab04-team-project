"""Відгуки (Марчук): форма для відвідувачів + перегляд і видалення в адмінці.

TODO: замініть заглушки справжньою реалізацією, ЗБЕРІГАЮЧИ імена функцій (endpoint),
бо на них посилаються base.html та base_admin.html.
"""
from flask import Blueprint, render_template

bp = Blueprint('feedback', __name__)


@bp.route('/feedback')
def feedback_form():
    return render_template('placeholder.html', title='Зворотний зв’язок', owner='Марчук')


@bp.route('/admin/feedback')
def admin_list():
    return render_template('admin/placeholder.html', title='Відгуки', owner='Марчук')
