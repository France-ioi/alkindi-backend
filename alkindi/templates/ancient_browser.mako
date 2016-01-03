<%inherit file="layout.mako"/>

<%block name="body">
  <div class="container">
    <h1>Désolé, votre navigateur est trop ancien…</h1>
    <p>
      Votre navigateur, ${user_agent['family']} ${user_agent['major']},
      n'est pas supporté.
    </p>
    <p>Vous pouvez utiliser l'une de ces versions ou ultérieures :</p>
    <ul>
      <li><a href="https://www.google.fr/intl/fr/chrome/browser/desktop/">Chrome</a> 47</li>
      <li><a href="https://www.mozilla.org/fr/firefox/new/">Firefox</a> 43</li>
      <li><a href="http://www.opera.com/fr">Opera</a> 34</li>
      <li>Safari 9.0.2</li>
      <li>Microsoft IE 9 ou Edge 25</li>
    </ul>
    <p>
      Si vous voulez essayer, sans garantie que cela fonctionne, suivez ce
        <a href="${request.route_url('index', _query={'ancient': '1'})}">lien</a>.
    </p>
  </div>
</%block>
