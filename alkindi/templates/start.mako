!function () {
  var mainElement = document.getElementById('main');
  function loadError () {
    var errorElement = document.getElementById('error');
    mainElement.innerHTML = '';
    errorElement.style.display = 'initial';
  }
  if (typeof System !== 'object' || typeof System.import !== 'function') {
    // Redirect to ?nocdn, if not already there.
    if (window.location.search === "") {
      window.location.search = '?nocdn';
    } else {
      loadError();
    }
    return;
  }
  System.import('alkindi-frontend').then(function (Frontend) {
    Frontend.run(${h.to_json(frontend_config)}, mainElement);
  }).catch(function (ex) {
    if (typeof console.log === 'function') {
      console.log(ex);
    }
    loadError();
  });
}();
