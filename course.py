from sqlalchemy import func

from decorators import login_required, check_access_level
from db import db, User, Course, Teacher, Organization, Evaluation, Configuration, Role
from flask import Blueprint, render_template, flash, url_for, request, make_response, redirect, \
    Flask, jsonify, session
from util import get_current_year
import json, re

course_bp = Blueprint('course', __name__)


def validate_course_code(code):
    course_code_regex = r'^[a-zA-Z0-9\s]+$'
    return re.match(course_code_regex, code) is not None


def validate_course_title(title):
    title_regex = r'^[\w\s,:\']+$'
    return re.match(title_regex, title) is not None


def validate_string_pattern(string):
    pattern = r'^[a-zA-Z\s]+$'
    return re.match(pattern, string) is not None


def validate_number_pattern(number):
    pattern = r'^(0|[1-9][0-9]*)$'
    return re.match(pattern, number) is not None


def validate_form_data(form, extra_fields_needed=False):
    mandatory_fields = {
        'code': validate_course_code,
        'title': validate_course_title,
        'language': validate_string_pattern,
        'year': validate_number_pattern,
        'quadri': validate_number_pattern,
    }

    extra_fields = {
        'nbr_students': validate_number_pattern,
        'nbr_teaching_assistants': validate_number_pattern,
        'nbr_monitor_students': validate_number_pattern,
    }

    if extra_fields_needed:
        mandatory_fields.update(extra_fields)

    for field, validator in mandatory_fields.items():
        value = form.get(field)
        if not value:
            return f"Missing {field}", 400
        if not validator(value):
            return f"Invalid {field}", 400


def assign_teachers_to_course(course_id, course_year, assigned_teachers):
    try:
        for teacher_id in assigned_teachers:
            teacher = Teacher(user_id=teacher_id, course_id=course_id, course_year=course_year)
            db.session.add(teacher)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e


@course_bp.route('/add_course', methods=['POST', 'GET'])
@login_required
@check_access_level(Role.ADMIN)
def add_course():
    if request.method == 'GET':
        return render_template('add_course.html')

    form = request.form
    if not form:
        return make_response("Problem with form request", 500)

    error = validate_form_data(form)
    if error:
        return make_response(*error)

    code = request.form['code']
    title = request.form['title']
    quadri = request.form['quadri']
    year = request.form['year']
    language = request.form['language']

    organization_ids = request.form.getlist('organization_code[]')
    if not len(organization_ids):
        flash("Please select at least one organization", "danger")
        return redirect(url_for('course.add_course'))

    try:
        is_course = db.session.query(Course).filter(Course.code == code,
                                                    Course.year == year).first()
        if is_course is not None:
            return make_response("Course already exists", 500)

        new_course = Course(year=year, code=code, title=title, quadri=quadri, language=language)
        # Fetch organizations and add them to the course
        organizations = db.session.query(Organization).filter(Organization.id.in_(organization_ids)).all()
        new_course.organizations.extend(organizations)

        db.session.add(new_course)
        db.session.commit()
        return redirect(url_for("course.courses", current_year=year))
    except Exception as e:
        db.session.rollback()
        raise e


@course_bp.route('/courses/<int:year>')
@login_required
@check_access_level(Role.ADMIN)
def courses(year):
    courses = db.session.query(Course).filter_by(year=year).all()
    return render_template('courses.html', courses=courses, current_year=year)


@course_bp.route('/search_teachers')
def search_teachers():
    search_term = request.args.get('q', '')

    if not validate_string_pattern(search_term):
        flash("Invalid search term", "danger")

    teachers = db.session.query(User).filter(
        User.active == True,
        User.is_teacher == True,
        func.concat(User.name, ' ', User.first_name).ilike(f'%{search_term}%')
    ).all()
    results = [{'id': teacher.id, 'text': f'{teacher.name} {teacher.first_name}'} for teacher in teachers]
    return jsonify(results)


@course_bp.route('<int:course_id>/<int:year>')
@login_required
@check_access_level(Role.ADMIN)
def course_info(course_id, year):
    course = db.session.query(Course).filter(Course.id == course_id, Course.year == year).first()
    if not course:
        return make_response("Course not found", 404)

    all_years = db.session.query(Course).filter_by(id=course.id).distinct(Course.year).order_by(
        Course.year.desc()).all()

    return render_template('course_info.html', course=course, all_years=all_years, current_year=year)


@course_bp.route('/update_course_info', methods=['POST'])
@login_required
@check_access_level(Role.ADMIN)
def update_course_info():
    form = request.form
    if not form:
        return make_response("Problem with form request", 500)

    error = validate_form_data(form)
    if error:
        return make_response(*error)

    code = request.form['code']
    title = request.form['title']
    course_id = request.form['course_id']
    quadri = request.form['quadri']
    year = request.form['year']
    language = request.form['language']
    nbr_students = request.form['nbr_students']
    nbr_teaching_assistants = request.form['nbr_teaching_assistants']
    nbr_monitor_students = request.form['nbr_monitor_students']
    assigned_teachers = request.form.getlist('assigned_teachers[]')
    organisation_code = request.form.getlist('organization_code[]')
    if not len(organisation_code):
        flash("Please select at least one organization", "danger")
        return redirect(url_for('course.course_info', course_id=course_id))

    course = db.session.query(Course).filter(Course.id == course_id, Course.year == year).first()
    if not course:
        return make_response("Course not found", 404)

    # Remove all teachers assigned to the course
    try:
        db.session.query(Teacher).filter(Teacher.course_id == course_id, Teacher.course_year == year).delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

    # Add new teachers to the course
    if assigned_teachers:
        assign_teachers_to_course(course_id, year, assigned_teachers)

    try:
        course.code = code
        course.title = title
        course.quadri = quadri
        course.year = year
        course.language = language
        course.nbr_students = nbr_students
        course.nbr_teaching_assistants = nbr_teaching_assistants
        course.nbr_monitor_students = nbr_monitor_students

        course.organizations.clear()
        course.organizations = db.session.query(Organization).filter(
            Organization.id.in_(organisation_code)).all()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
    return redirect(url_for("course.course_info", course_id=course_id, year=year))


@course_bp.route('/duplicate_course/<int:course_id>/<int:year>')
@login_required
@check_access_level(Role.ADMIN)
def duplicate_course(course_id, year):
    course = db.session.query(Course).filter(Course.id == course_id, Course.year == year).first()
    return render_template('duplicate_course.html', course=course)


@course_bp.route('/add_duplicate_course', methods=['POST'])
@login_required
@check_access_level(Role.ADMIN)
def add_duplicate_course():
    form = request.form
    if not form:
        return make_response("Problem with form request", 500)

    error = validate_form_data(form, extra_fields_needed=True)
    if error:
        return make_response(*error)

    code = request.form['code']
    title = request.form['title']
    quadri = request.form['quadri']
    year = request.form['year']
    language = request.form['language']
    nbr_students = request.form['nbr_students']
    nbr_teaching_assistants = request.form['nbr_teaching_assistants']
    nbr_monitor_students = request.form['nbr_monitor_students']
    course_id = request.form['course_id']
    assigned_teachers = request.form.getlist('assigned_teachers[]')
    organisation_code = request.form.getlist('organization_code[]')
    if not len(organisation_code):
        flash("Please select at least one organization", "danger")
        return redirect(url_for('course.duplicate_course', course_id=course_id, year=year))

    try:
        duplicate_course = Course(id=course_id, code=code, title=title, quadri=quadri, year=year,
                                  language=language, nbr_students=nbr_students,
                                  nbr_teaching_assistants=nbr_teaching_assistants,
                                  nbr_monitor_students=nbr_monitor_students)
        organizations = db.session.query(Organization).filter(Organization.id.in_(organisation_code)).all()
        duplicate_course.organizations.extend(organizations)
        db.session.add(duplicate_course)

        if assigned_teachers:
            assign_teachers_to_course(course_id, year, assigned_teachers)
        db.session.commit()
    except Exception as e:
        db.session.rollback()

    return redirect(url_for('course.course_info', course_id=course_id, year=year))


@course_bp.route('/evaluations/<int:user_id>/<int:current_year>')
@login_required
def evaluations(user_id, current_year):
    courses = db.session.query(Course).filter_by(year=current_year).all()

    return render_template('evaluations.html', courses=courses, current_year=current_year, user_id=user_id)


@course_bp.route('/create_evaluations/<int:user_id>/<int:current_year>', methods=['POST'])
@login_required
def create_evaluation(user_id, current_year):
    form = request.form
    if not form:
        return make_response("Problem with form request", 500)

    course_id = request.form.get('course_id')
    tasks = request.form.getlist('tasks[]')
    other_task = request.form.get('other_task')
    evaluation_hour = request.form.get('evaluation_hour')
    workload = request.form.get('workload')
    comment = request.form.get('comment')

    if not all([course_id, evaluation_hour, workload, comment is not None]):
        return make_response("Missing required fields", 400)

    if other_task:
        tasks.append(other_task)

    try:
        existing_evaluation = db.session.query(Evaluation).filter_by(course_id=course_id, course_year=current_year,
                                                                     user_id=user_id).first()
        if existing_evaluation:
            db.session.delete(existing_evaluation)
            db.session.commit()
            flash('Existing evaluation was replaced.', 'success')
        else:
            flash('Evaluation created successfully!', 'success')

        new_evaluation = Evaluation(course_id=course_id, course_year=current_year, user_id=user_id, task=tasks,
                                    nbr_hours=evaluation_hour, workload=workload, comment=comment)
        db.session.add(new_evaluation)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')

    return redirect(url_for('course.evaluations', user_id=user_id, current_year=current_year))
