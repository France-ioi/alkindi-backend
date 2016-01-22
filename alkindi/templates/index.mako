<%inherit file="layout.mako"/>

<%block name="body">
  <div id="main">
    <p>Chargement en cours, merci de patienter...</p>
  </div>
  <div id='pageFooter'>
    <div class='wrapper'>
      En cas de difficultés techniques, contactez
        info@concours-alkindi.fr
      en décrivant précisément la situation et en
      indiquant votre login.
      <span class="pull-right">
        v${front_version}
      </span>
    </div>
  </div>
  <div id="reports" style="position: fixed; right: 0; bottom: 0; width: 0; height: 0;"></div>
  <script type="text/javascript" src="${request.static_url('alkindi_r2_front:assets/main'+front_min+'.js')}"></script>
  <script type="text/javascript">
  !function () {
    var mainElement = document.getElementById('main');
    if (window.Alkindi !== undefined) {
      Alkindi.configure(${h.to_json(frontend_config)});
      Alkindi.install(mainElement);
    } else {
      // Redirect to ?nocdn, if not already there.
      if (window.location.search === "") {
        window.location.search = '?nocdn';
      } else {
        mainElement.innerHTML = "<p style='font-size: 24px; color: red;'>Le chargement a échoué, n'hésitez pas à contacter info@concours-alkindi.fr.</p>";
      }
    }
  }();
  </script>
%if front_min == '':
  <script type="text/javascript" src="http://127.0.0.1:5500/livereload.js"></script>
%endif
</%block>
