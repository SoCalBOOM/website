document.addEventListener('DOMContentLoaded', function() {
  if (typeof Isotope === 'undefined') {
    return;
  }

  var sections = document.querySelectorAll('.portfolio');
  sections.forEach(function(section) {
    var portfolioContainer = section.querySelector('.portfolio-container');
    var filterRoot = section.querySelector('#portfolio-flters, .portfolio-filters');
    if (!portfolioContainer || !filterRoot) {
      return;
    }

    var iso = new Isotope(portfolioContainer, {
      itemSelector: '.portfolio-item',
      layoutMode: 'fitRows',
      filter: '.filter-all'
    });

    function applyFilter(filterValue) {
      var targetFilter = filterValue || '.filter-all';
      var targetButton = filterRoot.querySelector('li[data-filter="' + targetFilter + '"]');
      var active = filterRoot.querySelector('.filter-active');
      if (active) {
        active.classList.remove('filter-active');
      }
      if (targetButton) {
        targetButton.classList.add('filter-active');
      }
      iso.arrange({ filter: targetFilter });
    }

    filterRoot.querySelectorAll('li[data-filter]').forEach(function(filterButton) {
      filterButton.addEventListener('click', function() {
        applyFilter(this.getAttribute('data-filter'));
      });
    });

    section.querySelectorAll('.portfolio-wrap[data-filter-trigger]').forEach(function(card) {
      card.addEventListener('click', function(e) {
        if (e.target.closest('a')) {
          return;
        }
        applyFilter(card.getAttribute('data-filter-trigger'));
      });
    });
  });
});
