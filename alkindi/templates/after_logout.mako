<%inherit file="layout.mako"/>
<%block name="body">
<script type="text/javascript">
window.opener.postMessage(${h.double_json({
  'dispatch': {'type': 'Logout.Feedback'}
})}, window.location.origin);
window.location.href = ${h.to_json(auth_provider_logout_uri)};
</script>
</%block>