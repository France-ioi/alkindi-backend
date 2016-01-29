from pyramid.httpexceptions import HTTPNotModified

from alkindi.contexts import WorkspaceRevisionApiContext
from alkindi.model.workspace_revisions import load_workspace_revision
import alkindi.views as views


def includeme(config):
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


def read_workspace_revision(request):
    revision_id = request.context.workspace_revision_id
    revision = load_workspace_revision(request.db, revision_id)
    check_etag(request, revision['created_at'])
    view = views.view_user_workspace_revision(revision)
    return {
        'success': True,
        'workspace_revision': view
    }
