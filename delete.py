from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from passlib.hash import bcrypt
import uuid

from src.v1_modules.auth.model import Role, User

# Database connection string
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/drive_db"  # Update with your DB credentials

# Create a database engine
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Function to insert data
def insert_dummy_data():
    try:
        # Hash the password
        hashed_password = bcrypt.hash("admin")

        # Create the admin role
        admin_role = Role(
            id=uuid.uuid4(),
            name="admin",
            can_view=True,
            can_edit=True,
            can_delete=True,
            can_create=True,
            can_share=True,
        )
        session.add(admin_role)
        session.commit()  # Commit to ensure the role ID is available

        # Create the admin user
        admin_user = User(
            id=uuid.uuid4(),
            username="admin",
            email="admin@example.com",
            password_hash=hashed_password,
            role_id=admin_role.id,  # Associate with the admin role
            created_at=None,
            last_login=None,
        )
        session.add(admin_user)
        session.commit()

        print("Admin user and role inserted successfully!")
    except Exception as e:
        session.rollback()  # Rollback if there's an error
        print(f"Error inserting dummy data: {e}")
    finally:
        session.close()

# Run the script
if __name__ == "__main__":
    insert_dummy_data()
