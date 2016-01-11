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
window.opener.postMessage(${h.double_json({
  'action': 'afterLogin',
  'user_id': user_id,
  'csrf_token': csrf_token,
})}, window.location.origin);
window.close();
</script>;
%endif

</%block>