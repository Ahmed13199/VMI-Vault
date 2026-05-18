from decimal import Decimal, InvalidOperation

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from flask_login import current_user

from . import journal_bp
from ...extensions import db
from ...models.journal import JournalTable, JournalTableRow, JournalTableColumn, JournalTableCell
from ...permissions import require_page_permission
from ...services.access_service import AccessService


@journal_bp.route('/')
@login_required
@require_page_permission('journal')
def index():
    tables = JournalTable.query.order_by(JournalTable.updated_at.desc(), JournalTable.created_at.desc()).all()
    return render_template('journal/index.html', tables=tables)


@journal_bp.route('/tables/new', methods=['GET', 'POST'])
@login_required
@require_page_permission('journal', 'edit')
def create_table():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        rows = request.form.get('rows', type=int)
        cols = request.form.get('cols', type=int)

        if not name:
            flash('Table name is required.', 'error')
            return render_template('journal/create_table.html')

        if rows is None or cols is None or rows < 1 or cols < 1:
            flash('Rows and columns must be at least 1.', 'error')
            return render_template('journal/create_table.html')

        if rows > 50 or cols > 20:
            flash('Please keep tables at 50 rows and 20 columns or less for performance.', 'error')
            return render_template('journal/create_table.html')

        table = JournalTable(name=name, created_by_user_id=getattr(current_user, 'id', None))
        db.session.add(table)
        db.session.flush()

        for i in range(1, rows + 1):
            db.session.add(JournalTableRow(table_id=table.id, position=i, name=f'Row {i}'))

        for j in range(1, cols + 1):
            db.session.add(JournalTableColumn(table_id=table.id, position=j, name=f'Col {j}'))

        db.session.commit()
        return redirect(url_for('journal.edit_table', table_id=table.id))

    return render_template('journal/create_table.html')


@journal_bp.route('/tables/<int:table_id>', methods=['GET', 'POST'])
@login_required
@require_page_permission('journal')
def edit_table(table_id: int):
    table = JournalTable.query.get_or_404(table_id)
    rows = JournalTableRow.query.filter_by(table_id=table.id).order_by(JournalTableRow.position.asc()).all()
    cols = JournalTableColumn.query.filter_by(table_id=table.id).order_by(JournalTableColumn.position.asc()).all()

    if request.method == 'POST':
        if not AccessService.can_access_page(current_user, 'journal', 'edit'):
            return AccessService.deny_access('edit')
        action = request.form.get('action', 'save')
        if action == 'add_row':
            next_pos = (rows[-1].position if rows else 0) + 1
            db.session.add(JournalTableRow(table_id=table.id, position=next_pos, name=f'Row {next_pos}'))
            db.session.commit()
            flash('Row added.', 'success')
            return redirect(url_for('journal.edit_table', table_id=table.id))

        if action == 'add_col':
            next_pos = (cols[-1].position if cols else 0) + 1
            db.session.add(JournalTableColumn(table_id=table.id, position=next_pos, name=f'Col {next_pos}'))
            db.session.commit()
            flash('Column added.', 'success')
            return redirect(url_for('journal.edit_table', table_id=table.id))

        if action == 'save':
            table_name = (request.form.get('table_name') or '').strip()
            if table_name:
                table.name = table_name

            for r in rows:
                r_name = (request.form.get(f'row_name_{r.id}') or '').strip()
                if r_name:
                    r.name = r_name

            for c in cols:
                c_name = (request.form.get(f'col_name_{c.id}') or '').strip()
                if c_name:
                    c.name = c_name

            for r in rows:
                for c in cols:
                    field = f'cell_{r.id}_{c.id}'
                    raw = request.form.get(field)
                    if raw is None:
                        continue
                    raw = raw.strip()

                    cell = JournalTableCell.query.filter_by(table_id=table.id, row_id=r.id, column_id=c.id).first()

                    if raw == '':
                        if cell is not None:
                            cell.value_text = None
                            cell.value_number = None
                        continue

                    value_number = None
                    value_text = None
                    try:
                        value_number = Decimal(raw)
                    except (InvalidOperation, ValueError):
                        value_text = raw

                    if cell is None:
                        cell = JournalTableCell(table_id=table.id, row_id=r.id, column_id=c.id)
                        db.session.add(cell)

                    cell.value_number = value_number
                    cell.value_text = value_text

            db.session.add(table)
            db.session.commit()
            flash('Saved.', 'success')
            return redirect(url_for('journal.edit_table', table_id=table.id))

    cells = JournalTableCell.query.filter_by(table_id=table.id).all()
    cell_map = {(c.row_id, c.column_id): c for c in cells}

    return render_template(
        'journal/edit_table.html',
        table=table,
        rows=rows,
        cols=cols,
        cell_map=cell_map,
    )


@journal_bp.route('/tables/<int:table_id>/delete', methods=['POST'])
@login_required
@require_page_permission('journal', 'edit')
def delete_table(table_id: int):
    table = JournalTable.query.get_or_404(table_id)
    db.session.delete(table)
    db.session.commit()
    flash('Table deleted.', 'success')
    return redirect(url_for('journal.index'))
