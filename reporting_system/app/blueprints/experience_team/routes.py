from decimal import Decimal, InvalidOperation

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required

from . import experience_team_bp
from ...extensions import db
from ...models.experience_team_deal import ExperienceTeamDeal
from ...permissions import require_page_permission


@experience_team_bp.route('/')
@login_required
@require_page_permission('experience_team')
def index():
    deals = ExperienceTeamDeal.query.order_by(ExperienceTeamDeal.created_at.desc()).all()
    return render_template('experience_team/index.html', deals=deals)


def _parse_money(value: str | None) -> Decimal:
    raw = (value or '').strip()
    if raw == '':
        return Decimal('0')
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        raise ValueError('Invalid money value.')


def _validate_step_type(value: str | None) -> str:
    step = (value or '').strip().lower()
    if step not in ('engineering', 'fabrication'):
        raise ValueError('Step type must be engineering or fabrication.')
    return step


@experience_team_bp.route('/deals/new', methods=['GET', 'POST'])
@login_required
@require_page_permission('experience_team', 'edit')
def create_deal():
    if request.method == 'POST':
        deal_name = (request.form.get('deal_name') or '').strip()
        client_name = (request.form.get('client_name') or '').strip() or None
        notes = (request.form.get('notes') or '').strip() or None

        try:
            if not deal_name:
                raise ValueError('Deal name is required.')

            step_type = _validate_step_type(request.form.get('step_type'))
            client_paid_so_far = _parse_money(request.form.get('client_paid_so_far'))
            step_cost = _parse_money(request.form.get('step_cost'))

            if client_paid_so_far < 0 or step_cost < 0:
                raise ValueError('Money values cannot be negative.')

            deal = ExperienceTeamDeal(
                deal_name=deal_name,
                client_name=client_name,
                step_type=step_type,
                client_paid_so_far=client_paid_so_far,
                step_cost=step_cost,
                acceptance_status='pending',
                notes=notes,
            )
            db.session.add(deal)
            db.session.commit()

            flash('Deal created.', 'success')
            return redirect(url_for('experience_team.index'))
        except Exception as e:
            flash(str(e), 'error')
            return render_template('experience_team/deal_form.html', deal=None, form_data=request.form)

    return render_template('experience_team/deal_form.html', deal=None, form_data={})


@experience_team_bp.route('/deals/<int:deal_id>/edit', methods=['GET', 'POST'])
@login_required
@require_page_permission('experience_team', 'edit')
def edit_deal(deal_id: int):
    deal = ExperienceTeamDeal.query.get_or_404(deal_id)

    if request.method == 'POST':
        deal_name = (request.form.get('deal_name') or '').strip()
        client_name = (request.form.get('client_name') or '').strip() or None
        notes = (request.form.get('notes') or '').strip() or None

        try:
            if not deal_name:
                raise ValueError('Deal name is required.')

            step_type = _validate_step_type(request.form.get('step_type'))
            client_paid_so_far = _parse_money(request.form.get('client_paid_so_far'))
            step_cost = _parse_money(request.form.get('step_cost'))

            if client_paid_so_far < 0 or step_cost < 0:
                raise ValueError('Money values cannot be negative.')

            deal.deal_name = deal_name
            deal.client_name = client_name
            deal.step_type = step_type
            deal.client_paid_so_far = client_paid_so_far
            deal.step_cost = step_cost
            deal.notes = notes

            db.session.commit()

            flash('Deal updated.', 'success')
            return redirect(url_for('experience_team.index'))
        except Exception as e:
            flash(str(e), 'error')
            return render_template('experience_team/deal_form.html', deal=deal, form_data=request.form)

    return render_template('experience_team/deal_form.html', deal=deal, form_data={
        'deal_name': deal.deal_name,
        'client_name': deal.client_name or '',
        'step_type': deal.step_type,
        'client_paid_so_far': str(deal.client_paid_so_far) if deal.client_paid_so_far is not None else '0',
        'step_cost': str(deal.step_cost) if deal.step_cost is not None else '0',
        'notes': deal.notes or ''
    })


@experience_team_bp.route('/deals/<int:deal_id>/delete', methods=['POST'])
@login_required
@require_page_permission('experience_team', 'edit')
def delete_deal(deal_id: int):
    deal = ExperienceTeamDeal.query.get_or_404(deal_id)
    db.session.delete(deal)
    db.session.commit()
    flash('Deal deleted.', 'success')
    return redirect(url_for('experience_team.index'))


@experience_team_bp.route('/deals/<int:deal_id>/accept', methods=['POST'])
@login_required
@require_page_permission('experience_team', 'edit')
def accept_deal(deal_id: int):
    deal = ExperienceTeamDeal.query.get_or_404(deal_id)
    if (deal.acceptance_status or 'pending') != 'accepted':
        deal.acceptance_status = 'accepted'
        deal.accepted_at = db.func.now()
        db.session.commit()
        flash('Deal marked as accepted.', 'success')
    return redirect(url_for('experience_team.index'))
