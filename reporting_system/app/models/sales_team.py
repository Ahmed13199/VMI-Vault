from datetime import datetime

from ..extensions import db


class SalesGuidelinePartition(db.Model):
    __tablename__ = 'sales_guideline_partitions'

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    position = db.Column(db.Integer, nullable=False, default=1)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    team = db.relationship('Team')
    created_by_user = db.relationship('User')
    sections = db.relationship(
        'SalesGuidelineSection',
        back_populates='partition',
        cascade='all, delete-orphan',
        order_by='SalesGuidelineSection.position.asc()'
    )
    resources = db.relationship(
        'SalesGuidelineResource',
        back_populates='partition',
        cascade='all, delete-orphan',
        order_by='SalesGuidelineResource.created_at.desc()'
    )


class SalesGuidelineSection(db.Model):
    __tablename__ = 'sales_guideline_sections'

    id = db.Column(db.Integer, primary_key=True)
    partition_id = db.Column(db.Integer, db.ForeignKey('sales_guideline_partitions.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    position = db.Column(db.Integer, nullable=False, default=1)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    partition = db.relationship('SalesGuidelinePartition', back_populates='sections')
    created_by_user = db.relationship('User')
    subsections = db.relationship(
        'SalesGuidelineSubsection',
        back_populates='section',
        cascade='all, delete-orphan',
        order_by='SalesGuidelineSubsection.position.asc()'
    )
    resources = db.relationship(
        'SalesGuidelineResource',
        back_populates='section',
        cascade='all, delete-orphan',
        order_by='SalesGuidelineResource.created_at.desc()'
    )


class SalesGuidelineSubsection(db.Model):
    __tablename__ = 'sales_guideline_subsections'

    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('sales_guideline_sections.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    position = db.Column(db.Integer, nullable=False, default=1)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    section = db.relationship('SalesGuidelineSection', back_populates='subsections')
    created_by_user = db.relationship('User')
    resources = db.relationship(
        'SalesGuidelineResource',
        back_populates='subsection',
        cascade='all, delete-orphan',
        order_by='SalesGuidelineResource.created_at.desc()'
    )


class SalesGuidelineResource(db.Model):
    __tablename__ = 'sales_guideline_resources'

    id = db.Column(db.Integer, primary_key=True)
    partition_id = db.Column(db.Integer, db.ForeignKey('sales_guideline_partitions.id'), nullable=True, index=True)
    section_id = db.Column(db.Integer, db.ForeignKey('sales_guideline_sections.id'), nullable=True, index=True)
    subsection_id = db.Column(db.Integer, db.ForeignKey('sales_guideline_subsections.id'), nullable=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    resource_type = db.Column(db.String(16), nullable=False, default='link')
    url = db.Column(db.String(1000), nullable=True)
    storage_key = db.Column(db.String(700), nullable=True, unique=True, index=True)
    original_filename = db.Column(db.String(500), nullable=True)
    content_type = db.Column(db.String(200), nullable=True)
    size_bytes = db.Column(db.BigInteger, nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.CheckConstraint("resource_type IN ('file', 'link')", name='ck_sales_guideline_resource_type'),
        db.CheckConstraint(
            "((partition_id IS NOT NULL)::integer + (section_id IS NOT NULL)::integer + (subsection_id IS NOT NULL)::integer) = 1",
            name='ck_sales_guideline_resource_single_parent'
        ),
    )

    partition = db.relationship('SalesGuidelinePartition', back_populates='resources')
    section = db.relationship('SalesGuidelineSection', back_populates='resources')
    subsection = db.relationship('SalesGuidelineSubsection', back_populates='resources')
    created_by_user = db.relationship('User')

    @property
    def owner_team_id(self):
        if self.partition is not None:
            return self.partition.team_id
        if self.section is not None:
            return self.section.partition.team_id
        if self.subsection is not None:
            return self.subsection.section.partition.team_id
        return None

    @property
    def owner_level(self):
        if self.partition_id is not None:
            return 'partition'
        if self.section_id is not None:
            return 'section'
        if self.subsection_id is not None:
            return 'subsection'
        return None
