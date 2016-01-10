<%inherit file="layout.mako"/>

<%block name="body">
  <div id="main">
    <p>Chargement en cours, merci de patienter...</p>
  </div>
  <div id='pageFooter'>
    <div class='wrapper'>
      En cas de difficultés techniques, contactez
        info@concours-alkindi.fr
      en décrivant précisément la situation.
      <span class="pull-right">
        v${front_version}
      </span>
    </div>
  </div>
  <div id="reports" style="position: fixed; right: 0; bottom: 0; width: 0; height: 0;"></div>
  <script type="text/javascript" src="${request.static_url('alkindi_r2_front:assets/main'+front_min+'.js')}"></script>
  <script type="text/javascript">
    Alkindi.configure(${h.to_json(frontend_config)});
    Alkindi.install(document.getElementById('main'));
  </script>
</%block>
