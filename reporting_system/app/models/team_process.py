from ..extensions import db


class TeamProcess(db.Model):
    __tablename__ = 'team_processes'

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False, index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)

    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(32), nullable=False, default='draft')

    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now(), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('team_id', 'slug', name='uq_team_process_team_slug'),
    )

    team = db.relationship('Team')
    created_by_user = db.relationship('User')
    sections = db.relationship(
        'TeamProcessSection',
        back_populates='process',
        cascade='all, delete-orphan',
        order_by='TeamProcessSection.position.asc()'
    )

    def __repr__(self) -> str:
        return f"<TeamProcess {self.team_id}:{self.slug}>"


class TeamProcessSection(db.Model):
    __tablename__ = 'team_process_sections'

    id = db.Column(db.Integer, primary_key=True)
    process_id = db.Column(db.Integer, db.ForeignKey('team_processes.id'), nullable=False, index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)

    position = db.Column(db.Integer, nullable=False, default=0)
    section_type = db.Column(db.String(32), nullable=False, default='paragraph')
    text_align = db.Column(db.String(16), nullable=False, default='left')
    title = db.Column(db.String(200), nullable=True)
    title_html = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now(), nullable=False)

    process = db.relationship('TeamProcess', back_populates='sections')
    created_by_user = db.relationship('User')

    def __repr__(self) -> str:
        return f"<TeamProcessSection {self.process_id}:{self.position}:{self.section_type}>"
