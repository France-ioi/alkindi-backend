<%inherit file="layout.mako"/>
<%block name="body">
% if user_id:
<script type="text/javascript">
window.opener.postMessage(${h.double_json({
  'dispatch': {
    'type': 'Login.Feedback',
    'user_id': user_id,
    'csrf_token': csrf_token
  }
})}, window.location.origin);
window.close();
</script>
% else:
<script type="text/javascript">
window.opener.postMessage(${h.double_json({
  'dispatch': {
    'type': 'Login.Feedback',
    'error': error
  }
})}, window.location.origin);
window.close();
</script>
% endif
</%block>