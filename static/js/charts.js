document.addEventListener('DOMContentLoaded', () => {
  const studyCtx = document.getElementById('studyChart');
  if (studyCtx) {
    new Chart(studyCtx, {
      type: 'line',
      data: {
        labels: JSON.parse(studyCtx.dataset.labels || '[]'),
        datasets: [
          {
            label: 'Study Hours',
            data: JSON.parse(studyCtx.dataset.values || '[]'),
            borderColor: '#2563eb',
            backgroundColor: 'rgba(37, 99, 235, 0.14)',
            fill: true,
            tension: 0.35,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: '#475569' } },
          y: { ticks: { color: '#475569' }, beginAtZero: true },
        },
      },
    });
  }

  const perfCtx = document.getElementById('performanceChart');
  if (perfCtx) {
    new Chart(perfCtx, {
      type: 'bar',
      data: {
        labels: JSON.parse(perfCtx.dataset.labels || '[]'),
        datasets: [
          {
            label: 'Average Score',
            data: JSON.parse(perfCtx.dataset.values || '[]'),
            backgroundColor: '#3b82f6',
            borderRadius: 12,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: '#475569' } },
          y: { ticks: { color: '#475569' }, beginAtZero: true, max: 100 },
        },
      },
    });
  }
});
