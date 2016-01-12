from pyramid.httpexceptions import HTTPNotModified

from alkindi.globals import app
from alkindi.contexts import (
    TeamApiContext, WorkspaceRevisionApiContext, AttemptApiContext)
import alkindi.views as views


def includeme(config):
    api_get(config, TeamApiContext, '', read_team)
    api_get(config, TeamApiContext, 'attempts', read_team_attempts)
    api_get(config, AttemptApiContext, 'revisions', list_attempt_revisions)
    api_get(config, AttemptApiContext, 'answers', list_attempt_answer)
    api_get(config, WorkspaceRevisionApiContext, '', read_workspace_revision)


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
    team = app.model.load_team(team_id)
    print("team {}".format(team))
    round_ = app.model.load_round(team['round_id'])
    print("round_ {}".format(round_))
    attempts = app.model.load_team_attempts(team_id)
    return views.view_attempts(attempts, team, round_)


def list_attempt_revisions(request):
    attempt_id = request.context.attempt_id
    revisions = app.model.load_attempt_revisions(attempt_id)
    view = views.view_revisions(revisions)
    view['success'] = True
    return view


def list_attempt_answer(request):
    attempt_id = request.context.attempt_id
    answers = app.model.load_attempt_answers(attempt_id)
    view = views.view_answers(answers)
    view['success'] = True
    return view


def read_workspace_revision(request):
    revision = request.context.workspace_revision
    check_etag(request, revision['created_at'])
    return {
        'success': True,
        'workspace_revision': views.view_user_workspace_revision(revision)
    }
