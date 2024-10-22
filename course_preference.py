from decorators import login_required, check_access_level
from db import db, Researcher, PreferenceAssignment, Role
from flask import Blueprint, render_template, flash, url_for, request, make_response, redirect, \
    Flask, jsonify, session
import json

from util import get_current_year

course_preference_bp = Blueprint('course_preference', __name__)


def delete_old_preferences(researcher_id, current_year):
    try:
        db.session.query(PreferenceAssignment).filter(
            PreferenceAssignment.researcher_id == researcher_id,
            PreferenceAssignment.course_year == current_year,
        ).delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e


@course_preference_bp.route('/save_preference', methods=['POST'])
@login_required
@check_access_level(Role.RESEARCHER)
def save_preference():
    data = request.get_json()
    current_year = get_current_year()

    if data is None:
        flash("No data received", "error")

    preferences = data.get("preferences", None)
    if preferences is None:
        flash("No preferences received", "error")

    user_id = session["user_id"]
    researcher = Researcher.query.filter(Researcher.user_id == user_id).first()
    if researcher is None:
        flash("Researcher not found", "error")

    delete_old_preferences(researcher.id, current_year)

    for rank, preference in enumerate(preferences):
        try:
            course_id = preference['course_id']
            course_year = preference['course_year']
            new_preference = PreferenceAssignment(rank=rank, course_id=course_id, course_year=course_year,
                                                  researcher_id=researcher.id)
            db.session.add(new_preference)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    return redirect(url_for("user.preferences", user_id=user_id, current_year=current_year))


@course_preference_bp.route('/delete_preference', methods=['GET'])
@login_required
@check_access_level(Role.RESEARCHER)
def delete_preference():
    preference_id = request.args.get('preference')
    current_year = get_current_year()
    try:
        db.session.query(PreferenceAssignment).filter_by(id=preference_id).delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

    return redirect(url_for("user.preferences", user_id=session["user_id"], current_year=current_year))
