/**
 * Media Flow — Apple.com Interactive & Kinetic Motion Script
 */

document.addEventListener('DOMContentLoaded', () => {
  initScrollReveal();
  initMetricCounters();
  initThemeMockupToggle();
  init3DParallaxTilt();
  initConverterSimulator();
  initAudioWaveform();
  initStickySubnav();
});

/* ==========================================================================
   1. SCROLL REVEAL ANIMATIONS (INTERSECTION OBSERVER)
   ========================================================================== */
function initScrollReveal() {
  const revealElements = document.querySelectorAll('.reveal-on-scroll');
  if (!('IntersectionObserver' in window)) {
    revealElements.forEach(el => el.classList.add('is-visible'));
    return;
  }

  const observer = new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        obs.unobserve(entry.target);
      }
    });
  }, {
    threshold: 0.15,
    rootMargin: '0px 0px -40px 0px'
  });

  revealElements.forEach(el => observer.observe(el));
}

/* ==========================================================================
   2. ANIMATED METRIC COUNTERS
   ========================================================================== */
function initMetricCounters() {
  const metrics = document.querySelectorAll('.metric-num');
  if (!('IntersectionObserver' in window)) return;

  const observer = new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const targetValue = el.getAttribute('data-target');
        if (targetValue) {
          animateCounter(el, targetValue);
        }
        obs.unobserve(el);
      }
    });
  }, { threshold: 0.5 });

  metrics.forEach(m => observer.observe(m));
}

function animateCounter(el, target) {
  // Check if string contains suffix like 'x' or '%'
  const hasX = target.includes('x');
  const hasPercent = target.includes('%');
  const num = parseInt(target.replace(/\D/g, ''), 10) || 0;
  let current = 0;
  const duration = 1200;
  const stepTime = 25;
  const steps = duration / stepTime;
  const increment = num / steps;

  const timer = setInterval(() => {
    current += increment;
    if (current >= num) {
      current = num;
      clearInterval(timer);
    }
    let display = Math.round(current).toString();
    if (hasX) display += 'x';
    if (hasPercent) display += '%';
    el.textContent = display;
  }, stepTime);
}

/* ==========================================================================
   3. THEME MOCKUP TOGGLE (DARK / LIGHT SCREENSHOT)
   ========================================================================== */
function initThemeMockupToggle() {
  const buttons = document.querySelectorAll('.theme-opt-btn');
  const mockupImg = document.getElementById('mockupImg');
  if (!mockupImg || !buttons.length) return;

  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      buttons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const mode = btn.getAttribute('data-theme');
      if (mode === 'light') {
        mockupImg.src = 'assets/app-light.png';
      } else {
        mockupImg.src = 'assets/app-dark.png';
      }
    });
  });
}

/* ==========================================================================
   4. INTERACTIVE 3D TILT WITH SPOTLIGHT EFFECT
   ========================================================================== */
function init3DParallaxTilt() {
  const cards = document.querySelectorAll('.bento-card, .showcase-card, .dl-card');
  cards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      const deltaX = (x - centerX) / centerX;
      const deltaY = (y - centerY) / centerY;

      const rotateX = -deltaY * 4;
      const rotateY = deltaX * 4;

      card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-3px)`;
    });

    card.addEventListener('mouseleave', () => {
      card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0px)';
    });
  });
}

/* ==========================================================================
   5. LIVE INTERACTIVE CONVERTER PLAYGROUND SIMULATOR
   ========================================================================== */
function initConverterSimulator() {
  const fileInputZone = document.getElementById('simFileZone');
  const fileNameDisplay = document.getElementById('simFileName');
  const formatSelect = document.getElementById('simFormatSelect');
  const btnStart = document.getElementById('btnSimStart');
  const progressBox = document.getElementById('simProgressBox');
  const progressBar = document.getElementById('simProgressBar');
  const progressText = document.getElementById('simProgressText');
  const speedText = document.getElementById('simSpeedText');

  if (!btnStart) return;

  const sampleFiles = [
    { name: 'clip_4k_cinematic.mov', size: '284 MB', defFmt: 'MP4' },
    { name: 'podcast_episodio_34.wav', size: '112 MB', defFmt: 'FLAC' },
    { name: 'grabacion_entrevista.m4a', size: '45 MB', defFmt: 'MP3' },
    { name: 'fotografia_raw.png', size: '18 MB', defFmt: 'WEBP' },
  ];
  let currentFileIdx = 0;

  if (fileInputZone) {
    fileInputZone.addEventListener('click', () => {
      currentFileIdx = (currentFileIdx + 1) % sampleFiles.length;
      const f = sampleFiles[currentFileIdx];
      fileNameDisplay.textContent = `${f.name} (${f.size})`;
      formatSelect.value = f.defFmt;
    });
  }

  btnStart.addEventListener('click', () => {
    btnStart.disabled = true;
    btnStart.textContent = 'Procesando con GPU...';
    progressBox.style.display = 'block';
    progressBar.style.width = '0%';

    let percent = 0;
    const interval = setInterval(() => {
      percent += Math.floor(Math.random() * 8) + 4;
      if (percent >= 100) {
        percent = 100;
        clearInterval(interval);
        progressBar.style.width = '100%';
        progressText.textContent = '¡Completado con éxito (0.8s)!';
        speedText.textContent = '100% finalizado';
        btnStart.textContent = '✨ Archivo Convertido';
        setTimeout(() => {
          btnStart.disabled = false;
          btnStart.textContent = 'Iniciar Nueva Conversión';
        }, 2000);
      } else {
        progressBar.style.width = `${percent}%`;
        progressText.textContent = `Procesando: ${percent}%`;
        const speed = Math.floor(Math.random() * 80) + 420;
        speedText.textContent = `${speed} fps • 42 MB/s`;
      }
    }, 70);
  });
}

/* ==========================================================================
   6. INTERACTIVE AUDIO WAVEFORM EQUALIZER
   ========================================================================== */
function initAudioWaveform() {
  const container = document.getElementById('waveformBox');
  if (!container) return;

  container.innerHTML = '';
  const totalBars = 32;

  for (let i = 0; i < totalBars; i++) {
    const bar = document.createElement('div');
    bar.className = 'waveform-bar';
    const randomHeight = Math.floor(Math.random() * 70) + 20;
    bar.style.height = `${randomHeight}px`;
    bar.style.animationDuration = `${0.6 + Math.random() * 1.2}s`;
    bar.style.animationDelay = `${Math.random() * 0.8}s`;
    container.appendChild(bar);
  }
}

/* ==========================================================================
   7. STICKY SUBNAV ACTIVE SPY
   ========================================================================== */
function initStickySubnav() {
  const subnav = document.querySelector('.apple-subnav');
  const links = document.querySelectorAll('.subnav-links a');
  if (!subnav || !links.length) return;

  const sections = Array.from(links).map(link => {
    const id = link.getAttribute('href');
    if (id && id.startsWith('#')) {
      return document.querySelector(id);
    }
    return null;
  }).filter(Boolean);

  window.addEventListener('scroll', () => {
    const scrollPos = window.scrollY + 120;
    sections.forEach((sec, idx) => {
      if (sec.offsetTop <= scrollPos && (sec.offsetTop + sec.offsetHeight) > scrollPos) {
        links.forEach(l => l.classList.remove('active'));
        if (links[idx]) links[idx].classList.add('active');
      }
    });
  }, { passive: true });
}
