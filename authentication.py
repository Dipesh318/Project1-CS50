from flask import redirect, render_template, request, session, flash


def auth():
    if session.get("user_id") is None:
        return False
    return True