"""
Graph visualization settings model for controlling node appearance by layer.
"""
from ..extensions import db


class GraphLayerSettings(db.Model):
    """
    Settings for graph visualization per layer.
    
    Attributes:
        id: Primary key
        layer: Layer number (1 for base metrics, 2+ for derived)
        color: Hex color code for nodes in this layer
        shape: Node shape (circle, rectangle, square, diamond)
        size: Node size in pixels
    """
    __tablename__ = 'graph_layer_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    layer = db.Column(db.Integer, unique=True, nullable=False, index=True)
    color = db.Column(db.String(7), nullable=False, default='#F26F2A')
    shape = db.Column(db.String(16), nullable=False, default='circle')
    size = db.Column(db.Integer, nullable=False, default=30)
    
    # Valid shapes
    SHAPES = ['circle', 'rectangle', 'square', 'diamond', 'hexagon']
    
    def __repr__(self):
        return f'<GraphLayerSettings layer={self.layer} color={self.color} shape={self.shape}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'layer': self.layer,
            'color': self.color,
            'shape': self.shape,
            'size': self.size
        }
    
    @classmethod
    def get_all_settings(cls):
        """Get all layer settings as a dictionary keyed by layer number."""
        settings = cls.query.order_by(cls.layer).all()
        return {s.layer: s.to_dict() for s in settings}
    
    @classmethod
    def get_or_create(cls, layer):
        """Get existing settings for a layer or create defaults."""
        setting = cls.query.filter_by(layer=layer).first()
        if setting is None:
            # Default colors by layer
            default_colors = {
                1: '#22c55e',  # Green for base metrics
                2: '#F26F2A',  # Orange for layer 2
                3: '#3b82f6',  # Blue for layer 3
                4: '#a855f7',  # Purple for layer 4
                5: '#ec4899',  # Pink for layer 5
            }
            setting = cls(
                layer=layer,
                color=default_colors.get(layer, '#6b7280'),
                shape='circle',
                size=30
            )
            db.session.add(setting)
            db.session.commit()
        return setting
    
    @classmethod
    def update_setting(cls, layer, color=None, shape=None, size=None):
        """Update settings for a specific layer."""
        setting = cls.get_or_create(layer)
        if color is not None:
            setting.color = color
        if shape is not None and shape in cls.SHAPES:
            setting.shape = shape
        if size is not None and 10 <= size <= 100:
            setting.size = size
        db.session.commit()
        return setting
    
    @classmethod
    def ensure_defaults_exist(cls, max_layer=5):
        """Ensure default settings exist for layers 1 through max_layer."""
        for layer in range(1, max_layer + 1):
            cls.get_or_create(layer)
