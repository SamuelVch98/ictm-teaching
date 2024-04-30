import json
from functools import wraps
from flask import Flask, render_template, redirect, session, request, url_for, make_response, flash
from sqlalchemy.sql.functions import current_user

from db import User, Session, Course

import auth
from auth import auth_bp

app = Flask(__name__)

app.config.from_file("config.json", load=json.load)
with open('config.json') as config_file:
    app.config.update(json.load(config_file))
'''
try:
    with open('config.json') as config_file:
        app.config.update(json.load(config_file))
except Exception as e:
    print(f"Error loading config file: {e}")
'''

# Core blueprints
app.register_blueprint(auth_bp, url_prefix="/auth")

# List from config.json
organization_codes = app.config.get('organization_codes', [])
quadri = app.config.get('quadri', [])
year = app.config.get('year', [])


# Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in", False):
            return auth.login()
        else:
            return f(*args, **kwargs)
    return decorated_function


# Routes
@app.route('/')
def index():  # put application's code here
    return render_template("index.html")


@app.route('/private')
@login_required
def private():
    return render_template("private.html")

@app.route('/register')
@login_required
def register():
    return render_template('register.html', organization_codes=organization_codes)


@app.route('/add_user', methods=['POST'])
@login_required
def add_user():
    form = request.form
    if form:
        name = request.form['name']
        first_name = request.form['first_name']
        email = request.form['email']
        organization_code = request.form['organization_code']

        db_session = Session()
        try:
            new_user = User(name=name, first_name=first_name, email=email, organization_code=organization_code)
            db_session.add(new_user)
            db_session.commit()
        except:
            db_session.rollback()
            raise
        return redirect(url_for("index"))
    else:
        return make_response("Problem with form request", 500)

@app.route('/profile')
@login_required
def profile():
    db_session = Session()
    email = session["email"]
    user = user = db_session.query(User).filter(User.email == email).first()
    return render_template("profile.html", user=user)


@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    form = request.form
    if form:
        name = request.form['name']
        first_name = request.form['first_name']
        email = request.form['email']

        db_session = Session()
        user = db_session.query(User).filter(User.email == email).first()
        if user:
            try:
                user.first_name = first_name
                user.name = name
                db_session.commit()
                session["first_name"] = first_name
                session["name"] = name
            except Exception as e:
                db_session.rollback()
            return redirect(url_for("profile"))
        else:
            flash('User not found', 'danger')
    else:
        return make_response("Problem with form request", 500)

@app.route('/users')
@login_required
def users():
    db_session = Session()
    all_users = db_session.query(User).all()
    return render_template('users.html', users=all_users)

@app.route('/user/profile/<int:user_id>')
@login_required
def user_profile(user_id):
    db_session = Session()
    my_user = db_session.query(User).filter_by(id=user_id).first()
    if my_user:
        return render_template('user_profile.html', user=my_user, organization_codes=organization_codes)
    else:
        return make_response("The user is not found", 500)

@app.route('/update_user_profile', methods=['POST'])
@login_required
def update_user_profile():
    form = request.form
    if form:
        name = request.form['name']
        first_name = request.form['first_name']
        email = request.form['email']
        user_id = request.form['user_id']
        organization_code = request.form['organization_code']

        db_session = Session()
        user = db_session.query(User).filter(User.id == user_id).first()
        if user:
            try:
                user.first_name = first_name
                user.name = name
                user.email = email
                user.organization_code = organization_code
                db_session.commit()
            except Exception as e:
                db_session.rollback()
            return redirect(url_for("user_profile", user_id=user_id))
        else:
            flash('User not found', 'danger')
    else:
        return make_response("Problem with form request", 500)

@app.route('/form_course')
@login_required
def form_course():
    return render_template('add_course.html', year=year, quadri=quadri)

@app.route('/add_course', methods=['POST'])
@login_required
def add_course():
    form = request.form
    if form:
        code = request.form['code']
        title = request.form['title']
        quadri = request.form['quadri']
        year = request.form['year']
        load_needed = request.form['load_needed']

        db_session = Session()
        try:
            new_course = Course(code=code, title=title, quadri=quadri, year=year, load_needed=load_needed)
            db_session.add(new_course)
            db_session.commit()
        except:
            db_session.rollback()
            raise
        return redirect(url_for("form_course"))

@app.route('/courses')
@login_required
def courses():
    db_session = Session()
    all_courses = db_session.query(Course).all()
    unique_courses = {}
    for course in all_courses:
        unique_courses[course.code] = course
    unique_courses = list(unique_courses.values())
    return render_template('courses.html', courses=unique_courses)

@app.route('/course/<int:course_id>')
@login_required
def course_info(course_id):
    db_session = Session()
    my_course = db_session.query(Course).filter_by(id=course_id).first()
    course_by_code = db_session.query(Course).filter_by(code=my_course.code).all()
    if my_course:
        return render_template('course_info.html', course=course_by_code, code=my_course.code, title=my_course.title, quadri=quadri, year=year)
    else:
        return make_response("The user is not found", 500)


@app.route('/update_course_info', methods=['POST'])
@login_required
def update_course_info():
    form = request.form
    if form:
        course_id = request.form['course_id']
        code = request.form['code']
        title = request.form['title']
        quadri = request.form['quadri']
        year = request.form['year']
        load_needed = request.form['load_needed']

        db_session = Session()
        course = db_session.query(Course).filter(Course.id == course_id).first()
        if course:
            try:
                course.code = code
                course.title = title
                course.quadri = quadri
                course.year = year
                course.load_needed = load_needed
                db_session.commit()
            except Exception as e:
                db_session.rollback()
            return redirect(url_for("course_info", course_id=course_id))
        else:
            flash('Course not found', 'danger')
    else:
        return make_response("Problem with form request", 500)



if __name__ == '__main__':
    app.run()
