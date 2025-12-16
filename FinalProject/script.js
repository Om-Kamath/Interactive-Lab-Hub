let subwayData = null;
let scheduleData = [];
let serviceStatus = 'Awaiting calendar sign-in';
let googleConfig = {};
let tokenClient = null;
let accessToken = null;
let connectedEmail = null;
let selectedEventId = null;
let currentRouteEvent = null;
let currentRouteLabel = '';
let planRequestToken = 0;
const routeCache = new Map();
const ROUTE_CACHE_STORAGE_KEY = 'planner_route_cache_v1';
const ROUTE_CACHE_TTL_MS = 30 * 60 * 1000; // 30 minutes
let currentStops = [];
let currentTransfers = [];
let currentStopIndex = 0;
let weatherData = {
  temp: '--°',
  condition: 'Loading weather...',
  icon: '⛅'
};
let signOutButton = null;

const TOKEN_STORAGE_KEY = 'planner_google_token';
const TOKEN_EXPIRY_KEY = 'planner_google_token_expiry';
const USER_EMAIL_KEY = 'planner_google_email';

const FIXED_ORIGIN = {
  label: 'Grand Central Terminal',
  lat: 40.7527,
  lon: -73.9772,
};

let userLocation = { ...FIXED_ORIGIN };
let isRouteLoading = false;
const LED_COUNT = 10;
const MAX_DEPARTURE_ADVANCE_MS = 90 * 60 * 1000; // 90 minutes before event
const MAX_EARLY_ARRIVAL_MS = 45 * 60 * 1000; // 45 minutes before event

function loadRouteCacheFromStorage() {
  try {
    const raw = localStorage.getItem(ROUTE_CACHE_STORAGE_KEY);
    if (!raw) return;
    const data = JSON.parse(raw);
    const now = Date.now();
    routeCache.clear();
    Object.entries(data).forEach(([key, entry]) => {
      if (!entry || !entry.value) return;
      const ts = typeof entry.ts === 'number' ? entry.ts : 0;
      if (now - ts > ROUTE_CACHE_TTL_MS) return;
      if (!isValidRoute(entry.value)) return;
      routeCache.set(key, { value: entry.value, ts });
    });
    console.info('[route-cache] loaded', routeCache.size, 'entries from storage');
  } catch (err) {
    console.warn('Unable to load route cache from storage', err);
  }
}

function persistRouteCacheToStorage() {
  try {
    const payload = {};
    for (const [key, entry] of routeCache.entries()) {
      payload[key] = entry;
    }
    localStorage.setItem(ROUTE_CACHE_STORAGE_KEY, JSON.stringify(payload));
    console.info('[route-cache] persisted', routeCache.size, 'entries to storage');
  } catch (err) {
    console.warn('Unable to persist route cache to storage', err);
  }
}

function cleanupRouteCache() {
  const now = Date.now();
  let removed = false;
  for (const [key, entry] of routeCache.entries()) {
    if (!entry || typeof entry.ts !== 'number' || now - entry.ts > ROUTE_CACHE_TTL_MS) {
      routeCache.delete(key);
      removed = true;
      continue;
    }
    if (!isValidRoute(entry.value)) {
      routeCache.delete(key);
      removed = true;
    }
  }
  if (removed) persistRouteCacheToStorage();
}

function getCachedRoute(cacheKey) {
  cleanupRouteCache();
  const entry = routeCache.get(cacheKey);
  if (!entry) return null;
  if (!isValidRoute(entry.value)) {
    routeCache.delete(cacheKey);
    persistRouteCacheToStorage();
    console.info('[route-cache] invalid entry pruned for', cacheKey);
    return null;
  }
  console.info('[route-cache] hit for', cacheKey);
  return entry.value;
}

function setCachedRoute(cacheKey, payload) {
  if (!isValidRoute(payload)) {
    console.info('[route-cache] not caching invalid payload for', cacheKey);
    return;
  }
  routeCache.set(cacheKey, { value: payload, ts: Date.now() });
  persistRouteCacheToStorage();
}

function updateClock() {
  const now = new Date();
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const timeString = `${hours}:${minutes}`;
  
  // Update main clock
  const mainClock = document.getElementById('current-time');
  if (mainClock) mainClock.textContent = timeString;
  
  // Update small clock on route screen
  const smallClock = document.getElementById('small-clock');
  if (smallClock) smallClock.textContent = timeString;

  const options = { weekday: 'long', month: 'long', day: 'numeric' };
  const dateEl = document.getElementById('current-date');
  if (dateEl) dateEl.textContent = now.toLocaleDateString('en-US', options);
}

function setScheduleStatus(message, isError = false) {
  const status = document.getElementById('schedule-status');
  status.textContent = message;
  status.classList.toggle('error', isError);
}

function scrollEventIntoView(eventId) {
  const el = document.querySelector(`[data-event-id="${eventId}"]`);
  if (!el) return;
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function updateActiveEventTitle(event) {
  const el = document.getElementById('active-event-title');
  if (!el) return;
  if (!event) {
    el.textContent = 'No event selected';
    return;
  }
  el.textContent = event.title || 'Calendar Event';
}

async function readJsonSafely(response) {
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch (error) {
    return { raw: text };
  }
}

function renderSchedule() {
  const list = document.getElementById('event-list');
  list.innerHTML = '';

  if (!scheduleData.length) {
    selectedEventId = null;
    updateActiveEventTitle(null);
    list.innerHTML = '<div class="empty-state">Sign in to Google Calendar to load the next event.</div>';
    return;
  }

  let currentDay = null;

  scheduleData.forEach(event => {
    if (event.dayKey && event.dayKey !== currentDay) {
      currentDay = event.dayKey;
      const divider = document.createElement('div');
      divider.className = 'day-divider';
      divider.innerHTML = `<span>${event.dayHeading}</span>`;
      list.appendChild(divider);
    }

    const item = document.createElement('div');
    const isSelected = event.id === selectedEventId;
    item.className = `event-item${isSelected ? ' selected' : ''}`;
    item.dataset.eventId = event.id;
    item.addEventListener('click', () => handleEventSelection(event.id));

    const locationText = event.hasLocation ? event.location : 'No location set';
    const locationClass = event.hasLocation ? 'event-location' : 'event-location no-location';
    const noLocationTag = event.hasLocation ? '' : '<span class="no-location-tag">No location</span>';
    const timeText = event.isAllDay ? 'All day' : event.timeLabel;

    item.innerHTML = `
      <div class="event-time-block">
        <div class="event-date-label">${event.dateLabel}</div>
        <div class="event-time-label ${event.isAllDay ? 'all-day' : ''}">${timeText}</div>
      </div>
      <div class="event-details">
        <div class="event-title">${event.title}</div>
        <div class="${locationClass}">${locationText} ${noLocationTag}</div>
      </div>
    `;
    list.appendChild(item);
  });
}

function renderWeather() {
  const container = document.getElementById('weather-widget');
  container.innerHTML = `
    <div class="weather-icon">${weatherData.icon}</div>
    <div class="weather-info">
      <div class="weather-temp">${weatherData.temp}</div>
      <div class="weather-condition">${weatherData.condition}</div>
    </div>
  `;
}

async function fetchWeather() {
  try {
    const resp = await fetch('/api/weather');
    if (!resp.ok) {
      throw new Error('Weather API error');
    }
    const data = await resp.json();
    const tempF = typeof data.temperature_f === 'number' ? `${Math.round(data.temperature_f)}°F` : null;
    const tempC = typeof data.temperature_c === 'number' ? `${Math.round(data.temperature_c)}°C` : null;
    weatherData = {
      temp: tempF || tempC || '--°',
      condition: data.condition || 'Weather unavailable',
      icon: data.icon || '⛅',
    };
  } catch (error) {
    console.error('Weather fetch failed', error);
    weatherData = {
      temp: '--°',
      condition: 'Weather unavailable',
      icon: '⚠️',
    };
  } finally {
    renderWeather();
  }
}

function updateAuthUI(isConnected = Boolean(accessToken)) {
  const button = document.getElementById('google-login-btn');
  if (!button) return;
  if (isConnected) {
    const label = connectedEmail ? `Connected as ${connectedEmail}` : 'Google Calendar Connected';
    button.textContent = label;
    button.classList.add('signed-in');
    button.disabled = true;
    if (signOutButton) {
      signOutButton.style.display = 'inline-flex';
      signOutButton.disabled = false;
    }
  } else {
    button.textContent = 'Sign in';
    button.classList.remove('signed-in');
    button.disabled = !googleConfig.googleClientId;
    if (signOutButton) {
      signOutButton.style.display = 'none';
      signOutButton.disabled = true;
    }
  }
}

function persistSession(token, expiresInSeconds, email) {
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
    const expiresMs = Date.now() + (expiresInSeconds || 1800) * 1000;
    localStorage.setItem(TOKEN_EXPIRY_KEY, String(expiresMs));
    if (email) {
      localStorage.setItem(USER_EMAIL_KEY, email);
    } else {
      localStorage.removeItem(USER_EMAIL_KEY);
    }
    updateActiveEventTitle(getEventById(selectedEventId));
  } catch (error) {
    console.warn('Unable to persist Google token', error);
  }
}

function clearStoredSession() {
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(TOKEN_EXPIRY_KEY);
    localStorage.removeItem(USER_EMAIL_KEY);
  } catch (error) {
    console.warn('Unable to clear stored session', error);
  }
}

function restoreStoredSession() {
  try {
    const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY);
    const expiry = Number(localStorage.getItem(TOKEN_EXPIRY_KEY) || 0);
    if (!storedToken || !expiry || Date.now() >= expiry) {
      clearStoredSession();
      updateAuthUI(false);
      return;
    }

    accessToken = storedToken;
    connectedEmail = localStorage.getItem(USER_EMAIL_KEY);
    updateAuthUI(true);
    updateActiveEventTitle(getEventById(selectedEventId));
    setScheduleStatus('Restored Google Calendar session.');
    fetchUpcomingEvents();
  } catch (error) {
    console.warn('Failed to restore Google session', error);
    clearStoredSession();
    updateAuthUI(false);
  }
}

async function fetchUserEmail(token) {
  try {
    const resp = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!resp.ok) return null;
    const data = await resp.json();
    return data.email || null;
  } catch (error) {
    console.warn('Unable to fetch user email', error);
    return null;
  }
}

async function handleTokenSuccess(response) {
  accessToken = response.access_token;
  const expiresIn = response.expires_in || 1800;
  connectedEmail = await fetchUserEmail(accessToken);
  persistSession(accessToken, expiresIn, connectedEmail);
  updateAuthUI(true);
  setScheduleStatus('Loaded your Google Calendar.');
  fetchUpcomingEvents();
}

function handleSignOut() {
  accessToken = null;
  connectedEmail = null;
  selectedEventId = null;
  subwayData = null;
  renderSubwayInfo();
  calculateTimeToLeave();
  clearStoredSession();
  updateAuthUI(false);
  scheduleData = [];
  renderSchedule();
  setScheduleStatus('Signed out of Google Calendar.');
}

function renderServiceStatus(message = serviceStatus) {
  serviceStatus = message;
  const el = document.getElementById('service-status');
  el.textContent = message;

  if (message.toLowerCase().includes('good')) {
    el.style.color = 'var(--success-color)';
    el.style.background = 'rgba(76, 217, 100, 0.1)';
  } else if (message.toLowerCase().includes('error')) {
    el.style.color = '#FF3B30';
    el.style.background = 'rgba(255, 59, 48, 0.15)';
  } else {
    el.style.color = 'var(--warning-color)';
    el.style.background = 'rgba(255, 214, 10, 0.1)';
  }
}

function renderStopDetail() {
  const nameEl = document.getElementById('current-stop-name');
  const posEl = document.getElementById('stop-position');
  const transferEl = document.getElementById('stop-transfer');
  const badgeEl = document.getElementById('stop-line-badge');
  const nextHint = document.getElementById('stop-next-hint');
  if (!nameEl || !posEl || !transferEl || !badgeEl) return;

  if (!currentStops.length || currentStopIndex >= currentStops.length) {
    nameEl.textContent = 'Select a route';
    posEl.textContent = '--';
    transferEl.textContent = 'No transfer';
    badgeEl.textContent = '-';
    badgeEl.style.backgroundColor = 'var(--accent-color)';
    if (nextHint) nextHint.style.visibility = 'hidden';
    updateLEDStrip([]);
    return;
  }

  const stopName = currentStops[currentStopIndex];
  nameEl.textContent = stopName;
  posEl.textContent = `Stop ${currentStopIndex + 1} of ${currentStops.length}`;

  // Determine line at this stop based on transfers.
  let activeLine = subwayData?.next_train?.line || 'F';
  for (let i = 0; i <= currentStopIndex; i += 1) {
    const t = currentTransfers.find(tr => tr.at_station === currentStops[i]);
    if (t) activeLine = t.to_line;
  }
  const color = getLineColor(activeLine);
  badgeEl.textContent = activeLine;
  badgeEl.style.backgroundColor = color;
  badgeEl.style.boxShadow = `0 0 24px ${color.replace('rgb', 'rgba').replace(')', ', 0.4)')}`;

  const transfer = currentTransfers.find(tr => tr.at_station === stopName);
  if (transfer) {
    transferEl.textContent = `Transfer to ${transfer.to_line}`;
  } else {
    transferEl.textContent = 'No transfer';
  }
  if (nextHint) {
    nextHint.style.visibility = currentStopIndex < currentStops.length - 1 ? 'visible' : 'hidden';
  }
  updateLEDStrip(currentStops, currentStopIndex);
}
function calculateTimeToLeave() {
  const timerEl = document.getElementById('leave-timer');
  const countdownEl = document.getElementById('leave-countdown');

  if (!subwayData || !subwayData.next_train) {
    timerEl.textContent = '--:--';
    countdownEl.textContent = 'Waiting for route';
    countdownEl.style.color = 'var(--text-secondary)';
    return;
  }

  const departureDate = computeDepartureDate(subwayData.next_train);
  if (!departureDate) {
    timerEl.textContent = '--:--';
    countdownEl.textContent = 'Waiting for schedule';
    countdownEl.style.color = 'var(--text-secondary)';
    return;
  }
  const eventDate = currentRouteEvent ? normalizeEventDate(currentRouteEvent.rawStart) : null;

  const walkingMinutes = subwayData.station_access.walking_time_minutes;
  const leaveDate = new Date(departureDate.getTime() - walkingMinutes * 60000);
  const leaveLabel = leaveDate.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  timerEl.textContent = leaveLabel;

  const now = new Date();
  const diffMs = leaveDate - now;
  const diffMins = Math.ceil(diffMs / 60000);
  const isSameDay = eventDate ? eventDate.toDateString() === now.toDateString() : true;
  const leaveDateLabel = leaveDate.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });

  if (!isSameDay || diffMins > 120) {
    countdownEl.textContent = `Leave ${leaveDateLabel} at ${leaveLabel}`;
    countdownEl.style.color = 'var(--warning-color)';
  } else if (diffMins > 0) {
    countdownEl.textContent = `Leave in ${diffMins} min`;
    countdownEl.style.color = 'var(--success-color)';
  } else if (diffMins > -5) {
    countdownEl.textContent = 'Leave NOW!';
    countdownEl.style.color = '#FF3B30';
  } else {
    countdownEl.textContent = 'Train Departed';
    countdownEl.style.color = 'var(--text-secondary)';
  }
}

function renderSubwayInfo() {
  if (!subwayData) {
    document.getElementById('line-badge').textContent = '-';
    document.getElementById('line-badge').style.backgroundColor = 'var(--accent-color)';
    document.getElementById('line-badge').style.boxShadow = 'none';
    const lb2 = document.getElementById('line-badge-2');
    const sep = document.getElementById('line-separator');
    if (lb2) {
      lb2.textContent = '-';
      lb2.style.backgroundColor = 'var(--surface-color)';
      lb2.style.boxShadow = 'none';
      lb2.style.display = 'none';
    }
    if (sep) {
      sep.style.display = 'none';
    }
    document.getElementById('direction').textContent = 'Awaiting route';
    document.getElementById('departure-time').textContent = '--:--';
    document.getElementById('walking-time').textContent = '-- min';
    document.getElementById('walking-dist').textContent = '-- m';
    document.getElementById('route-line-detail').textContent = 'Waiting for event selection';
    document.getElementById('transfer-detail').textContent = 'No transfers';
    document.getElementById('arrival-detail').textContent = 'Arrival --:--';
    currentStops = [];
    currentTransfers = [];
    currentStopIndex = 0;
    renderStopDetail();
    // Update route summary
    const routeSummary = document.getElementById('route-summary');
    if (routeSummary) routeSummary.textContent = 'No route';
    const stopsCountEl = document.getElementById('stops-count');
    const routeEndpointEl = document.getElementById('route-endpoint');
    if (stopsCountEl) stopsCountEl.textContent = '-- stops';
    if (routeEndpointEl) routeEndpointEl.textContent = 'to --';
    const nextHint = document.getElementById('stop-next-hint');
    if (nextHint) nextHint.style.visibility = 'hidden';
    return;
  }

  const lineBadge = document.getElementById('line-badge');
  const currentLine = subwayData.next_train.line;
  lineBadge.textContent = currentLine;
  const lineColor = currentLine ? getLineColor(currentLine) : 'var(--accent-color)';
  const lineShadow = lineColor.replace('rgb', 'rgba').replace(')', ', 0.65)');
  lineBadge.style.backgroundColor = lineColor;
  lineBadge.style.boxShadow = `0 0 20px ${lineShadow}`;
  const lb2 = document.getElementById('line-badge-2');
  const sep = document.getElementById('line-separator');
  if (lb2) {
    const seq = buildLineSequence(subwayData);
    const second = seq.length > 1 ? seq[1] : null;
    lb2.textContent = second || '-';
    const c2 = second ? getLineColor(second) : 'var(--surface-color)';
    const s2 = c2.replace('rgb', 'rgba').replace(')', ', 0.65)');
    lb2.style.backgroundColor = c2;
    lb2.style.boxShadow = second ? `0 0 20px ${s2}` : 'none';
    lb2.style.display = second ? 'flex' : 'none';
    if (sep) {
      sep.style.display = second ? 'flex' : 'none';
    }
  }

  const eventDate = currentRouteEvent ? normalizeEventDate(currentRouteEvent.rawStart) : null;
  const todayStr = new Date().toDateString();
  const showDepartureDate = eventDate && eventDate.toDateString() !== todayStr;

  document.getElementById('direction').textContent = subwayData.next_train.direction;
  const departureTimeDisplay = formatTimeOfDay(subwayData.next_train.departure_time);
  document.getElementById('departure-time').textContent = departureTimeDisplay;

  document.getElementById('walking-time').textContent = `${subwayData.station_access.walking_time_minutes} min`;
  document.getElementById('walking-dist').textContent = `${subwayData.station_access.walking_distance_meters} m`;
  const departureDateLabel = showDepartureDate ? `${eventDate.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })} ` : '';
  const lineSeq = buildLineSequence(subwayData);
  const lineLabel = lineSeq.length ? lineSeq.join(' → ') : currentLine;
  document.getElementById('route-line-detail').textContent = `Lines: ${lineLabel} • Depart ${departureDateLabel}${departureTimeDisplay}`;
  
  // Update route summary for compact view
  const stops = (subwayData.route && subwayData.route.stops) || [];
  const routeSummary = document.getElementById('route-summary');
  if (routeSummary && stops.length >= 2) {
    routeSummary.textContent = `${stops[0]} → ${stops[stops.length - 1]}`;
  }
  // Update stops count and route endpoint for Screen 3 summary
  const stopsCountEl = document.getElementById('stops-count');
  const routeEndpointEl = document.getElementById('route-endpoint');
  if (stopsCountEl) stopsCountEl.textContent = `${stops.length} stops`;
  if (routeEndpointEl && stops.length > 0) routeEndpointEl.textContent = `to ${stops[stops.length - 1]}`;
  
  const transfers = (subwayData.route && subwayData.route.transfers) || [];
  document.getElementById('transfer-detail').textContent = renderTransfers(transfers);
  const arrivalLabelRaw = subwayData.route && subwayData.route.arrival_time ? subwayData.route.arrival_time : '--:--';
  const arrivalLabel = formatTimeOfDay(arrivalLabelRaw);
  const destinationLabel = currentRouteEvent ? (currentRouteEvent.location || 'Destination') : 'Destination';
  const showArrivalDate = eventDate && eventDate.toDateString() !== todayStr;
  const arrivalDateLabel = showArrivalDate ? `${eventDate.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })} ` : '';
  document.getElementById('arrival-detail').textContent = `Arrive ${destinationLabel}: ${arrivalDateLabel}${arrivalLabel}`;

  // Store stops/transfers for Screen 3 detail navigation.
  currentStops = stops;
  currentTransfers = transfers;
  currentStopIndex = 0;
  renderStopDetail();

  if (stops.length) {
    updateLEDStrip(stops, currentStopIndex);
  } else {
    updateLEDStrip([]);
  }
}

async function fetchConfig() {
  const resp = await fetch('/api/config');
  if (resp.ok) {
    googleConfig = await resp.json();
  }
}

function initGoogleAuth() {
  const button = document.getElementById('google-login-btn');
  signOutButton = document.getElementById('google-signout-btn');
  if (signOutButton) {
    signOutButton.addEventListener('click', handleSignOut);
    signOutButton.style.display = 'none';
    signOutButton.disabled = true;
  }

  if (!googleConfig.googleClientId) {
    button.textContent = 'Set GOOGLE_CLIENT_ID';
    button.disabled = true;
    updateAuthUI(false);
    return;
  }

  const initClient = () => {
    if (!window.google || !window.google.accounts || !window.google.accounts.oauth2) {
      setTimeout(initClient, 300);
      return;
    }

    tokenClient = window.google.accounts.oauth2.initTokenClient({
      client_id: googleConfig.googleClientId,
      scope: 'https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/userinfo.email',
      callback: async (response) => {
        await handleTokenSuccess(response);
      },
    });

    button.disabled = false;
    button.addEventListener('click', () => {
      if (!tokenClient) return;
      tokenClient.requestAccessToken({ prompt: accessToken ? '' : 'consent' });
    });
  };

  initClient();
  updateAuthUI(Boolean(accessToken));
  restoreStoredSession();
}

async function fetchUpcomingEvents() {
  if (!accessToken) {
    setScheduleStatus('Sign in to pull your next event.');
    return;
  }

  setScheduleStatus('Fetching next event...');
  const nowIso = new Date().toISOString();
  const weekAhead = new Date();
  weekAhead.setDate(weekAhead.getDate() + 7);
  const resp = await fetch('/api/events/next', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ access_token: accessToken, time_min: nowIso, time_max: weekAhead.toISOString() })
  });

  if (!resp.ok) {
    const error = await readJsonSafely(resp);
    console.error('Calendar request failed', error);
    setScheduleStatus(error.error || 'Unable to load calendar events.', true);
    return;
  }

  const payload = await resp.json();
  const events = payload.events || [];
  if (!events.length) {
    scheduleData = [];
    selectedEventId = null;
    setScheduleStatus('No upcoming events found.', true);
    renderSchedule();
    return;
  }

  scheduleData = events.map(event => {
    const formatted = formatEventDateParts(event.start);
    return {
      id: event.id,
      title: event.summary || 'Calendar Event',
      location: event.location || null,
      hasLocation: event.has_location ?? Boolean(event.location),
      time: formatted.combined,
      dateLabel: formatted.dateLabel,
      timeLabel: formatted.timeLabel,
      dayHeading: formatted.dayHeading,
      dayKey: event.start_day || formatted.dayKey,
      isAllDay: formatted.isAllDay,
      rawStart: event.start,
      startTimestamp: typeof event.start_timestamp === 'number' ? event.start_timestamp * 1000 : null,
    };
  });
  scheduleData.sort((a, b) => {
    const aTime = typeof a.startTimestamp === 'number' ? a.startTimestamp : (normalizeEventDate(a.rawStart)?.getTime() || 0);
    const bTime = typeof b.startTimestamp === 'number' ? b.startTimestamp : (normalizeEventDate(b.rawStart)?.getTime() || 0);
    return aTime - bTime;
  });

  const selected = ensureSelectedEvent(true);
  setScheduleStatus(`Loaded ${events.length} upcoming event${events.length > 1 ? 's' : ''}.`);
  renderSchedule();
  if (selected && selected.hasLocation) {
    tryPlanRoute({ preferLocation: true });
  } else {
    renderServiceStatus('No upcoming events have a location set.');
  }
  updateActiveEventTitle(selected);
}

function normalizeEventDate(dateString) {
  if (!dateString) return null;
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateString)) {
    return new Date(`${dateString}T00:00:00`);
  }
  return new Date(dateString);
}

function formatEventDateParts(dateString) {
  const date = normalizeEventDate(dateString);
  if (!date) {
    return {
      combined: 'TBD',
      dateLabel: 'TBD',
      timeLabel: '--:--',
      dayHeading: 'Unknown date',
      dayKey: null,
      isAllDay: false,
    };
  }

  const dateLabel = date.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });
  const isAllDay = !dateString || dateString.length === 10;
  const timeLabel = isAllDay ? 'All day' : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const dayHeading = date.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' });
  const dayKey = date.toISOString().split('T')[0];

  return {
    combined: isAllDay ? `${dateLabel} (All day)` : `${dateLabel} ${timeLabel}`,
    dateLabel,
    timeLabel,
    dayHeading,
    dayKey,
    isAllDay,
  };
}

function formatTimeOfDay(timeString) {
  if (!timeString) return '--:--';
  const [hours, minutes] = timeString.split(':').slice(0, 2).map(Number);
  if (Number.isNaN(hours) || Number.isNaN(minutes)) return timeString;
  const date = new Date();
  date.setHours(hours, minutes, 0, 0);
  return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

function computeDepartureDate(nextTrain) {
  if (!nextTrain || !nextTrain.departure_time) return null;
  const [depHours, depMinutes] = nextTrain.departure_time.split(':').slice(0, 2).map(Number);
  if (Number.isNaN(depHours) || Number.isNaN(depMinutes)) return null;
  const base = currentRouteEvent ? normalizeEventDate(currentRouteEvent.rawStart) : new Date();
  const departure = base ? new Date(base) : new Date();
  departure.setHours(depHours, depMinutes, 0, 0);
  return departure;
}

function computeArrivalDate(route) {
  if (!route || !route.arrival_time) return null;
  const [arrHours, arrMinutes] = route.arrival_time.split(':').slice(0, 2).map(Number);
  if (Number.isNaN(arrHours) || Number.isNaN(arrMinutes)) return null;
  const base = currentRouteEvent ? normalizeEventDate(currentRouteEvent.rawStart) : new Date();
  const arrival = base ? new Date(base) : new Date();
  arrival.setHours(arrHours, arrMinutes, 0, 0);
  return arrival;
}

function getEventById(id) {
  return scheduleData.find(event => event.id === id);
}

function ensureSelectedEvent(preferLocation = false) {
  if (!scheduleData.length) {
    selectedEventId = null;
    return null;
  }

  let selected = selectedEventId ? getEventById(selectedEventId) : null;
  if (!selected) {
    selected = scheduleData[0];
    selectedEventId = selected.id;
  }

  if (preferLocation && selected && !selected.hasLocation) {
    const next = scheduleData.find(event => event.hasLocation);
    if (next) {
      selected = next;
      selectedEventId = next.id;
    }
  }

  return selected;
}

function getRouteCacheKey(event) {
  if (!event) return null;
  const id = event.id || 'unknown';
  const when = event.rawStart || '';
  const loc = event.location || '';
  return `${id}|${when}|${loc}`;
}

function handleEventSelection(eventId) {
  selectedEventId = eventId;
  renderSchedule();
  const event = getEventById(eventId);
  if (!event) return;
  updateActiveEventTitle(event);
  scrollEventIntoView(eventId);
  if (!event.hasLocation) {
    renderServiceStatus('Selected event has no location. Choose another event or add one in Calendar.');
    return;
  }
  tryPlanRoute();
}

async function tryPlanRoute({ preferLocation = true, allowRetry = true } = {}) {
  if (!scheduleData.length) {
    return;
  }
  let event = ensureSelectedEvent(preferLocation);
  if (!event) {
    renderServiceStatus('No events available to plan a route.');
    return;
  }
  if (!event.hasLocation) {
    const fallback = scheduleData.find(ev => ev.hasLocation);
    if (fallback) {
      event = fallback;
      selectedEventId = fallback.id;
      renderSchedule();
    } else {
      renderServiceStatus('No upcoming events have a location. Using default destination.');
    }
  }
  // Allow new requests even if another is in-flight, unless it's the same event.
  if (isRouteLoading && currentRouteEvent && currentRouteEvent.id === event.id) {
    return;
  }

  currentRouteEvent = event;
  currentRouteLabel = `${event.dayHeading} • ${event.isAllDay ? 'All day' : event.timeLabel}`;
  updateActiveEventTitle(event);

  isRouteLoading = true;
  const requestToken = ++planRequestToken;
  console.info('[route] start planning', currentRouteLabel, 'token', requestToken);
  renderServiceStatus(`Planning route for ${currentRouteLabel}...`);

  const cacheKey = getRouteCacheKey(event);
  if (cacheKey) {
    const cached = getCachedRoute(cacheKey);
    if (cached) {
      console.info('[route] cache hit', cacheKey);
      subwayData = cached;
      renderServiceStatus(`Using cached route for ${currentRouteLabel}`);
      renderSubwayInfo();
      calculateTimeToLeave();
      isRouteLoading = false;
      try {
        fetch('/health').catch(() => {});
      } catch (_) {}
      return;
    }
  }
  scrollEventIntoView(event.id);
  // Clear prior route UI/LEDs while we fetch a fresh plan (cache miss).
  subwayData = null;
  currentStopIndex = 0;
  renderSubwayInfo();
  calculateTimeToLeave();
  updateLEDStrip([]);

  const payload = {
    origin: userLocation,
    destination: { label: event.location || googleConfig.defaultDestination },
    event_start: event.rawStart,
    current_time: new Date().toISOString(),
    user_context: `Event: ${event.title} on ${currentRouteLabel}`,
  };

  try {
    const resp = await fetch('/api/routes/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!resp.ok) {
      const error = await readJsonSafely(resp);
      console.error('Route planning failed', error);
      const detail = error.details || error.error || 'Unable to plan route';
      renderServiceStatus(`Error: ${detail}`);
      return;
    }

    subwayData = await resp.json();
    if (requestToken !== planRequestToken) {
      // Outdated response; ignore.
      return;
    }
    if (cacheKey) {
      setCachedRoute(cacheKey, subwayData);
    }
    console.info('[route] plan ready', currentRouteLabel, 'token', requestToken);
    const departureDate = computeDepartureDate(subwayData.next_train);
    const arrivalDate = computeArrivalDate(subwayData.route);
    const eventStartDate = currentRouteEvent ? new Date(currentRouteEvent.rawStart) : null;
    const now = new Date();
    const eventIsToday = eventStartDate ? eventStartDate.toDateString() === now.toDateString() : true;
    const departurePassed = eventIsToday && departureDate && departureDate < now;
    const isAllDayEvent = currentRouteEvent ? currentRouteEvent.isAllDay : false;
    const departureTooEarly = !isAllDayEvent && eventStartDate && departureDate && (eventStartDate - departureDate > MAX_DEPARTURE_ADVANCE_MS);
    const arrivalTooEarly = !isAllDayEvent && eventStartDate && arrivalDate && (eventStartDate - arrivalDate > MAX_EARLY_ARRIVAL_MS);
    if (departurePassed || departureTooEarly || arrivalTooEarly) {
      const needsRetry = allowRetry;
      renderServiceStatus(needsRetry ? 'Refreshing schedule to find a closer departure...' : 'Showing earliest departure available for this event.');
      renderSubwayInfo();
      calculateTimeToLeave();
      if (needsRetry) {
        isRouteLoading = false;
        await tryPlanRoute({ preferLocation, allowRetry: false });
        return;
      }
    }
    renderServiceStatus(`Route ready for ${currentRouteLabel}`);
    renderSubwayInfo();
    calculateTimeToLeave();
  } catch (error) {
    console.error('Route planning network error', error);
    renderServiceStatus('Error: Unable to reach planner');
  } finally {
    if (requestToken === planRequestToken) {
      isRouteLoading = false;
    }
  }
}

// NYC Subway Line Colors (RGB) - Adjusted for better LED distinction
const LINE_COLORS = {
  '1': [255, 0, 0], '2': [255, 0, 0], '3': [255, 0, 0],
  '4': [0, 255, 0], '5': [0, 255, 0], '6': [0, 255, 0],
  '7': [180, 0, 180],
  'A': [0, 0, 255], 'C': [0, 0, 255], 'E': [0, 0, 255],
  'B': [255, 140, 0], 'D': [255, 140, 0], 'F': [255, 140, 0], 'M': [255, 140, 0],
  'G': [100, 255, 50],
  'J': [150, 100, 50], 'Z': [150, 100, 50],
  'L': [150, 150, 150],
  'N': [255, 255, 0], 'Q': [255, 255, 0], 'R': [255, 255, 0], 'W': [255, 255, 0],
  'S': [100, 100, 100]
};

function getLineColor(line) {
  const rgb = LINE_COLORS[line];
  if (!rgb) return 'rgb(255, 99, 25)';
  return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
}

// Trigger LED update
function updateLEDStrip(stops, activeIndex = 0) {
  const routeStops = Array.isArray(stops) ? stops : [];
  const clampedActive = routeStops.length ? Math.max(0, Math.min(routeStops.length - 1, activeIndex)) : 0;

  const transfers = (subwayData && subwayData.route && subwayData.route.transfers) || [];
  const transferMap = {};
  transfers.forEach(t => { transferMap[t.at_station] = t.to_line; });

  const currentLine = subwayData && subwayData.next_train ? subwayData.next_train.line : 'F';
  const leds = [];

  if (!routeStops.length) {
    while (leds.length < LED_COUNT) {
      leds.push({ r: 0, g: 0, b: 0, mode: 'static' });
    }
    fetch('/update-leds', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ leds })
    }).catch(error => {
      console.warn('LED Update Failed:', error);
    });
    return;
  }

  let activeLine = currentLine || 'F';
  for (let i = 0; i < routeStops.length && leds.length < LED_COUNT; i += 1) {
    if (i > 0) {
      const transferLine = transferMap[routeStops[i - 1]];
      if (transferLine) {
        activeLine = transferLine;
      }
    }
    const rgb = LINE_COLORS[activeLine] || [255, 99, 25];
    // Highlight the currently focused stop with a white overlay.
    if (i === clampedActive) {
      leds.push({ r: 255, g: 255, b: 255, mode: 'static' });
    } else {
      leds.push({ r: rgb[0], g: rgb[1], b: rgb[2], mode: 'static' });
    }
  }

  while (leds.length < LED_COUNT) {
    leds.push({ r: 0, g: 0, b: 0, mode: 'static' });
  }

  fetch('/update-leds', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ leds: leds.slice(0, LED_COUNT) })
  }).catch(error => {
    console.warn('LED Update Failed:', error);
  });
}

async function init() {
  updateClock();
  setInterval(updateClock, 1000);
  loadRouteCacheFromStorage();
  cleanupRouteCache();
  renderSchedule();
  renderWeather();
  fetchWeather();
  renderServiceStatus();
  calculateTimeToLeave();
  setInterval(calculateTimeToLeave, 60000);
  // Periodically refresh the current route (and bypass expired cache entries).
  setInterval(() => {
    tryPlanRoute({ preferLocation: true, allowRetry: true });
  }, 5 * 60 * 1000);

  setScheduleStatus('Sign in to Google Calendar to start.');

  await fetchConfig();
  initGoogleAuth();
  userLocation = { ...FIXED_ORIGIN };

  // Initialize Navigation
  showScreen(1);
  pollEncoder();
}

// Navigation Logic
let currentScreen = 1;
const totalScreens = 3;
let detailMode = false; // Track if we're in detail view

function showScreen(screenIndex) {
  if (screenIndex < 1) screenIndex = totalScreens;
  if (screenIndex > totalScreens) screenIndex = 1;
  
  currentScreen = screenIndex;
  detailMode = false; // Reset to summary when switching screens
  
  // Update Screens
  document.querySelectorAll('.screen-section').forEach(el => {
    el.classList.remove('active');
    // Reset to summary view
    const summary = el.querySelector('.summary-view');
    const detail = el.querySelector('.detail-view');
    if (summary) summary.style.display = 'flex';
    if (detail) detail.style.display = 'none';
  });
  const activeScreen = document.getElementById(`screen-${currentScreen}`);
  if (activeScreen) activeScreen.classList.add('active');
  
  // Update Dots
  document.querySelectorAll('.dot').forEach(el => {
    el.classList.remove('active');
  });
  const activeDot = document.querySelector(`.dot[data-screen="${currentScreen}"]`);
  if (activeDot) activeDot.classList.add('active');
}

function toggleDetailView() {
  // Temporarily disable detail toggle on Screen 2 (time + line) but keep
  // logic intact for potential future use.
  if (currentScreen === 2) return;

  const activeScreen = document.getElementById(`screen-${currentScreen}`);
  if (!activeScreen) return;
  
  const summary = activeScreen.querySelector('.summary-view');
  const detail = activeScreen.querySelector('.detail-view');
  
  if (!summary || !detail) return;
  
  detailMode = !detailMode;
  
  if (detailMode) {
    summary.style.display = 'none';
    detail.style.display = 'flex';
    if (currentScreen === 3) {
      renderStopDetail();
    }
  } else {
    summary.style.display = 'flex';
    detail.style.display = 'none';
    if (currentScreen === 3) {
      currentStopIndex = 0;
      renderStopDetail();
    }
  }
}

function nextScreen() {
  if (isEventDetailActive()) {
    moveSelection(1);
    return;
  }
  if (isStopDetailActive()) {
    changeStopIndex(1);
    return;
  }
  showScreen(currentScreen + 1);
}

function prevScreen() {
  if (isEventDetailActive()) {
    moveSelection(-1);
    return;
  }
  if (isStopDetailActive()) {
    changeStopIndex(-1);
    return;
  }
  showScreen(currentScreen - 1);
}

// Keyboard Navigation (for testing)
document.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowRight') nextScreen();
  if (e.key === 'ArrowLeft') prevScreen();
  if (e.key === 'Enter' || e.key === ' ') toggleDetailView();
});

// Poll for Encoder Events
async function pollEncoder() {
    try {
        const response = await fetch('/api/encoder-event');
        if (response.ok) {
            const data = await response.json();
            
            // Clockwise -> Previous Screen, Counter-Clockwise -> Next Screen
            if (data.event === 'cw') prevScreen();
            if (data.event === 'ccw') nextScreen();
            if (data.event === 'click') {
                if (isEventDetailActive()) {
                    // Enter Screen 2 when clicking while browsing events.
                    showScreen(2);
                } else if (isStopDetailActive()) {
                    // Exit stop detail to summary on click.
                    toggleDetailView();
                } else {
                    toggleDetailView();
                }
            }
        }
    } catch (e) {
        // Ignore errors
    }
    // Poll again
    setTimeout(pollEncoder, 100);
}

document.addEventListener('DOMContentLoaded', init);
function isEventDetailActive() {
  const screenEl = document.getElementById(`screen-${currentScreen}`);
  if (!screenEl) return false;
  if (currentScreen !== 1) return false;
  const detail = screenEl.querySelector('.detail-view');
  return detail && detail.style.display === 'flex';
}

function isStopDetailActive() {
  const screenEl = document.getElementById(`screen-${currentScreen}`);
  if (!screenEl) return false;
  if (currentScreen !== 3) return false;
  const detail = screenEl.querySelector('.detail-view');
  return detail && detail.style.display === 'flex';
}

function buildLineSequence(plan) {
  if (!plan || !plan.next_train) return [];
  const baseLine = plan.next_train.line;
  const transfers = (plan.route && Array.isArray(plan.route.transfers)) ? plan.route.transfers : [];
  const stops = (plan.route && Array.isArray(plan.route.stops)) ? plan.route.stops : [];
  if (!baseLine) return [];
  const seq = [baseLine];
  // Append each transfer line in order, avoiding duplicates.
  transfers.forEach(t => {
    if (t && t.to_line && seq[seq.length - 1] !== t.to_line) {
      seq.push(t.to_line);
    }
  });
  // Fallback: infer transfers embedded in stop labels like "Transfer to F".
  stops.forEach(s => {
    if (typeof s !== 'string') return;
    const m = /transfer to\s+([A-Za-z0-9]+)/i.exec(s);
    if (m && seq[seq.length - 1] !== m[1]) {
      seq.push(m[1]);
    }
  });
  return seq;
}

function isValidRoute(payload) {
  if (!payload || typeof payload !== 'object') return false;
  const nt = payload.next_train || {};
  const rt = payload.route || {};
  const hasLine = Boolean(nt.line);
  const hasDeparture = Boolean(nt.departure_time);
  // Allow cached routes even if stops are missing; they may be filled later.
  return hasLine && hasDeparture;
}

function renderTransfers(transfers) {
  if (!transfers || !transfers.length) {
    return 'No transfers';
  }
  const parts = [];
  transfers.forEach(t => {
    if (t?.to_line && t?.at_station) {
      parts.push(`Transfer to ${t.to_line} at ${t.at_station}`);
    }
  });
  return parts.length ? parts.join(' • ') : 'No transfers';
}

function changeStopIndex(delta) {
  if (!currentStops.length) return;
  currentStopIndex = Math.max(0, Math.min(currentStops.length - 1, currentStopIndex + delta));
  renderStopDetail();
  // Move LEDs to reflect the focused stop (white dot marches along stops).
  updateLEDStrip(currentStops, currentStopIndex);
}

function moveSelection(delta) {
  if (!scheduleData.length) return;
  let idx = scheduleData.findIndex(ev => ev.id === selectedEventId);
  if (idx === -1) idx = 0;
  idx = Math.max(0, Math.min(scheduleData.length - 1, idx + delta));
  const target = scheduleData[idx];
  handleEventSelection(target.id);
}
