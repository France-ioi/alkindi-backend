<!doctype html>

<head lang="fr">
  <meta charset="utf-8">
  <title>Index</title>
  <link href="${g.asset_url('main.css')}" rel="stylesheet">
</head>

<body>
  <p>Welcome, ${username}.</p>
  <form action="${request.route_url('logout')}" method="POST">
    <button type='submit'>déconnexion</button>
  </form>
</body>

<tt>${h.to_json(dict(request.session.items()))}</tt>
