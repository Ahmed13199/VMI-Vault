import uuid

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from . import documents_bp
from ...extensions import db
from ...models.document_folder import DocumentFolder
from ...models.document import Document
from ...permissions import require_page_permission
from ...services.r2_service import R2Service


def _collect_folder_tree_ids(root_folder_id: int) -> list[int]:
    ids: list[int] = []
    stack: list[int] = [root_folder_id]

    while stack:
        current_id = stack.pop()
        ids.append(current_id)

        child_ids = [row[0] for row in db.session.query(DocumentFolder.id)
                     .filter(DocumentFolder.parent_id == current_id)
                     .all()]
        stack.extend(child_ids)

    return ids


@documents_bp.route('/')
@login_required
@require_page_permission('documents')
def index():
    folders = (DocumentFolder.query
               .filter(DocumentFolder.parent_id.is_(None))
               .order_by(DocumentFolder.name.asc())
               .all())

    return render_template('documents/index.html', current_folder=None, folders=folders, documents=[])


@documents_bp.route('/folder/<int:folder_id>')
@login_required
@require_page_permission('documents')
def folder(folder_id: int):
    current_folder = DocumentFolder.query.get_or_404(folder_id)

    folders = (DocumentFolder.query
               .filter(DocumentFolder.parent_id == current_folder.id)
               .order_by(DocumentFolder.name.asc())
               .all())

    documents = (Document.query
                 .filter(Document.folder_id == current_folder.id)
                 .order_by(Document.updated_at.desc())
                 .all())

    return render_template('documents/index.html', current_folder=current_folder, folders=folders, documents=documents)


@documents_bp.route('/folder/<int:folder_id>/delete', methods=['POST'])
@login_required
@require_page_permission('documents', 'edit')
def delete_folder(folder_id: int):
    folder_obj = DocumentFolder.query.get_or_404(folder_id)
    parent_id = folder_obj.parent_id

    folder_ids = _collect_folder_tree_ids(folder_obj.id)

    docs = Document.query.filter(Document.folder_id.in_(folder_ids)).all()
    for doc in docs:
        try:
            R2Service.delete_object(doc.storage_key)
        except Exception:
            pass

    Document.query.filter(Document.folder_id.in_(folder_ids)).delete(synchronize_session=False)
    DocumentFolder.query.filter(DocumentFolder.id.in_(folder_ids)).delete(synchronize_session=False)
    db.session.commit()

    flash('Folder deleted.', 'success')
    if parent_id:
        return redirect(url_for('documents.folder', folder_id=parent_id))
    return redirect(url_for('documents.index'))


@documents_bp.route('/folders/new', methods=['POST'])
@login_required
@require_page_permission('documents', 'edit')
def create_folder():
    name = (request.form.get('name') or '').strip()
    parent_id_raw = (request.form.get('parent_id') or '').strip() or None

    if not name:
        flash('Folder name is required.', 'error')
        return redirect(request.referrer or url_for('documents.index'))

    parent_id = int(parent_id_raw) if parent_id_raw else None

    folder = DocumentFolder(
        name=name,
        parent_id=parent_id,
        created_by_user_id=getattr(current_user, 'id', None)
    )

    db.session.add(folder)
    db.session.commit()

    flash('Folder created.', 'success')
    if parent_id:
        return redirect(url_for('documents.folder', folder_id=parent_id))
    return redirect(url_for('documents.index'))


@documents_bp.route('/upload', methods=['POST'])
@login_required
@require_page_permission('documents', 'edit')
def upload():
    file = request.files.get('file')
    title = (request.form.get('title') or '').strip()
    folder_id_raw = (request.form.get('folder_id') or '').strip() or None

    if not file or not file.filename:
        flash('Please choose a file to upload.', 'error')
        return redirect(request.referrer or url_for('documents.index'))

    if not folder_id_raw:
        flash('Please choose a folder to upload the document into.', 'error')
        return redirect(request.referrer or url_for('documents.index'))

    folder_id = int(folder_id_raw) if folder_id_raw else None

    DocumentFolder.query.get_or_404(folder_id)

    original_filename = secure_filename(file.filename)
    if not title:
        title = original_filename

    key = f"documents/{uuid.uuid4().hex}_{original_filename}"

    content_type = getattr(file, 'mimetype', None)
    R2Service.upload_fileobj(file, key, content_type=content_type)

    size_bytes = None
    try:
        size_bytes = file.content_length
    except Exception:
        size_bytes = None

    doc = Document(
        folder_id=folder_id,
        created_by_user_id=getattr(current_user, 'id', None),
        title=title,
        original_filename=original_filename,
        content_type=content_type,
        size_bytes=size_bytes,
        storage_key=key,
    )

    db.session.add(doc)
    db.session.commit()

    flash('Document uploaded.', 'success')
    if folder_id:
        return redirect(url_for('documents.folder', folder_id=folder_id))
    return redirect(url_for('documents.index'))


@documents_bp.route('/document/<int:document_id>/view')
@login_required
@require_page_permission('documents')
def view_document(document_id: int):
    doc = Document.query.get_or_404(document_id)
    url = R2Service.presigned_get_url(doc.storage_key, expires_in_seconds=600)
    return redirect(url)


@documents_bp.route('/document/<int:document_id>/delete', methods=['POST'])
@login_required
@require_page_permission('documents', 'edit')
def delete_document(document_id: int):
    doc = Document.query.get_or_404(document_id)

    folder_id = doc.folder_id

    try:
        R2Service.delete_object(doc.storage_key)
    except Exception:
        pass

    db.session.delete(doc)
    db.session.commit()

    flash('Document deleted.', 'success')
    if folder_id:
        return redirect(url_for('documents.folder', folder_id=folder_id))
    return redirect(url_for('documents.index'))
