"""
Authentication service for user login/logout operations.
"""
from flask_login import login_user, logout_user
from ..models.user import User
from ..extensions import db


class AuthService:
    """Service class for authentication operations."""
    
    @staticmethod
    def authenticate(username, password):
        """
        Authenticate a user with username and password.
        
        Args:
            username: User's username
            password: Plain text password
            
        Returns:
            User instance if authentication successful, None otherwise
        """
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            return user
        return None
    
    @staticmethod
    def login(user, remember=False):
        """
        Log in a user and create a session.
        
        Args:
            user: User instance to log in
            remember: Whether to remember the user
            
        Returns:
            True if login successful
        """
        return login_user(user, remember=remember)
    
    @staticmethod
    def logout():
        """
        Log out the current user.
        
        Returns:
            True if logout successful
        """
        return logout_user()
    
    @staticmethod
    def create_user(username, password, role='support', team_id=None, rank='agent',
                    first_name=None, last_name=None):
        """
        Create a new user with hashed password.
        
        Args:
            username: Unique username
            password: Plain text password (will be hashed)
            role: User role
            team_id: Optional team ID
            rank: User rank
            first_name: User first name
            last_name: User last name
            
        Returns:
            New User instance
        """
        user = User.create_user(
            username,
            password,
            role,
            team_id,
            rank,
            first_name=first_name,
            last_name=last_name,
        )
        db.session.add(user)
        db.session.commit()
        return user
    
    @staticmethod
    def get_user_by_id(user_id):
        """
        Get a user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User instance or None
        """
        return User.query.get(user_id)
    
    @staticmethod
    def get_user_by_username(username):
        """
        Get a user by username.
        
        Args:
            username: Username to search for
            
        Returns:
            User instance or None
        """
        return User.query.filter_by(username=username).first()
