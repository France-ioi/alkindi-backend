<%inherit file="layout.mako"/>

<%block name="body">
  <div id="logout">
    <form action="${request.route_url('logout')}" method="POST">
      <button type='submit'>déconnexion</button>
    </form>
  </div>
  <div id="main">
    <p>Chargement en cours, merci de patienter...</p>
  </div>
  <script type="text/javascript" src="${request.static_url('alkindi_r2_front:assets/main.js')}"></script>
  <script type="text/javascript">
    Alkindi.configureAssets({
      template: '${request.static_url('alkindi_r2_front:assets/{}').replace('%7B%7D', '{}')}'
    });
    Alkindi.install(document.getElementById('main'));
  </script>
  <!-- ${h.to_json(dict(request.session.items()))} -->
</%block>
