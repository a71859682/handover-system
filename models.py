from database import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text, nullable=False, unique=True)
    display_name = db.Column(db.Text)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.Text, nullable=False, default="member", server_default="member")
    created_at = db.Column(db.Text, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"))


class Sheet(db.Model):
    __tablename__ = "sheets"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    created_at = db.Column(db.Text, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"))


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    sheet_id = db.Column(db.Integer, db.ForeignKey("sheets.id"))
    col_index = db.Column(db.Integer, nullable=False, unique=True)
    vendor = db.Column(db.Text)
    location = db.Column(db.Text)
    name = db.Column(db.Text, nullable=False)


class Floor(db.Model):
    __tablename__ = "floors"

    id = db.Column(db.Integer, primary_key=True)
    sheet_id = db.Column(db.Integer, db.ForeignKey("sheets.id"))
    sort_order = db.Column(db.Integer, nullable=False, unique=True)
    name = db.Column(db.Text, nullable=False)
    block_name = db.Column(db.Text)
    unit_count = db.Column(db.Integer, nullable=False)


class Unit(db.Model):
    __tablename__ = "units"

    id = db.Column(db.Integer, primary_key=True)
    floor_id = db.Column(db.Integer, db.ForeignKey("floors.id"), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False)
    name = db.Column(db.Text, nullable=False)


class Progress(db.Model):
    __tablename__ = "progress"

    unit_id = db.Column(db.Integer, db.ForeignKey("units.id"), primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), primary_key=True)
    value = db.Column(db.Text, nullable=False, default="X", server_default="X")
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column(db.Text, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"))


class UnitExtra(db.Model):
    __tablename__ = "unit_extra"

    unit_id = db.Column(db.Integer, db.ForeignKey("units.id"), primary_key=True)
    initial_check = db.Column(db.Text, nullable=False, default="", server_default="")
    recheck_1 = db.Column(db.Text, nullable=False, default="", server_default="")
    recheck_2 = db.Column(db.Text, nullable=False, default="", server_default="")
    handover = db.Column(db.Text, nullable=False, default="X", server_default="X")
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column(db.Text, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"))


class ExtraField(db.Model):
    __tablename__ = "extra_fields"
    __table_args__ = (
        db.UniqueConstraint("sheet_id", "field_key", name="uq_extra_fields_sheet_field_key"),
    )

    id = db.Column(db.Integer, primary_key=True)
    sheet_id = db.Column(db.Integer, db.ForeignKey("sheets.id"), nullable=False)
    field_key = db.Column(db.Text, nullable=False)
    name = db.Column(db.Text, nullable=False)
    field_type = db.Column(db.Text, nullable=False, default="date", server_default="date")
    sort_order = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    is_builtin = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    active = db.Column(db.Integer, nullable=False, default=1, server_default="1")


class UnitExtraValue(db.Model):
    __tablename__ = "unit_extra_values"

    unit_id = db.Column(db.Integer, db.ForeignKey("units.id"), primary_key=True)
    field_key = db.Column(db.Text, primary_key=True)
    value = db.Column(db.Text, nullable=False, default="", server_default="")
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column(db.Text, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"))


class Meta(db.Model):
    __tablename__ = "meta"

    key = db.Column(db.Text, primary_key=True)
    value = db.Column(db.Text, nullable=False)
