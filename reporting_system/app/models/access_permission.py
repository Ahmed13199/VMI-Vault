"""
Per-page access permissions by rank.
"""
from ..extensions import db


class AccessPermission(db.Model):
    """Stores view/edit permissions for a page and rank."""

    __tablename__ = 'access_permissions'
    __table_args__ = (
        db.UniqueConstraint('page_key', 'rank', name='uq_access_permissions_page_rank'),
    )

    id = db.Column(db.Integer, primary_key=True)
    page_key = db.Column(db.String(64), nullable=False, index=True)
    page_name = db.Column(db.String(128), nullable=False)
    rank = db.Column(db.String(32), nullable=False, index=True)
    can_view = db.Column(db.Boolean, nullable=False, default=False)
    can_edit = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f'<AccessPermission page={self.page_key} rank={self.rank}>'
