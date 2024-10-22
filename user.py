from decorators import login_required, check_access_level
from db import db, User, Researcher, Course, PreferenceAssignment, Teacher, Role, ResearcherSupervisor
from flask import Blueprint, render_template, flash, url_for, request, make_response, redirect, session, \
    Flask
from enums import DEFAULT_MAX_LOAD
from util import get_current_year
import re, json

user_bp = Blueprint('user', __name__)


def get_teachers():
    return db.session.query(User).filter(User.is_teacher == True, User.active == True).all()


def create_researcher(user_id, researcher_type, max_loads):
    new_researcher = Researcher(user_id=user_id, researcher_type=researcher_type, max_loads=max_loads)
    db.session.add(new_researcher)
    db.session.commit()
    return new_researcher


def get_researchers():
    return db.session.query(User).join(Researcher).filter(User.active == True).all()


@user_bp.route('/register')
@login_required
@check_access_level(Role.ADMIN)
def register():
    return render_template('register.html', supervisors=get_teachers())


def is_valid_email(email):
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None


def contains_valid_characters(name):
    name_regex = r'^[\w\s-]+$'
    return re.match(name_regex, name) is not None


@user_bp.route('/add_user', methods=['POST'])
@login_required
@check_access_level(Role.ADMIN)
def add_user():
    form = request.form
    if not form:
        return make_response("Problem with form request", 500)

    name = request.form['name']
    first_name = request.form['first_name']
    email = request.form['email']

    if not contains_valid_characters(name):
        return make_response("Invalid characters in name", 400)
    if not contains_valid_characters(first_name):
        return make_response("Invalid characters in first name", 400)
    if email != '' and not is_valid_email(email):
        return make_response("Invalid email format", 400)

    organization_code = request.form['organization_code']
    is_teacher = 'is_teacher' in request.form
    is_researcher = 'is_researcher' in request.form
    supervisor_ids = request.form.getlist('supervisor[]') if is_researcher else None
    researcher_type = request.form['researcher_type'] if is_researcher else None

    try:
        if db.session.query(User).filter(User.email == email).first():
            flash("Email already exists")
        else:
            new_user = User(name=name, first_name=first_name, email=email, is_teacher=is_teacher,
                            organization_id=organization_code)
            db.session.add(new_user)
            db.session.commit()
            if is_researcher:
                all_loads = DEFAULT_MAX_LOAD
                max_load = all_loads.get(researcher_type, 0)
                new_researcher = create_researcher(new_user.id, researcher_type, max_load)

                if supervisor_ids:
                    supervisors = db.session.query(User).filter(User.id.in_(supervisor_ids)).all()
                    new_researcher.supervisors = [ResearcherSupervisor(researcher=new_researcher, supervisor=s) for s in
                                                  supervisors]
                    db.session.commit()

            flash("User added successfully.", "success")
    except:
        db.session.rollback()
        raise

    return redirect(url_for("user.register"))


@user_bp.route('/users/<string:user_type>')
@login_required
@check_access_level(Role.ADMIN)
def users(user_type):
    base_query = db.session.query(User)
    list_name = ''

    if user_type == 'teacher':
        base_query = base_query.filter(User.active == True, User.is_teacher == True)
        list_name = 'Teachers'
    elif user_type == 'researcher':
        base_query = base_query.join(Researcher).filter(User.active == True)
        list_name = 'Researchers'
    elif user_type == 'archived':
        base_query = base_query.filter(User.active == False)
        list_name = 'Archived Users'
    elif user_type == 'other':
        base_query = base_query.outerjoin(Researcher).filter(
            User.active == True,
            User.is_teacher == False
        )
        list_name = 'Other Users'

    all_users = base_query.all()
    return render_template('users.html', users=all_users, user_type=user_type, list_name=list_name)


def is_allowed_user(user_id):
    return user_id == session["user_id"] or session["is_admin"]


@user_bp.route('/profile/<int:user_id>')
@login_required
def user_profile(user_id, ):
    current_year = get_current_year()
    if not is_allowed_user(user_id):
        flash("Permission denied. You do not have access to this page.", "error")
        return redirect(url_for("index"))

    all_users = get_teachers()
    requested_user = db.session.query(User).filter_by(id=user_id).first()
    researcher = db.session.query(Researcher).filter(Researcher.user_id == requested_user.id).first()
    current_user = requested_user.email == session["email"]

    courses = []
    if current_user and requested_user.organization:
        courses = db.session.query(Course).filter(Course.year == current_year,
                                                  Course.organizations.contains(requested_user.organization)
                                                  ).all()

    return render_template('user_profile.html', requested_user=requested_user, supervisors=all_users,
                           researcher=researcher, courses=courses, current_user=current_user,
                           current_year=current_year)


def delete_researcher(user_id):
    researcher = db.session.query(Researcher).filter(Researcher.user_id == user_id).first()
    if researcher:
        db.session.delete(researcher)
        db.session.commit()


@user_bp.route('/<int:user_id>/preferences/<int:current_year>', methods=['GET'])
@login_required
@check_access_level(Role.ADMIN, Role.RESEARCHER)
def preferences(user_id, current_year):
    requested_user = db.session.query(User).filter_by(id=user_id).first()
    if not is_allowed_user(user_id) or requested_user.researcher_profile is None:
        flash("Permission denied. You do not have access to this page.", "error")
        return redirect(url_for("index"))

    researcher = db.session.query(Researcher).filter(Researcher.user_id == user_id).first()
    user = db.session.query(User).filter(User.id == session["user_id"]).first()

    preferences = []
    if researcher:
        preferences = (db.session.query(PreferenceAssignment).filter_by(researcher_id=researcher.id,
                                                                        course_year=current_year)
                       .order_by(PreferenceAssignment.rank).all())

    courses = []
    if user.organization:
        courses = db.session.query(Course).filter(Course.year == current_year,
                                                  Course.organizations.contains(user.organization)
                                                  ).all()

    return render_template('preferences.html', preferences=preferences, current_year=current_year,
                           researcher=researcher, courses=courses)


@user_bp.route('/update_user_profile/<int:user_id>', methods=['POST'])
@login_required
def update_user_profile(user_id):
    form = request.form
    if not form:
        return make_response("Problem with form request", 500)

    if not is_allowed_user(user_id):
        flash("Permission denied. You do not have access to this page.", "error")
        return redirect(url_for("index"))

    name = request.form['name']
    first_name = request.form['first_name']
    email = request.form['email']
    current_year = get_current_year()

    if not contains_valid_characters(name):
        return make_response("Invalid characters in name", 400)
    if not contains_valid_characters(first_name):
        return make_response("Invalid characters in first name", 400)
    if email != '' and not is_valid_email(email):
        return make_response("Invalid email format", 400)

    organization_code = None if request.form['organization_code'] == 'None' else request.form['organization_code']
    is_admin = True if 'is_admin' in request.form else False
    is_teacher = True if 'is_teacher' in request.form else False
    is_researcher = True if 'is_researcher' in request.form else False
    supervisor_ids = request.form.getlist('supervisor[]') if is_researcher else None
    researcher_type = request.form['researcher_type'] if is_researcher else None
    max_loads = request.form['max_load'] if is_researcher else None

    user = db.session.query(User).filter(User.id == user_id).first()
    researcher = db.session.query(Researcher).filter(Researcher.user_id == user.id).first()
    if user is None:
        return make_response("User not found", 404)

    try:
        user.first_name = first_name
        user.name = name
        if session["is_admin"]:
            user.email = email
            user.organization_id = organization_code
            user.is_admin = is_admin
            user.is_teacher = is_teacher
            if is_researcher:
                if researcher is None:
                    create_researcher(user.id, researcher_type, max_loads)
                else:
                    researcher.max_loads = max_loads
                    researcher.researcher_type = researcher_type

                if supervisor_ids:
                    db.session.query(ResearcherSupervisor).filter_by(researcher_id=researcher.id).delete()
                    supervisors = db.session.query(User).filter(User.id.in_(supervisor_ids)).all()
                    researcher.supervisors = [ResearcherSupervisor(researcher=researcher, supervisor=s) for s in
                                              supervisors]
            else:
                delete_researcher(user.id)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
    return redirect(url_for("user.user_profile", user_id=user_id, current_year=current_year))


@user_bp.route('/disable/<int:user_id>')
@login_required
@check_access_level(Role.ADMIN)
def disable(user_id):
    user_type = request.args.get('user_type')
    try:
        user = db.session.query(User).filter_by(id=user_id).first()
        if user is None:
            return make_response("User not found", 404)

        user.active = 0
        db.session.commit()
        flash("User deactivated successfully.", "success")
    except ValueError as e:
        db.session.rollback()
        flash(str(e), "error")
    except Exception as e:
        db.session.rollback()
        raise e

    return redirect(url_for("user.users", user_type=user_type))


@user_bp.route('/enable/<int:user_id>')
@login_required
@check_access_level(Role.ADMIN)
def enable(user_id):
    try:
        user = db.session.query(User).filter_by(id=user_id).first()
        if user is None:
            return make_response("User not found", 404)

        user.active = 1
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

    return redirect(url_for("user.users", user_type='archived'))
