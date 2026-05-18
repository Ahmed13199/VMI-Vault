from datetime import datetime

from ..extensions import db


class JournalTable(db.Model):
    __tablename__ = 'journal_tables'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    rows = db.relationship('JournalTableRow', back_populates='table', cascade='all, delete-orphan', order_by='JournalTableRow.position')
    columns = db.relationship('JournalTableColumn', back_populates='table', cascade='all, delete-orphan', order_by='JournalTableColumn.position')
    cells = db.relationship('JournalTableCell', back_populates='table', cascade='all, delete-orphan')


class JournalTableRow(db.Model):
    __tablename__ = 'journal_table_rows'

    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('journal_tables.id'), nullable=False, index=True)
    position = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    table = db.relationship('JournalTable', back_populates='rows')

    __table_args__ = (
        db.UniqueConstraint('table_id', 'position', name='uq_journal_rows_table_position'),
    )


class JournalTableColumn(db.Model):
    __tablename__ = 'journal_table_columns'

    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('journal_tables.id'), nullable=False, index=True)
    position = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    table = db.relationship('JournalTable', back_populates='columns')

    __table_args__ = (
        db.UniqueConstraint('table_id', 'position', name='uq_journal_cols_table_position'),
    )


class JournalTableCell(db.Model):
    __tablename__ = 'journal_table_cells'

    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('journal_tables.id'), nullable=False, index=True)
    row_id = db.Column(db.Integer, db.ForeignKey('journal_table_rows.id'), nullable=False)
    column_id = db.Column(db.Integer, db.ForeignKey('journal_table_columns.id'), nullable=False)

    value_text = db.Column(db.Text, nullable=True)
    value_number = db.Column(db.Numeric(18, 4), nullable=True)

    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    table = db.relationship('JournalTable', back_populates='cells')
    row = db.relationship('JournalTableRow')
    column = db.relationship('JournalTableColumn')

    __table_args__ = (
        db.UniqueConstraint('table_id', 'row_id', 'column_id', name='uq_journal_cells_unique'),
        db.CheckConstraint('(value_text IS NULL) OR (value_number IS NULL)', name='ck_journal_cell_one_type'),
    )
