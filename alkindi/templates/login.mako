<%inherit file="layout.mako"/>

<%block name="body">

%if error:
  <p>Désolé, une erreur est survenue lors de l'authentification.</p>
  <p>Erreur: ${error}</p>
  <p>Code: ${error_code}</p>
  <p>Description: ${error_description}</p>
%endif

  <div>
    Pour continuer, authentifiez vous en cliquant
      <a href="${authenticate_uri}">ici</a>.
  </div>

</%block>
