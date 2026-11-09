const gallery = document.querySelector('.author__gallery');

if (gallery) {
  const slides = [...gallery.querySelectorAll('.author__gallery-frame > a')];
  const controls = [...gallery.querySelectorAll('.author__gallery-controls button')];
  let active = 0;

  function showSlide(next) {
    slides[active].classList.remove('is-active');
    slides[active].inert = true;
    controls[active].setAttribute('aria-pressed', 'false');
    active = next;
    slides[active].inert = false;
    slides[active].classList.add('is-active');
    controls[active].setAttribute('aria-pressed', 'true');
  }

  controls.forEach((button, index) => {
    button.addEventListener('click', () => showSlide(index));
  });

  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    window.setInterval(() => {
      if (!gallery.matches(':hover, :focus-within')) {
        showSlide((active + 1) % slides.length);
      }
    }, 4000);
  }
}
