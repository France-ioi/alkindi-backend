<!DOCTYPE html>
<meta charset="utf-8">
<html>
<head>
  <title>TEST IMAGE</title>
  <style type="text/css">
    .playfairIntro-main-table {
         margin: 5px;
      }
    .playfairIntro-main-table, .playfairIntro-table {
      border-collapse: collapse;
      text-align:center;
      font-family:"Lucida Console", Monaco, monospace;
         float: right;
    }
    .playfairIntro-td {
      border: 1px solid #000;
      height: 30px;
      width: 30px;
      padding:0;
    }
    .playfairIntro-td-redBorder {
      border:5px solid red;
      padding:0;
    }
    .playfairIntro-td-background {
      background-color:#aaa;
    }
  </style>
</head>

<body style="width:800px;">
<p>
Votre amie Alice a récupéré une pochette contenant un message chiffré (allez lire la Bande dessinée de son aventure quand vous avez un peu de temps). Voici le texte :
</p>
<div class="playfairIntro-cipher-text">
  ${cipher_text}
</div>
<p>
Votre but est de l’aider à déchiffrer ce texte, et d’y trouver une adresse et deux nombres à calculer pour accéder à un coffre.
</p>
<p>
Vous avez remarqué plusieurs choses qui vont vous aider :
</p>
<p>
<b>Prénom :</b> sur la pochette se trouve le prénom du destinataire du message : ${firstname}. Notez que ce prénom n’est probablement pas présent dans le message.
</p>
<p>
<b>Type de chiffrement :</b> Alice a identifié le type de chiffrement utilisé. Il s’agit du chiffrement appelé Playfair. Une description de son principe en est donnée plus bas.
</p>
<p>
<b>Outils :</b> dans l’onglet cryptanalyse accessible en haut de votre interface, vous disposez d’outils pour vous aider à déchiffrer le message. Une documentation de ces outils est fournie dans l’onglet documentation.
</p>
<p>
<b>Indices :</b> le deuxième de ces outils permet d’obtenir des indices. Chaque indice retire 10 points au score que vous obtiendrez après avoir résolu le sujet. Vous avez un capital de 500 points. Il est difficile de réussir sans indices, donc n’hésitez pas trop à en demander quelques-uns en les choisissant bien. Assurez-vous cependant que votre équipe est d’accord sur votre stratégie avant de demander des indices.
</p>
<p>
<b>Entraînement et tentatives :</b> au départ vous avez un sujet d’entraînement à résoudre sans limite de temps. Le score obtenu sur ce sujet ne compte pas. Une fois résolu, vous aurez 3 tentatives pour résoudre en 1h à chaque fois un sujet avec un message un peu différent, chiffré selon le même principe, mais une clé différente (la grille Playfair) et bien sûr une adresse et un code à trouver  différents. À chaque tentative, vous repartez d’une grille vide et d’un capital de 500 points.
</p>
<p>
<b>La méthode de chiffrement de Playfair :</b> voici quelques explications sur les points importants de la méthode qui a été utilisée pour chiffrer le message, à savoir Playfair.
</p>
<p>
1) Le message a été converti en majuscules et les accents retirés, alors que les espaces et les signes de ponctuation sont ignorés.
</p>
<p>
2) Tous les W du message ont été remplacés par des V.
</p>
<p>
4) Une grille de 5x5 cases a été remplie avec les lettres de l’alphabet sauf le W. Dans notre cas, considérez que les lettres ont été placées au hasard.
</p>
<p>
5) Le texte a ensuite été découpé en paires de lettres successives, appelées bigrammes. Ainsi le texte “MON TEXTE” est découpé en 4 bigrammes, “MO”, “NT, “EX”, “TE”.
</p>
<p>
Pour éviter des bigrammes consitués de deux fois la même lettre, des X sont insérés dans le texte entre certaines lettres doubles. Ainsi, le texte “BELLE” devient “BE”, “LX”, “LE”. Par contre le texte “ELLE” devient “EL” “LE” car les deux L ne tombent pas dans le même bigramme donc il n’est pas utile d’insérer un X..
</p>
<p>
6) Chaque bigramme du texte est remplacé par un bigramme chiffré en utilisant la position des lettres de l’alphabet dans la grille. Par exemple pour “MO”, on a trois cas possibles :
</p>
<p>
a) si le M et le O ne sont ni sur la même ligne, ni sur la même colonne :
</p>
<table class="playfairIntro-main-table">
  <tr>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
  </tr>
  <tr>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
  </tr>
  <tr>
    <td class="playfairIntro-td"></td>
    <td colspan='4' rowspan='2' class="playfairIntro-td-redBorder">
      <table class="playfairIntro-table">
        <tr>
          <td class="playfairIntro-td playfairIntro-td-background">O</td>
          <td class="playfairIntro-td"></td>
          <td class="playfairIntro-td"></td>
          <td class="playfairIntro-td">R</td>
        </tr>
        <tr>
          <td class="playfairIntro-td">C</td>
          <td class="playfairIntro-td"></td>
          <td class="playfairIntro-td"></td>
          <td class="playfairIntro-td playfairIntro-td-background">M</td>
        </tr>
      </table>
    </td>
  </tr>
  <tr>
    <td class="playfairIntro-td"></td>
  </tr>
  <tr>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
  </tr>
</table>
<p>
Les deux lettres définissent alors les deux coins d’un rectangle, représenté en rouge dans l’exemple de grille (incomplète) ci-contre. Pour chiffrer “MO”, on remplace alors le M et le O par les lettres situées aux 2 autres coins du rectangle, en prenant pour chaque lettre du bigramme d’origine la lettre du coin situé sur la même ligne, donc C pour M et R pour O dans notre exemple. Le bigramme “MO” est donc chiffré en “CR” pour cet exemple de grille. Le bigramme “RC” est chiffré “OM”, etc.
</p>
<p>
Pour déchiffrer ún bigramme, on fait exactement la même chose. Déchiffrer “CR” donne “MO”.
</p>
<p>
b) Si le M et le O sont sur la même ligne.
</p>
<table class="playfairIntro-main-table">
  <tr>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
  </tr>
  <tr>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
  </tr>
  <tr>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
  </tr>
  <tr>
    <td class="playfairIntro-td">S</td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td playfairIntro-td-background">O</td>
    <td class="playfairIntro-td">T</td>
    <td class="playfairIntro-td playfairIntro-td-background">M</td>
  </tr>
  <tr>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
  </tr>
</table>
<p>
Chaque lettre du bigramme est alors remplacée par la lettre qui se trouve juste à sa droite sur la même ligne, ou bien si l’on est sur la dernière colonne la lettre qui se trouve à la première colonne de la même ligne.
</p>
<p>
Ainsi pour l’exemple (incomplet) de grille ci-contre, le bigramme “MO” serait chiffré en “ST”
</p>
<p>
Pour déchiffrer un bigramme, il faut faire le contraire et prendre la lettre à gauche de chaque lettre. “ST” redevient alors “MO”.
</p>
<p>
c) Si le M et le O sont sur la même colonne.
</p>
<table class="playfairIntro-main-table">
  <tr>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td">K</td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
  </tr>
  <tr>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
  </tr>
  <tr>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td playfairIntro-td-background">M</td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
  </tr>
  <tr>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td">T</td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
  </tr>
  <tr>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td playfairIntro-td-background">O</td>
    <td class="playfairIntro-td"></td>
    <td class="playfairIntro-td"></td>
  </tr>
</table>
<p>
Le principe est similaire, sauf que pour chiffrer chaque lettre du bigramme, on prend la lettre juste en dessous (ou sur la première ligne si on est déjà en bas), et pour déchiffrer, on fait l’inverse.
</p>
<p>
Dans l’exemple (incomplet) de grille ci-contre, le bigramme “MO” est chiffré en “TK”.
</p>


</body>
</html>