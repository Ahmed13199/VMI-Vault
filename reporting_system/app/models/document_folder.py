from ..extensions import db


class DocumentFolder(db.Model):
    __tablename__ = 'document_folders'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)

    parent_id = db.Column(db.Integer, db.ForeignKey('document_folders.id'), nullable=True, index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)

    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now(), nullable=False)

    parent = db.relationship('DocumentFolder', remote_side=[id])
    created_by_user = db.relationship('User')

    def __repr__(self) -> str:
        return f"<DocumentFolder {self.id}:{self.name}>"
