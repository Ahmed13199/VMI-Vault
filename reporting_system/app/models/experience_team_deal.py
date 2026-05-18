from ..extensions import db


class ExperienceTeamDeal(db.Model):
    __tablename__ = 'experience_team_deals'

    id = db.Column(db.BigInteger, primary_key=True)

    deal_name = db.Column(db.String(255), nullable=False)
    client_name = db.Column(db.String(255), nullable=True)

    step_type = db.Column(db.String(20), nullable=False)

    client_paid_so_far = db.Column(db.Numeric(12, 2), nullable=False, server_default='0')
    step_cost = db.Column(db.Numeric(12, 2), nullable=False, server_default='0')

    acceptance_status = db.Column(db.String(20), nullable=False, server_default='pending', index=True)
    accepted_at = db.Column(db.DateTime(timezone=True), nullable=True)

    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<ExperienceTeamDeal {self.id}:{self.deal_name}>"
