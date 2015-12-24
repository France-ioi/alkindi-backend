<%inherit file="layout.mako"/>
<%block name="body">
<script type="text/javascript">
window.opener.postMessage(JSON.stringify({'action': 'afterLogout'}), window.location.origin);
window.location.href = ${h.to_json(identity_provider_logout_uri)};
</script>
</%block>