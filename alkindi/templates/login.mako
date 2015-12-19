<%inherit file="layout.mako"/>

<%block name="body">

%if error:
  <p>Désolé, une erreur est survenue lors de l'authentification.</p>
  <p>Erreur: ${error}</p>
  <p>Code: ${error_code}</p>
  <p>Description: ${error_description}</p>
%endif

  <div class="container">
    <div class="panel panel-default" style="margin-top: 20px">
      <div class="panel-heading">
        Concours Alkindi
      </div>
      <div class="panel-body">
        Pour continuer, authentifiez vous en cliquant
          <a class="btn btn-primary" href="${authenticate_uri}">ici</a>.
      </div>
    </div>
  </div>

</%block>
