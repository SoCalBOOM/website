document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('#navbar .nav-dropdown').forEach(function(dropdown) {
    var caretButton = dropdown.querySelector('.nav-dropdown-caret');
    if (!caretButton) return;

    caretButton.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      var isOpen = dropdown.getAttribute('data-open') === 'true';
      dropdown.setAttribute('data-open', isOpen ? 'false' : 'true');
      caretButton.setAttribute('aria-expanded', isOpen ? 'false' : 'true');
    });
  });
});
