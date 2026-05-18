"""
User model for authentication and authorization.
"""
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db


class User(UserMixin, db.Model):
    """
    User model representing system users.
    
    Attributes:
        id: Primary key
        username: Unique username for login
        password_hash: Securely hashed password (never store plain text)
        role: User role / department identity
        rank: User authority level
        team_id: Optional foreign key to Team
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(64), nullable=True)
    last_name = db.Column(db.String(64), nullable=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(32), nullable=False, default='support')
    rank = db.Column(db.String(32), nullable=False, default='agent')
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    
    # Relationships
    team = db.relationship('Team', back_populates='users')
    
    # Valid roles
    ROLES = ['support', 'sales', 'engineering', 'admin']
    RANKS = ['agent', 'senior', 'team_leader', 'admin']
    RANK_LABELS = {
        'agent': 'Agent',
        'senior': 'Senior',
        'team_leader': 'Team Leader',
        'admin': 'Admin',
    }
    
    def __repr__(self):
        return f'<User {self.username}>'

    @property
    def full_name(self):
        """Return the user's full name when available."""
        parts = [part for part in [self.first_name, self.last_name] if part]
        return ' '.join(parts) if parts else self.username
    
    def set_password(self, password):
        """
        Hash and set the user's password.
        
        Args:
            password: Plain text password to hash
        """
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """
        Verify a password against the stored hash.
        
        Args:
            password: Plain text password to verify
            
        Returns:
            True if password matches, False otherwise
        """
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if user has admin rank."""
        return self.effective_rank() == 'admin'

    def effective_rank(self):
        """Return a normalized rank, keeping legacy admin users working."""
        rank = (self.rank or '').strip().lower()
        if rank in self.RANKS:
            return rank
        if (self.role or '').strip().lower() == 'admin':
            return 'admin'
        return 'agent'

    def display_rank(self):
        """Return a display-friendly rank label."""
        return self.RANK_LABELS.get(self.effective_rank(), 'Agent')

    def can_access_page(self, page_key):
        """Check view permission for a page."""
        from ..services.access_service import AccessService
        return AccessService.can_access_page(self, page_key, 'view')

    def can_edit_page(self, page_key):
        """Check edit permission for a page."""
        from ..services.access_service import AccessService
        return AccessService.can_access_page(self, page_key, 'edit')
    
    @classmethod
    def create_user(cls, username, password, role='support', team_id=None, rank='agent',
                    first_name=None, last_name=None):
        """
        Factory method to create a new user with hashed password.
        
        Args:
            username: Unique username
            password: Plain text password (will be hashed)
            role: User role
            team_id: Optional team ID
            rank: User authority rank
            first_name: User first name
            last_name: User last name
            
        Returns:
            New User instance (not yet committed to database)
        """
        user = cls(
            username=username,
            first_name=(first_name or '').strip() or None,
            last_name=(last_name or '').strip() or None,
            role=role,
            rank=rank,
            team_id=team_id,
        )
        user.set_password(password)
        return user
