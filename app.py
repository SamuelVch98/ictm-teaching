import datetime

import jinja2.defaults

from auth import auth_bp
from user import user_bp
from course import course_bp
from config import config_bp
from course_preference import course_preference_bp
from assignment import assignment_bp
from db import db, Configuration, Organization, User, Course, Teacher, Researcher, PublishAssignment
from decorators import *
from flask import Flask, render_template, session, request
from enums import *
from util import get_current_year
import json

app = Flask(__name__)
app.config.from_file("config.json", load=json.load)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Core blueprints
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(user_bp, url_prefix="/user")
app.register_blueprint(course_bp, url_prefix="/course")
app.register_blueprint(config_bp, url_prefix="/config")
app.register_blueprint(course_preference_bp, url_prefix="/course_preference")
app.register_blueprint(assignment_bp, url_prefix="/assignment")


def get_configurations():
    return db.session.query(Configuration).order_by(Configuration.year.asc()).all()


def get_organization():
    return db.session.query(Organization).all()


def is_researcher():
    return db.session.query(Researcher).filter_by(user_id=session['user_id']).first() is not None


@app.context_processor
def inject_configurations():
    return dict(configurations=get_configurations(), organizations_code=get_organization(), quadri=QUADRI,
                language=LANGUAGES, researcher_type=RESEARCHERS_TYPE, dynamic_year=get_current_year(),
                tasks=TASK, evaluation_hour=EVALUATION_HOUR, workloads=WORKLOAD, is_researcher=is_researcher())


# Routes
@app.route('/')
@login_required
def index():  # put application's code here
    current_year = get_current_year()
    user = db.session.query(User).filter_by(email=session['email']).first()
    researcher = db.session.query(Researcher).filter_by(user_id=user.id).first()

    courses_teacher = db.session.query(Course).join(Teacher).filter(Teacher.user_id == user.id).all()
    courses_researcher = db.session.query(PublishAssignment).order_by(PublishAssignment.id.desc()).first()

    '''
    if researcher:
        courses_researcher = courses_researcher.filter(PublishAssignment.is_teacher_publication == False).all()
    else:
        courses_researcher = courses_researcher.all()
    '''
    return render_template("home.html", user=user, courses=courses_teacher, courses_researcher=courses_researcher)


if __name__ == '__main__':
    app.run()
