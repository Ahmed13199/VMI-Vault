"""
Application-level settings.
"""
from ..extensions import db


class AppSetting(db.Model):
    """Small key/value store for site-wide feature switches."""

    __tablename__ = 'app_settings'

    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Text, nullable=True)

    @classmethod
    def get_value(cls, key, default=None):
        setting = cls.query.get(key)
        if setting is None or setting.value in (None, ''):
            return default
        return setting.value

    @classmethod
    def set_value(cls, key, value):
        setting = cls.query.get(key)
        if setting is None:
            setting = cls(key=key)
        setting.value = str(value) if value not in (None, '') else None
        db.session.add(setting)
        db.session.commit()
        return setting
