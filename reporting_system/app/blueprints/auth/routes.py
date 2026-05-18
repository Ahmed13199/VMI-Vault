"""
Authentication routes: login and logout.
"""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from . import auth_bp
from ...services.access_service import AccessService
from ...services.auth_service import AuthService


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login.
    
    GET: Display login form
    POST: Process login credentials
    """
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for(AccessService.first_accessible_route(current_user)))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False) == 'on'
        
        # Validate input
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('auth/login.html')
        
        # Authenticate user
        user = AuthService.authenticate(username, password)
        
        if user:
            AuthService.login(user, remember=remember)
            flash(f'Welcome back, {user.username}!', 'success')
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for(AccessService.first_accessible_route(user)))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """
    Handle user logout.
    """
    AuthService.logout()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
