from enum import Enum

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import json
from sqlalchemy.orm import validates

db = SQLAlchemy()


class Role(Enum):
    ADMIN = "admin"
    RESEARCHER = "researcher"
    TEACHER = "teacher"


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    first_name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(200), nullable=True, unique=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_teacher = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))

    organization = db.relationship('Organization', back_populates='users')

    @validates('active')
    def validate_active(self, key, value):
        if not value:
            if self.researchers:
                raise ValueError("Cannot deactivate a supervisor who has supervisees.")
            if self.user_teacher:
                raise ValueError("Cannot deactivate a teacher assigned to a course.")
        return value

    def allowed(self, access_level):
        role_access = {
            Role.ADMIN: self.is_admin,
            Role.RESEARCHER: self.researcher_profile is not None,
            Role.TEACHER: self.is_teacher
        }

        return role_access.get(access_level, False)


class Course(db.Model):
    __tablename__ = 'course'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    year = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10))
    title = db.Column(db.String(100))
    quadri = db.Column(db.Integer)
    language = db.Column(db.String(10))
    nbr_students = db.Column(db.Integer, default=0)
    nbr_teaching_assistants = db.Column(db.Integer, default=0)
    nbr_monitor_students = db.Column(db.Integer, default=0)

    __table_args__ = (db.UniqueConstraint('id', 'year', name='uq_course_id_year'),)

    organizations = db.relationship('Organization',
                                    secondary='course_organization',
                                    back_populates='courses',
                                    primaryjoin="and_(Course.id == CourseOrganization.course_id, Course.year == "
                                                "CourseOrganization.course_year)",
                                    secondaryjoin="Organization.id == CourseOrganization.organization_id")


class Researcher(db.Model):
    __tablename__ = 'researcher'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    max_loads = db.Column(db.Integer)
    jokers = db.Column(db.Integer)
    researcher_type = db.Column(db.String(30))

    user = db.relationship('User', backref=db.backref('researcher_profile', uselist=False))


class ResearcherSupervisor(db.Model):
    __tablename__ = 'researcher_supervisor'
    researcher_id = db.Column(db.Integer, db.ForeignKey('researcher.id'), primary_key=True)
    supervisor_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)

    researcher = db.relationship('Researcher', backref=db.backref('supervisors', lazy=True))
    supervisor = db.relationship('User', backref=db.backref('researchers', lazy=True))


class Teacher(db.Model):
    __tablename__ = 'teacher'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer)
    course_year = db.Column(db.Integer)

    # Creation of a link to the compound key (id, year) of the course table
    __table_args__ = (
        db.ForeignKeyConstraint(
            ['course_id', 'course_year'],
            ['course.id', 'course.year']
        ),
    )

    user = db.relationship('User', backref=db.backref('user_teacher', uselist=False))
    course = db.relationship('Course', backref=db.backref('course_teacher', lazy=True))


class PreferenceAssignment(db.Model):
    __tablename__ = 'preference_assignment'
    rank = db.Column(db.Integer, nullable=False)
    id = db.Column(db.Integer, primary_key=True)
    rank = db.Column(db.Integer, nullable=False)
    course_id = db.Column(db.Integer, nullable=False)
    course_year = db.Column(db.Integer, nullable=False)
    researcher_id = db.Column(db.Integer, db.ForeignKey('researcher.id'), nullable=False)

    # Creation of a link to the compound key (id, year) of the course table
    __table_args__ = (
        db.UniqueConstraint('course_id', 'course_year', 'researcher_id', name='unique_course_year_researcher'),
        db.ForeignKeyConstraint(
            ['course_id', 'course_year'],
            ['course.id', 'course.year']
        ),
    )

    course = db.relationship('Course', backref=db.backref('course_preference_assignment', lazy=True))
    researcher = db.relationship('Researcher', backref=db.backref('researcher_preference_assignment', lazy=True))


class Configuration(db.Model):
    __tablename__ = 'configuration'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    is_current_year = db.Column(db.Boolean, default=False)

    @classmethod
    def update_current_year(cls, config_id):
        # Update all years to set is_current_year to False
        cls.query.update({cls.is_current_year: False})

        selected_config = cls.query.get(config_id)
        if selected_config:
            selected_config.is_current_year = True
            db.session.commit()


class Organization(db.Model):
    __tablename__ = 'organization'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False, unique=True)

    users = db.relationship('User', back_populates='organization')
    courses = db.relationship('Course',
                              secondary='course_organization',
                              back_populates='organizations',
                              primaryjoin="Organization.id == CourseOrganization.organization_id",
                              secondaryjoin="and_(Course.id == CourseOrganization.course_id, Course.year == CourseOrganization.course_year)")


class CourseOrganization(db.Model):
    __tablename__ = 'course_organization'

    course_id = db.Column(db.Integer, primary_key=True)
    course_year = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), primary_key=True)

    __table_args__ = (
        db.ForeignKeyConstraint(
            ['course_id', 'course_year'],
            ['course.id', 'course.year']
        ),
    )


class PublishAssignment(db.Model):
    __tablename__ = 'publish_assignment'
    course_id = db.Column(db.Integer, primary_key=True)
    course_year = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    load_q1 = db.Column(db.Integer)
    load_q2 = db.Column(db.Integer)
    position = db.Column(db.Integer)

    __table_args__ = (
        db.ForeignKeyConstraint(
            ['course_id', 'course_year'],
            ['course.id', 'course.year']
        ),
    )


class Evaluation(db.Model):
    __tablename__ = 'evaluation'

    course_id = db.Column(db.Integer, primary_key=True)
    course_year = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    task = db.Column(db.JSON, nullable=False)
    nbr_hours = db.Column(db.String(10), nullable=False)
    workload = db.Column(db.String(10), nullable=False)
    comment = db.Column(db.String(500))

    __table_args__ = (
        db.ForeignKeyConstraint(
            ['course_id', 'course_year'],
            ['course.id', 'course.year']
        ),
    )
