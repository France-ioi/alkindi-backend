<%inherit file="layout.mako"/>

<%block name="body">
  <div id="main">
    <p>Chargement en cours, merci de patienter...</p>
  </div>
  <script type="text/javascript" src="${request.static_url('alkindi_r2_front:assets/main'+front_min+'.js')}"></script>
  <script type="text/javascript">
    Alkindi.configure(${h.to_json(frontend_config)});
    Alkindi.install(document.getElementById('main'));
  </script>
</%block>
