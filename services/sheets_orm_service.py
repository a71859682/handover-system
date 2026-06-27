from __future__ import annotations

from models import Floor, Sheet, Task, Unit


def list_sheets_orm():
    return Sheet.query.order_by(Sheet.sort_order, Sheet.id).all()


def get_sheet_orm(sheet_id):
    return Sheet.query.filter_by(id=sheet_id).first()


def list_tasks_for_sheet_orm(sheet_id):
    return Task.query.filter_by(sheet_id=sheet_id).order_by(Task.col_index).all()


def list_floors_for_sheet_orm(sheet_id):
    return Floor.query.filter_by(sheet_id=sheet_id).order_by(Floor.sort_order).all()


def list_units_for_floor_orm(floor_id):
    return Unit.query.filter_by(floor_id=floor_id).order_by(Unit.sort_order).all()
