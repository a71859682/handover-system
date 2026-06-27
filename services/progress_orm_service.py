from __future__ import annotations

from models import ExtraField, Floor, Progress, Unit, UnitExtra, UnitExtraValue


def list_progress_orm():
    return Progress.query.order_by(Progress.unit_id, Progress.task_id).all()


def list_unit_extra_orm():
    return UnitExtra.query.order_by(UnitExtra.unit_id).all()


def list_extra_fields_for_sheet_orm(sheet_id):
    return ExtraField.query.filter_by(sheet_id=sheet_id).order_by(ExtraField.sort_order, ExtraField.id).all()


def list_unit_extra_values_for_sheet_orm(sheet_id):
    return (
        UnitExtraValue.query.join(Unit, Unit.id == UnitExtraValue.unit_id)
        .join(Floor, Floor.id == Unit.floor_id)
        .filter(Floor.sheet_id == sheet_id)
        .order_by(UnitExtraValue.unit_id, UnitExtraValue.field_key)
        .all()
    )
