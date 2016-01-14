from pyramid.httpexceptions import HTTPNotModified

from alkindi.globals import app
from alkindi.contexts import (
    TeamApiContext, WorkspaceRevisionApiContext, AttemptApiContext)
from alkindi.model.teams import load_team
from alkindi.model.rounds import load_round
from alkindi.model.attempts import load_team_attempts
from alkindi.model.workspace_revisions import load_workspace_revision
import alkindi.views as views


def includeme(config):
    # Still used
    api_get(config, WorkspaceRevisionApiContext, '', read_workspace_revision)
    # No longer used:
    api_get(config, TeamApiContext, '', read_team)
    api_get(config, TeamApiContext, 'attempts', read_team_attempts)
    api_get(config, AttemptApiContext, 'revisions', list_attempt_revisions)
    api_get(config, AttemptApiContext, 'answers', list_attempt_answer)


def api_get(config, context, name, view):
    config.add_view(
        view, context=context, name=name,
        request_method='GET',
        permission='read', renderer='json')


def check_etag(request, etag):
    etag = str(etag)
    if etag in request.if_none_match:
        raise HTTPNotModified()
    request.response.vary = 'Cookie'
    request.response.cache_control = 'max-age=3600, private, must-revalidate'
    request.response.etag = etag


def read_team(request):
    team = request.context.team
    check_etag(request, team['revision'])
    return {'team': views.view_user_team(team)}


def read_team_attempts(request):
    team_id = request.context.team_id
    team = load_team(app.db, team_id)
    round_ = load_round(app.db, team['round_id'])
    attempts = load_team_attempts(app.db, team_id)
    return views.view_round_attempts(round_, attempts)


def list_attempt_revisions(request):
    attempt_id = request.context.attempt_id
    view = {'success': True}
    views.add_revisions(app.db, view, attempt_id)
    return view


def list_attempt_answer(request):
    attempt_id = request.context.attempt_id
    answers = app.model.load_limited_attempt_answers(attempt_id)
    view = views.view_answers(app.db, answers)
    view['success'] = True
    return view


def read_workspace_revision(request):
    revision_id = request.context.workspace_revision_id
    revision = load_workspace_revision(app.db, revision_id)
    check_etag(request, revision['created_at'])
    view = views.view_user_workspace_revision(revision)
    return {
        'success': True,
        'workspace_revision': view
    }
