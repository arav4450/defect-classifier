const form = document.querySelector('#classifier-form');
const imageInput = document.querySelector('#image-input');
const dropzone = document.querySelector('#dropzone');
const preview = document.querySelector('#preview');
const selectedFile = document.querySelector('#selected-file');
const formMessage = document.querySelector('#form-message');
const resultsEmpty = document.querySelector('#results-empty');
const resultsList = document.querySelector('#results-list');
const resultMeta = document.querySelector('#result-meta');
const analyzeButton = document.querySelector('#analyze-button');
const selectAllButton = document.querySelector('#select-all');
const customLabel = document.querySelector('#custom-label');
const addLabelButton = document.querySelector('#add-label');
const ratingButtons = document.querySelectorAll('.rating-button');
const feedbackComment = document.querySelector('#feedback-comment');
const submitFeedbackButton = document.querySelector('#submit-feedback');
const feedbackMessage = document.querySelector('#feedback-message');
const refreshMetricsButton = document.querySelector('#refresh-metrics');
let lastRequestId = null;
let selectedRating = null;

function showFile(file) {
  if (!file) return;
  if (!file.type.startsWith('image/')) {
    formMessage.textContent = 'Please choose a JPG, PNG, or WebP image.';
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    preview.src = reader.result;
    dropzone.classList.add('has-preview');
    selectedFile.textContent = `${file.name} · ${(file.size / 1024).toFixed(0)} KB`;
    formMessage.textContent = '';
  };
  reader.readAsDataURL(file);
}

imageInput.addEventListener('change', () => showFile(imageInput.files[0]));
['dragenter', 'dragover'].forEach((eventName) => dropzone.addEventListener(eventName, (event) => {
  event.preventDefault();
  dropzone.classList.add('dragging');
}));
['dragleave', 'drop'].forEach((eventName) => dropzone.addEventListener(eventName, (event) => {
  event.preventDefault();
  dropzone.classList.remove('dragging');
}));
dropzone.addEventListener('drop', (event) => {
  const file = event.dataTransfer.files[0];
  if (file) {
    imageInput.files = event.dataTransfer.files;
    showFile(file);
  }
});

selectAllButton.addEventListener('click', () => {
  const checkboxes = document.querySelectorAll('input[name="label"]');
  const shouldCheck = [...checkboxes].some((checkbox) => !checkbox.checked);
  checkboxes.forEach((checkbox) => { checkbox.checked = shouldCheck; });
  selectAllButton.textContent = shouldCheck ? 'Clear all' : 'Select all';
});

addLabelButton.addEventListener('click', () => {
  const value = customLabel.value.trim();
  if (!value) return;
  const option = document.createElement('label');
  option.className = 'label-option';
  option.innerHTML = `<input type="checkbox" name="label" value=""><span class="checkmark">✓</span><span></span>`;
  option.querySelector('input').value = value;
  option.querySelector('input').checked = true;
  option.querySelector('span:last-child').textContent = value;
  document.querySelector('#label-list').append(option);
  customLabel.value = '';
});
customLabel.addEventListener('keydown', (event) => { if (event.key === 'Enter') { event.preventDefault(); addLabelButton.click(); } });

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const labels = [...document.querySelectorAll('input[name="label"]:checked')].map((input) => input.value);
  if (!imageInput.files[0]) { formMessage.textContent = 'Choose an image before analyzing.'; return; }
  if (labels.length < 2) { formMessage.textContent = 'Select at least two labels to compare.'; return; }

  const payload = new FormData();
  payload.append('image', imageInput.files[0]);
  payload.append('labels', labels.join(','));
  analyzeButton.disabled = true;
  analyzeButton.querySelector('span').textContent = 'Analyzing...';
  formMessage.textContent = '';
  resultMeta.textContent = 'Running model';

  try {
    const response = await fetch('/predict', { method: 'POST', body: payload });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || 'Prediction failed.');
    renderResults(body);
  } catch (error) {
    formMessage.textContent = error.message;
    resultMeta.textContent = 'Unable to analyze';
  } finally {
    analyzeButton.disabled = false;
    analyzeButton.querySelector('span').textContent = 'Analyze image';
  }
});

function renderResults(body) {
  const predictions = [...body.predictions].sort((a, b) => b.score - a.score);
  resultsEmpty.style.display = 'none';
  resultsList.innerHTML = predictions.map((prediction, index) => {
    const score = Math.round(prediction.score * 100);
    return `<div class="result-row"><span class="result-rank">0${index + 1}</span><span class="result-label">${escapeHtml(prediction.label)}</span><span class="result-score">${score}%</span><div class="result-track"><div class="result-bar" style="width: ${score}%"></div></div></div>`;
  }).join('');
  resultMeta.textContent = body.cached ? 'Cached result' : `${predictions.length} labels compared`;
  lastRequestId = body.request_id;
  ratingButtons.forEach((button) => { button.disabled = false; });
  feedbackComment.disabled = false;
}

ratingButtons.forEach((button) => button.addEventListener('click', () => {
  selectedRating = Number(button.dataset.rating);
  ratingButtons.forEach((item) => item.classList.toggle('selected', item === button));
  submitFeedbackButton.disabled = false;
  feedbackMessage.textContent = '';
}));

submitFeedbackButton.addEventListener('click', async () => {
  if (!lastRequestId || selectedRating === null) return;
  const payload = new FormData();
  payload.append('request_id', lastRequestId);
  payload.append('rating', selectedRating);
  payload.append('comment', feedbackComment.value.trim());
  submitFeedbackButton.disabled = true;
  feedbackMessage.textContent = 'Sending...';
  try {
    const response = await fetch('/feedback', { method: 'POST', body: payload });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || 'Could not send feedback.');
    feedbackMessage.textContent = 'Feedback recorded.';
    feedbackComment.value = '';
  } catch (error) {
    feedbackMessage.textContent = error.message;
    submitFeedbackButton.disabled = false;
  }
});

async function loadMetrics() {
  refreshMetricsButton.disabled = true;
  metricsStatus.textContent = 'Refreshing metrics...';
  try {
    const response = await fetch('/metrics');
    if (!response.ok) throw new Error('Metrics unavailable');
    const text = await response.text();
    const requests = metricValue(text, 'predict_requests_total');
    const errors = metricValue(text, 'predict_errors_total');
    const latencySum = metricValue(text, 'predict_latency_seconds_sum');
    const latencyCount = metricValue(text, 'predict_latency_seconds_count');
    const cost = metricValue(text, 'predict_estimated_cost_usd_total');
    document.querySelector('#metric-requests').textContent = formatNumber(requests);
    document.querySelector('#metric-errors').textContent = formatNumber(errors);
    document.querySelector('#metric-latency').textContent = latencyCount ? `${(latencySum / latencyCount).toFixed(2)}s` : '--';
    document.querySelector('#metric-cost').textContent = cost === null ? '--' : `₹${cost.toFixed(4)}`;
    metricsStatus.textContent = 'Updated just now';
  } catch (error) {
    metricsStatus.textContent = error.message;
  } finally {
    refreshMetricsButton.disabled = false;
  }
}

const metricsStatus = document.querySelector('#metrics-status');
function metricValue(text, metricName) {
  const lines = text.split('\n').filter((item) => item.startsWith(metricName) && !item.startsWith(`${metricName}_`));
  if (!lines.length) return null;
  const values = lines.map((line) => Number(line.substring(line.lastIndexOf(' ') + 1)));
  return values.every((value) => Number.isFinite(value)) ? values.reduce((total, value) => total + value, 0) : null;
}
function formatNumber(value) { return value === null ? '--' : Math.round(value).toLocaleString(); }
refreshMetricsButton.addEventListener('click', loadMetrics);
loadMetrics();

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[character]));
}
