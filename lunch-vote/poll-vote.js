(function () {
  const pathSegments = window.location.pathname.split('/').filter(Boolean);
  const queryPollSlug = new URLSearchParams(window.location.search).get('poll') || '';
  const pathPollSlug = pathSegments[0] === 'poll-vote' ? pathSegments[1] : pathSegments[0];
  const pollSlug = (queryPollSlug || pathPollSlug || 'lunch-vote').trim();
  const apiBase = `/api/poll-vote/${encodeURIComponent(pollSlug)}`;
  const tokenStorageKey = `zoak-poll-token:${pollSlug}`;
  let poll = null;
  let voteToken = '';
  let voteTokenUsable = false;
  let currentCandidateSlug = '';
  let selectedCandidateSlug = '';
  let closeTimerHandle = null;

  function isLikelyVoteToken(value) {
    return /^[A-Za-z0-9_-]{24,128}$/.test(value || '');
  }

  function readStoredVoteToken() {
    try {
      return sessionStorage.getItem(tokenStorageKey) || '';
    } catch (e) {
      return '';
    }
  }

  function storeVoteToken(token) {
    try {
      sessionStorage.setItem(tokenStorageKey, token);
    } catch (e) {}
  }

  function clearStoredVoteToken() {
    try {
      sessionStorage.removeItem(tokenStorageKey);
    } catch (e) {}
  }

  function captureVoteTokenFromUrl() {
    const url = new URL(window.location.href);
    const token = (url.searchParams.get('token') || '').trim();
    if (token) {
      url.searchParams.delete('token');
      window.history.replaceState({}, document.title, `${url.pathname}${url.search}${url.hash}`);
    }
    return token;
  }

  function candidateBySlug(slug) {
    return (poll?.candidates || []).find((candidate) => candidate.slug === slug);
  }

  function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value || '';
  }

  function setTokenNotice(message) {
    const notice = document.getElementById('tokenNotice');
    notice.textContent = message;
    notice.classList.toggle('visible', Boolean(message));
  }

  function setStatus(message, type) {
    const status = document.getElementById('voteStatus');
    status.textContent = message;
    status.className = `status visible ${type || ''}`;
  }

  function isPollClosed() {
    if (!poll?.closeTime) return Boolean(poll?.isClosed);
    return Date.now() >= Date.parse(poll.closeTime);
  }

  function updateSubmitState(isBusy) {
    const submitButton = document.getElementById('submitButton');
    const closed = isPollClosed();
    submitButton.disabled = Boolean(isBusy) || !voteTokenUsable || closed;
    submitButton.textContent = closed ? 'Poll closed' : (currentCandidateSlug ? 'Update vote' : 'Cast vote');
  }

  function formatCountdown(ms) {
    const totalSeconds = Math.max(0, Math.floor(ms / 1000));
    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    return `${String(days).padStart(2, '0')}:${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}.${String(seconds).padStart(2, '0')}`;
  }

  function updateCloseTimer() {
    const timer = document.getElementById('closeTimer');
    if (!poll?.closeTime) {
      timer.classList.remove('visible');
      return;
    }
    const remaining = Date.parse(poll.closeTime) - Date.now();
    timer.classList.add('visible');
    if (remaining <= 0) {
      timer.textContent = 'Poll closed';
      poll.isClosed = true;
      updateSubmitState();
      return;
    }
    timer.textContent = `Closes in ${formatCountdown(remaining)}`;
  }

  function startCloseTimer() {
    if (closeTimerHandle) window.clearInterval(closeTimerHandle);
    updateCloseTimer();
    if (poll?.closeTime) {
      closeTimerHandle = window.setInterval(updateCloseTimer, 1000);
    }
  }

  function applyCurrentVote(candidateSlug) {
    currentCandidateSlug = candidateSlug || '';
    document.querySelectorAll('.hero-option').forEach((button) => {
      button.classList.toggle('voted', button.dataset.candidateSlug === currentCandidateSlug);
    });
    document.querySelectorAll('.option-radio').forEach((label) => {
      const input = label.querySelector('input[name="candidate"]');
      label.classList.toggle('voted', Boolean(input && input.value === currentCandidateSlug));
    });
    updateSubmitState();
  }

  function selectCandidate(candidateSlug, options = {}) {
    const candidate = candidateBySlug(candidateSlug);
    if (!candidate) return;
    selectedCandidateSlug = candidateSlug;
    document.querySelectorAll('.hero-option').forEach((button) => {
      button.setAttribute('aria-pressed', button.dataset.candidateSlug === candidateSlug ? 'true' : 'false');
    });
    document.querySelectorAll('.option-radio').forEach((label) => label.classList.remove('selected'));
    const input = document.getElementById(`candidate-${candidate.slug}`);
    if (input) {
      input.checked = true;
      input.closest('.option-radio').classList.add('selected');
    }
    if (options.scroll !== false) {
      document.getElementById('voteCard').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  function renderTags(tags) {
    const wrapper = document.createElement('span');
    wrapper.className = 'tag-list';
    (tags || []).forEach((tag) => {
      const item = document.createElement('span');
      item.className = 'tag';
      item.innerHTML = `<b></b><span></span>`;
      item.querySelector('b').textContent = tag.key || '';
      item.querySelector('span').textContent = tag.val || '';
      wrapper.append(item);
    });
    return wrapper;
  }

  function renderHeroCandidates() {
    const strip = document.getElementById('heroCandidateStrip');
    strip.replaceChildren();
    poll.candidates.forEach((candidate) => {
      const button = document.createElement('button');
      button.className = 'hero-option';
      button.type = 'button';
      button.dataset.candidateSlug = candidate.slug;
      button.setAttribute('aria-pressed', 'false');
      button.setAttribute('aria-label', `Select ${candidate.name}`);
      button.addEventListener('click', () => selectCandidate(candidate.slug));

      const img = document.createElement('img');
      img.src = candidate.img;
      img.alt = `${candidate.name} thumbnail`;
      img.width = 320;
      img.height = 240;

      const overlay = document.createElement('span');
      overlay.className = 'thumb-overlay';
      overlay.innerHTML = '<strong></strong><span></span>';
      overlay.querySelector('strong').textContent = candidate.name;
      overlay.querySelector('span').textContent = (candidate.tags || []).map((tag) => tag.val).filter(Boolean).slice(0, 2).join(' · ');

      button.append(img, overlay);
      strip.append(button);
    });
  }

  function renderCandidateRadios() {
    const choices = document.getElementById('candidateChoices');
    choices.replaceChildren();
    poll.candidates.forEach((candidate) => {
      const label = document.createElement('label');
      label.className = 'option-radio';
      label.htmlFor = `candidate-${candidate.slug}`;

      const input = document.createElement('input');
      input.id = `candidate-${candidate.slug}`;
      input.type = 'radio';
      input.name = 'candidate';
      input.value = candidate.slug;
      input.required = true;
      input.addEventListener('change', () => selectCandidate(candidate.slug, { scroll: false }));

      const title = document.createElement('strong');
      title.textContent = candidate.name;

      const details = document.createElement('small');
      details.textContent = candidate.details;

      label.append(input, title, details, renderTags(candidate.tags));
      if (candidate.informationUrl) {
        const link = document.createElement('a');
        link.href = candidate.informationUrl;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = 'More information';
        label.append(link);
      }
      choices.append(label);
    });
  }

  async function verifyVoteToken() {
    if (!voteToken) return;
    try {
      const response = await fetch(`${apiBase}/token?token=${encodeURIComponent(voteToken)}`);
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.ok || !data.usable) {
        voteTokenUsable = false;
        applyCurrentVote('');
        setTokenNotice(data.error || 'This voting link cannot be used.');
        updateSubmitState();
        return;
      }
      voteTokenUsable = true;
      if (data.pollClosed) poll.isClosed = true;
      if (data.voted && data.candidateSlug) {
        applyCurrentVote(data.candidateSlug);
        selectCandidate(data.candidateSlug, { scroll: false });
        setTokenNotice(`Your current vote is ${data.candidateName || 'recorded'}. Select another option to update it.`);
      } else {
        applyCurrentVote('');
        setTokenNotice(isPollClosed() ? 'This poll is closed.' : 'Your voting link is ready. Cast one vote below.');
      }
      updateSubmitState();
    } catch (e) {
      setTokenNotice('Could not verify this voting link yet. You can still try to submit.');
      updateSubmitState();
    }
  }

  function initializeVoteToken() {
    const urlToken = captureVoteTokenFromUrl();
    if (urlToken && !isLikelyVoteToken(urlToken)) {
      voteToken = '';
      voteTokenUsable = false;
      clearStoredVoteToken();
      setTokenNotice('This voting link is not valid. Ask the organiser for a fresh link.');
      updateSubmitState();
      return;
    }
    voteToken = urlToken || readStoredVoteToken();
    if (!voteToken) {
      voteTokenUsable = false;
      setTokenNotice('Use your unique voting link from the email invitation to cast a vote. Results are still available below.');
      updateSubmitState();
      return;
    }
    storeVoteToken(voteToken);
    voteTokenUsable = true;
    setTokenNotice('Checking your voting link...');
    updateSubmitState();
    verifyVoteToken();
  }

  async function submitVote(event) {
    event.preventDefault();
    const payload = {
      token: voteToken,
      candidateSlug: selectedCandidateSlug,
      comment: document.getElementById('comment').value.trim(),
      dietary: '',
      website: document.getElementById('website').value.trim()
    };
    if (!isLikelyVoteToken(payload.token)) {
      setStatus('Use your unique voting link from the email invitation.', 'error');
      return;
    }
    if (!payload.candidateSlug) {
      setStatus('Choose an option before casting your vote.', 'error');
      return;
    }
    if (payload.comment.length > 500) {
      setStatus('The comment is longer than allowed.', 'error');
      return;
    }
    if (payload.website) {
      setStatus('Submission could not be accepted.', 'error');
      return;
    }
    updateSubmitState(true);
    setStatus('Submitting your vote...', 'pending');
    try {
      const response = await fetch(apiBase, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.ok) {
        throw new Error(data.error || 'Vote could not be recorded.');
      }
      voteTokenUsable = true;
      applyCurrentVote(data.candidateSlug || payload.candidateSlug);
      setTokenNotice(`Your current vote is ${data.candidateName || candidateBySlug(payload.candidateSlug)?.name || 'recorded'}. Select another option to update it.`);
      setStatus(data.message || 'Vote recorded.', 'success');
      await loadResults();
    } catch (error) {
      setStatus(error.message || 'Vote could not be recorded.', 'error');
    } finally {
      updateSubmitState();
    }
  }

  async function loadResults() {
    const summary = document.getElementById('resultsSummary');
    summary.textContent = 'Loading results...';
    try {
      const response = await fetch(`${apiBase}/results`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Results could not be loaded.');
      renderResults(data);
    } catch (error) {
      summary.textContent = 'Results are unavailable right now.';
      document.getElementById('resultsList').replaceChildren();
    }
  }

  function renderResults(data) {
    const total = Number(data.total) || 0;
    const list = document.getElementById('resultsList');
    const summary = document.getElementById('resultsSummary');
    const options = Array.isArray(data.options) ? data.options : [];
    summary.textContent = `${total} total vote${total === 1 ? '' : 's'}`;
    list.replaceChildren();

    poll.candidates.forEach((candidate) => {
      const result = options.find((item) => item.slug === candidate.slug) || { votes: 0, percentage: 0 };
      const votes = Number(result.votes) || 0;
      const percentage = Number(result.percentage) || 0;
      const row = document.createElement('div');
      row.className = 'result-row';
      row.setAttribute('aria-label', `${candidate.name}: ${votes} vote${votes === 1 ? '' : 's'}, ${percentage.toFixed(1)} percent`);
      const meta = document.createElement('div');
      meta.className = 'result-meta';
      meta.innerHTML = '<strong></strong><span></span>';
      meta.querySelector('strong').textContent = candidate.name;
      meta.querySelector('span').textContent = `${votes} vote${votes === 1 ? '' : 's'} · ${percentage.toFixed(1)}%`;
      const track = document.createElement('div');
      track.className = 'result-track';
      const fill = document.createElement('span');
      fill.className = 'result-fill';
      fill.style.width = `${Math.max(0, Math.min(100, percentage))}%`;
      track.append(fill);
      row.append(meta, track);
      list.append(row);
    });
  }

  async function loadPoll() {
    const response = await fetch(`${apiBase}/config`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Poll config could not be loaded.');
    poll = data;
    document.title = `${poll.PollTitle} — ZOAK Solutions`;
    setText('pollSlugLabel', poll.PollSlug);
    setText('pollTitle', poll.PollTitle);
    setText('pollDescription', poll.PollDescription);
    renderHeroCandidates();
    renderCandidateRadios();
    startCloseTimer();
  }

  document.addEventListener('DOMContentLoaded', async () => {
    try {
      await loadPoll();
      document.getElementById('voteForm').addEventListener('submit', submitVote);
      document.getElementById('refreshResults').addEventListener('click', loadResults);
      initializeVoteToken();
      loadResults();
    } catch (error) {
      setText('pollTitle', 'Poll unavailable');
      setText('pollDescription', error.message || 'The poll could not be loaded.');
    }
  });
})();
