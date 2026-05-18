"""
Access control service for rank-based page permissions.
"""
from flask import flash, redirect, request, url_for
from ..extensions import db
from ..models.access_permission import AccessPermission


class AccessService:
    """Rank-aware access control for page visibility and editing."""

    PAGE_DEFINITIONS = [
        {
            'key': 'dashboard',
            'name': 'Dashboard',
            'description': 'Main KPI dashboard and executive overview.',
            'route': 'dashboard.index',
            'group': 'Core',
        },
        {
            'key': 'framework',
            'name': 'Framework',
            'description': 'Framework landing page and quick navigation.',
            'route': 'framework.index',
            'group': 'Knowledge Base',
        },
        {
            'key': 'team_processes',
            'name': 'Team Processes',
            'description': 'Process library, process details, and process editing.',
            'route': 'team_processes.index',
            'group': 'Knowledge Base',
        },
        {
            'key': 'documents',
            'name': 'Documents',
            'description': 'Document library, folders, uploads, and file deletion.',
            'route': 'documents.index',
            'group': 'Knowledge Base',
        },
        {
            'key': 'experience_team',
            'name': 'Experience Team',
            'description': 'Experience team deal board and acceptance flow.',
            'route': 'experience_team.index',
            'group': 'Operations',
        },
        {
            'key': 'sales_team',
            'name': 'Team Guidelines',
            'description': 'Team knowledge tabs, grouped guidelines, links, files, and structure edits.',
            'route': 'sales_team.guidelines',
            'group': 'Operations',
        },
        {
            'key': 'settings',
            'name': 'Metric Settings',
            'description': 'Metric definitions, categories, formulas, and graph settings.',
            'route': 'settings.index',
            'group': 'Configuration',
        },
        {
            'key': 'reporting_input',
            'name': 'Data Entry',
            'description': 'Reporting period input and target/value submission.',
            'route': 'reporting.input',
            'group': 'Reporting',
        },
        {
            'key': 'reporting_output',
            'name': 'Results',
            'description': 'Calculated reporting results and historical comparisons.',
            'route': 'reporting.output',
            'group': 'Reporting',
        },
        {
            'key': 'journal',
            'name': 'Journal',
            'description': 'Journal tables, rows, columns, and cell updates.',
            'route': 'journal.index',
            'group': 'Operations',
        },
        {
            'key': 'permissions',
            'name': 'Access Control',
            'description': 'Admin-only control center for page access by rank.',
            'route': 'settings.access_control',
            'group': 'Configuration',
        },
        {
            'key': 'user_management',
            'name': 'User Management',
            'description': 'Admin-only creation of internal users and identity details.',
            'route': 'settings.index',
            'group': 'Configuration',
        },
        {
            'key': 'team_management',
            'name': 'Team Management',
            'description': 'Admin-only team creation and reassignment support.',
            'route': 'settings.index',
            'group': 'Configuration',
        },
    ]

    RANKS = ['team_leader', 'senior', 'agent', 'admin']
    MANAGED_RANKS = ['team_leader', 'senior', 'agent']

    @classmethod
    def _definition_map(cls):
        return {page['key']: page for page in cls.PAGE_DEFINITIONS}

    @classmethod
    def get_page_definition(cls, page_key):
        return cls._definition_map().get(page_key)

    @classmethod
    def default_permission(cls, page_key, rank):
        if rank == 'admin':
            return {'can_view': True, 'can_edit': True}
        if page_key in {'permissions', 'user_management', 'team_management'}:
            return {'can_view': False, 'can_edit': False}

        edit_enabled_pages = {
            'team_processes',
            'documents',
            'experience_team',
            'sales_team',
            'settings',
            'reporting_input',
            'journal',
        }
        return {
            'can_view': True,
            'can_edit': page_key in edit_enabled_pages,
        }

    @classmethod
    def ensure_defaults_exist(cls):
        existing = {
            (row.page_key, row.rank): row
            for row in AccessPermission.query.all()
        }
        created = False

        for page in cls.PAGE_DEFINITIONS:
            for rank in cls.RANKS:
                key = (page['key'], rank)
                if key in existing:
                    continue
                default = cls.default_permission(page['key'], rank)
                db.session.add(
                    AccessPermission(
                        page_key=page['key'],
                        page_name=page['name'],
                        rank=rank,
                        can_view=default['can_view'],
                        can_edit=default['can_edit'],
                    )
                )
                created = True

        if created:
            db.session.commit()

    @classmethod
    def get_permission_map(cls):
        cls.ensure_defaults_exist()
        rows = AccessPermission.query.order_by(AccessPermission.page_name.asc(), AccessPermission.rank.asc()).all()
        return {(row.page_key, row.rank): row for row in rows}

    @classmethod
    def get_permission_matrix(cls):
        permission_map = cls.get_permission_map()
        grouped = {}

        for page in cls.PAGE_DEFINITIONS:
            group = page['group']
            grouped.setdefault(group, [])
            page_permissions = []
            for rank in cls.RANKS:
                permission = permission_map.get((page['key'], rank))
                if permission is None:
                    fallback = cls.default_permission(page['key'], rank)
                    page_permissions.append({
                        'rank': rank,
                        'can_view': fallback['can_view'],
                        'can_edit': fallback['can_edit'],
                    })
                else:
                    page_permissions.append({
                        'rank': rank,
                        'can_view': bool(permission.can_view),
                        'can_edit': bool(permission.can_edit),
                    })

            grouped[group].append({
                'key': page['key'],
                'name': page['name'],
                'description': page['description'],
                'route': page['route'],
                'permissions': page_permissions,
            })

        return grouped

    @classmethod
    def save_from_form(cls, form_data):
        cls.ensure_defaults_exist()
        permission_map = cls.get_permission_map()

        for page in cls.PAGE_DEFINITIONS:
            for rank in cls.MANAGED_RANKS:
                record = permission_map[(page['key'], rank)]
                view_field = f'perm__{page["key"]}__{rank}__view'
                edit_field = f'perm__{page["key"]}__{rank}__edit'

                can_view = form_data.get(view_field) == 'on'
                can_edit = form_data.get(edit_field) == 'on'
                if can_edit and not can_view:
                    can_view = True

                record.page_name = page['name']
                record.can_view = can_view
                record.can_edit = can_edit

        db.session.commit()

    @classmethod
    def first_accessible_route(cls, user):
        for page in cls.PAGE_DEFINITIONS:
            if cls.can_access_page(user, page['key'], 'view'):
                return page['route']
        return 'auth.logout'

    @classmethod
    def can_access_page(cls, user, page_key, access_type='view'):
        if user is None or not getattr(user, 'is_authenticated', False):
            return False

        if getattr(user, 'is_admin', lambda: False)():
            return True

        effective_rank = getattr(user, 'effective_rank', lambda: 'agent')()
        cls.ensure_defaults_exist()
        permission = AccessPermission.query.filter_by(page_key=page_key, rank=effective_rank).first()

        if permission is None:
            fallback = cls.default_permission(page_key, effective_rank)
            return fallback['can_edit'] if access_type == 'edit' else fallback['can_view']

        if access_type == 'edit':
            return bool(permission.can_edit)
        return bool(permission.can_view)

    @classmethod
    def deny_access(cls, access_type='view'):
        action = 'modify this area' if access_type == 'edit' else 'access this page'
        flash(f'You do not have permission to {action}.', 'error')
        target = request.referrer or url_for('dashboard.index')
        return redirect(target)
