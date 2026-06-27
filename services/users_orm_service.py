from __future__ import annotations

from models import User


def get_user_by_username_orm(username):
    return User.query.filter_by(username=username).first()


def get_user_by_id_orm(user_id):
    return User.query.filter_by(id=user_id).first()


def list_users_orm():
    return User.query.order_by(User.id).all()
