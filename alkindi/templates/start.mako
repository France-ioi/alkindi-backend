!function () {
  var mainElement = document.getElementById('main');
  function loadError () {
    var errorElement = document.getElementById('error');
    mainElement.innerHTML = '';
    errorElement.style.display = 'initial';
  }
  if (typeof Alkindi !== 'object' || typeof Alkindi.run !== 'function') {
    // Redirect to ?nocdn, if not already there.
    if (window.location.search === "") {
      window.location.search = '?nocdn';
    } else {
      loadError();
    }
    return;
  }
  try {
    Alkindi.run(${h.to_json(frontend_config)}, mainElement);
  } catch (ex) {
    if (typeof console.log === 'function') {
      console.log(ex);
    }
    loadError();
  }
}();
