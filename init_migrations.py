"""
Initialize database migrations for Hex Explorer
"""
from flask_migrate import Migrate, init, migrate as create_migration, upgrade
from app import app, db
import os

def initialize_migrations():
    """Initialize Flask-Migrate"""
    
    # Push application context
    with app.app_context():
        # Initialize migrations
        if not os.path.exists('migrations'):
            init(directory='migrations')
            print("[OK] Migrations initialized")
        else:
            print("[OK] Migrations already initialized")
        
        # Create initial migration
        try:
            create_migration(message='Initial migration')
            print("[OK] Initial migration created")
        except Exception as e:
            print(f"[WARNING] Migration already exists or error: {e}")
        
        # Apply migrations
        try:
            upgrade()
            print("[OK] Database upgraded to latest migration")
        except Exception as e:
            print(f"[WARNING] Database upgrade error: {e}")
        
        print("\nDatabase migration setup complete!")
        print("To create new migrations in the future, run:")
        print("  flask db migrate -m 'Description of changes'")
        print("  flask db upgrade")

if __name__ == '__main__':
    initialize_migrations()