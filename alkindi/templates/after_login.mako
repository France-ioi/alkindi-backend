<%inherit file="layout.mako"/>
<%block name="body">

%if error:
  <div class="alert alert-danger" role="alert">
    <p>Désolé, une erreur est survenue lors de l'authentification.</p>
    <p>Erreur : <strong>${error}</strong></p>
    <p>Description : <strong>${error_description}</strong></p>
  </div>
%endif

%if user:
<script type="text/javascript">
window.opener.postMessage(JSON.stringify({
  'action': 'afterLogin',
  'user': ${h.to_json(user)}
}), window.location.origin);
window.close();
</script>;
%endif

</%block>