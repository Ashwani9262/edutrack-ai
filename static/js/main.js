const activeSession = {
  startTime: null,
  duration: 0,
  focused: 1,
  tabSwitches: 0,
};

function toggleClassSelection(role) {
  document.querySelector('#student-select').classList.toggle('hidden', role !== 'student');
  document.querySelector('#teacher-select').classList.toggle('hidden', role !== 'teacher');
}

function startSession() {
  fetch('/session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'start' }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.status === 'started') {
        activeSession.startTime = Date.now();
        activeSession.focused = document.visibilityState === 'visible' ? 1 : 0;
        activeSession.tabSwitches = 0;
        window.addEventListener('visibilitychange', () => {
          if (document.visibilityState !== 'visible') {
            activeSession.tabSwitches += 1;
          }
        });
        alert('Study session started. Keep the tab active for focus points.');
      }
    });
}

function stopSession() {
  if (!activeSession.startTime) {
    alert('No session has been started.');
    return;
  }
  const elapsed = Math.max(0, Math.floor((Date.now() - activeSession.startTime) / 1000));
  fetch('/session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action: 'stop',
      duration: elapsed,
      focused: activeSession.focused,
      tab_switches: activeSession.tabSwitches,
    }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.status === 'stopped') {
        alert(`Session completed! You earned ${data.earned_points} points.`);
        window.location.reload();
      }
    });
}
