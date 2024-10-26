from decorators import login_required, check_access_level
from db import db, User, Course, PreferenceAssignment, Teacher, Researcher, Organization, PublishAssignment, \
    ResearcherSupervisor, Role, SaveAssignment
from flask import Blueprint, render_template, flash, current_app, url_for, request, make_response, redirect, session, \
    Flask, jsonify
from util import get_current_year
from enums import DEFAULT_MAX_LOAD

assignment_bp = Blueprint('assignment', __name__)


@assignment_bp.route('/assignments', methods=['GET'])
@login_required
def assignments():
    return render_template('assignment.html')


def serialize_model(model):
    """Converts a SQLAlchemy model object into a dictionary."""
    return {column.name: getattr(model, column.name) for column in model.__table__.columns}


@assignment_bp.route('/save_data', methods=['POST'])
@login_required
@check_access_level(Role.ADMIN)
def save_data():
    data = request.get_json()
    comments = data.get('comments')
    table_data = data.get('tableData')
    user_ids = data.get('userIds')

    try:
        saved_data = SaveAssignment(data=table_data, comments=comments, user_ids=user_ids)
        db.session.add(saved_data)
        db.session.commit()
    except Exception as e:
        flash(f"An error occurred while saving the data: {str(e)}", "error")

    return jsonify({"message": "Data saved successfully"}), 200


@assignment_bp.route('/load_data', methods=['GET'])
@login_required
@check_access_level(Role.ADMIN)
def load_data():
    current_year = get_current_year()
    courses = (db.session.query(Course).filter_by(year=current_year).order_by(Course.quadri).all())
    #users = db.session.query(User).filter_by(active=True).all()
    supervisors = db.session.query(ResearcherSupervisor).all()
    teachers = db.session.query(Teacher).filter_by(course_year=current_year).all()
    researchers = db.session.query(Researcher).all()
    preferences = db.session.query(PreferenceAssignment).filter_by(course_year=current_year).all()
    organizations = db.session.query(Organization).all()
    users_with_preferences = (
        db.session.query(User)
        .join(Researcher, Researcher.user_id == User.id)
        .join(PreferenceAssignment, PreferenceAssignment.researcher_id == Researcher.id)
        .filter(PreferenceAssignment.course_year == current_year)
        .all()
    )

    saved_data = db.session.query(SaveAssignment).order_by(SaveAssignment.id.desc()).first()
    user_ids = saved_data.user_ids if saved_data else []
    users = db.session.query(User).filter(
        (User.active == True) | (User.id.in_(user_ids))
    ).all()

    data = {
        'courses': [serialize_model(course) for course in courses],
        'users': {user.id: serialize_model(user) for user in users},
        'supervisors': [serialize_model(supervisor) for supervisor in supervisors],
        'teachers': {teacher.id: serialize_model(teacher) for teacher in teachers},
        'researchers': {researcher.id: serialize_model(researcher) for researcher in researchers},
        'preferences': {preference.id: serialize_model(preference) for preference in preferences},
        'organizations': {organization.id: serialize_model(organization) for organization in organizations},
        'current_year': current_year,
        'MAX_LOAD': DEFAULT_MAX_LOAD,
    }

    if saved_data:
        data['saved_data'] = serialize_model(saved_data)

    return jsonify(data)


@assignment_bp.route('/publish_assignments', methods=['POST'])
@login_required
def publish_assignments():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    current_year = get_current_year()

    for item in data:
        user_data = item.get('userData')
        course_data = item.get('courseData')

        if course_data and user_data:
            for id, pos in course_data.items():
                try:
                    assignment = PublishAssignment(course_id=id, course_year=current_year,
                                                   user_id=user_data.get('user_id'),
                                                   load_q1=user_data.get('load_q1'), load_q2=user_data.get('load_q2'),
                                                   position=pos)
                    db.session.add(assignment)
                except Exception as e:
                    return jsonify({"error": str(e)}), 400

            db.session.commit()

    return jsonify({"message": "Assignments published successfully"}), 200