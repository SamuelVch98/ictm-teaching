import argparse
from app import app, db
from datetime import datetime
from db import User, Configuration, Organization


def create_database(name, first_name, email):
    with app.app_context():
        add_first_admin(name, first_name, email)
        initialize_configuration()
        create_organizations()
        print("Database tables created successfully.")


def add_first_admin(name, first_name, email):
    admin_exists = db.session.query(User).filter_by(is_admin=True).first()
    if admin_exists is None:
        first_admin = User(first_name=first_name, name=name, email=email, is_admin=True)
        db.session.add(first_admin)
        db.session.commit()
        print(f"Admin account for {first_name} {name} created successfully.")
    else:
        print("Admin account already exists.")


# Add the first year corresponding to the current year
def initialize_configuration():
    current_year = datetime.now().year
    existing_year = Configuration.query.filter_by(year=current_year).first()

    if existing_year is None:
        config = Configuration(year=current_year, is_current_year=True)
        db.session.add(config)
        db.session.commit()


# Create organizations
def create_organizations():
    if db.session.query(Organization).count() == 0:
        ORGANIZATIONS = ["SST", "ICTM", "ELEN", "EPL", "INMA", "SSH", "IMMC", "IMAQ", "INGI", "SSS", "IONS", "ELI",
                         "LDRI"]
        db.session.add_all([Organization(name=org) for org in ORGANIZATIONS])
        db.session.commit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Create the database and add the first admin.")
    parser.add_argument('--name', required=True, help="Name of the admin.")
    parser.add_argument('--first_name', required=True, help="First name of the admin.")
    parser.add_argument('--email', required=True, help="Email of the admin.")

    args = parser.parse_args()
    create_database(args.name, args.first_name, args.email)
