from ..extensions import db


class Team(db.Model):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    type = db.Column(db.String(32), nullable=True)

    users = db.relationship("User", back_populates="team", lazy="dynamic")
    metric_definitions = db.relationship("MetricDefinition", back_populates="team", lazy="dynamic")
    scoped_metrics = db.relationship("MetricDefinition", secondary='metric_definition_teams', back_populates="scoped_teams")
    metric_categories = db.relationship("MetricCategory", secondary='metric_category_teams', back_populates="teams")
    metric_values = db.relationship("MetricValue", back_populates="team", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Team {self.name}>"

    @classmethod
    def get_or_create(cls, name: str, type: str | None = None) -> "Team":
        team = cls.query.filter_by(name=name).first()
        if team is not None:
            return team

        team = cls(name=name, type=type)
        db.session.add(team)
        db.session.commit()
        return team
