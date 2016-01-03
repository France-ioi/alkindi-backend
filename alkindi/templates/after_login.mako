<%inherit file="layout.mako"/>
<%block name="body">

%if error:
  <div class="alert alert-danger" role="alert">
    <p>Désolé, une erreur est survenue lors de l'authentification.</p>
    <p>Erreur : <strong>${error}</strong></p>
  </div>
%endif

%if user_id:
<script type="text/javascript">
window.opener.postMessage(JSON.stringify({
  'action': 'afterLogin',
  'user_id': ${h.to_json(user_id)}
}), window.location.origin);
window.close();
</script>;
%endif

</%block>