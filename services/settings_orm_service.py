from __future__ import annotations

from models import Meta


def get_setting_orm(key, default=None):
    row = Meta.query.filter_by(key=key).first()
    return row.value if row else default


def get_settings_orm(default_settings):
    settings = dict(default_settings)
    rows = Meta.query.all()
    for row in rows:
        if row.key in settings:
            settings[row.key] = row.value
    return settings
