from ..extensions import db


class Document(db.Model):
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)

    folder_id = db.Column(db.Integer, db.ForeignKey('document_folders.id'), nullable=True, index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)

    title = db.Column(db.String(200), nullable=False)
    original_filename = db.Column(db.String(500), nullable=False)
    content_type = db.Column(db.String(200), nullable=True)
    size_bytes = db.Column(db.BigInteger, nullable=True)

    storage_key = db.Column(db.String(700), nullable=False, unique=True, index=True)

    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now(), nullable=False)

    folder = db.relationship('DocumentFolder')
    created_by_user = db.relationship('User')

    def __repr__(self) -> str:
        return f"<Document {self.id}:{self.storage_key}>"
